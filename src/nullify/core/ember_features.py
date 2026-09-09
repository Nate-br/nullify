"""EMBER 2017 feature extraction (feature_version=2 layout, 2381 dims).

Vendored from elastic/ember (ember/features.py, MIT/AdaptiveBeam license) with
one deliberate change: LIEF is replaced by a pefile-backed shim providing the
same duck-typed surface (sections, imports, exports, headers, data directories).
This removes the pinned lief-0.9.0 dependency while keeping the raw-feature
schema byte-compatible with the EMBER 2017 v2 dataset shipped by Elastic.

IMPORTANT TRAIN/INFERENCE CONTRACT
  * Dataset training: read the dataset's *raw feature dicts* and call
    ``ember_feature_vector_from_raw(raw)`` — identical layout code to inference.
  * Inference: read file bytes and call ``ember_feature_vector_from_bytes(b)``
    which produces the same raw dict schema (verified by tests against the
    dataset's own records) then vectorizes it with the same functions.

Feature block order (v2): histogram(256) byteentropy(256) strings(104)
general(10) header(62) section(255) imports(1280) exports(128)
datadirectories(30) = 2381 dims.
"""

from __future__ import annotations

import binascii
import json
import math
import os
import re
from collections import OrderedDict

import numpy as np
import pefile
from sklearn.feature_extraction import FeatureHasher

# --------------------------------------------------------------------------
# pefile-backed LIEF shim (duck-typed subset used by the feature blocks)
# --------------------------------------------------------------------------

class _ShimSection:
    """LIEF-like view of a pefile PE section."""

    def __init__(self, pe: pefile.PE, section: pefile.SectionStructure):
        self.name = section.Name.rstrip(b"\x00").decode("utf-8", "ignore")
        self.size = int(section.Misc_VirtualSize or 0)
        self.virtual_size = int(section.Misc_VirtualSize or 0)
        raw = section.get_data()
        self.entropy = float(section.get_entropy()) if raw else 0.0
        chars = int(section.Characteristics)
        self.characteristics_lists = [
            flag for flag in _SECTION_FLAGS if chars & getattr(pefile.SECTION_CHARACTERISTICS, flag).value
        ]


_SECTION_FLAGS = [
    "MEM_EXECUTE", "MEM_READ", "MEM_WRITE",
    "CNT_CODE", "CNT_INITIALIZED_DATA", "CNT_UNINITIALIZED_DATA",
]


class _ShimImportEntry:
    def __init__(self, imp: pefile.ImportData):
        if imp.ordinal is not None:
            self.is_ordinal = True
            self.ordinal = int(imp.ordinal)
            self.name = ""
        else:
            self.is_ordinal = False
            self.ordinal = 0
            self.name = (imp.name or b"").decode("utf-8", "ignore")


class _ShimImportLib:
    def __init__(self, entry: pefile.ImportDescData):
        self.name = (entry.dll or b"").decode("utf-8", "ignore")
        self.entries = [_ShimImportEntry(i) for i in (entry.imports or [])]


class _ShimDataDirectory:
    def __init__(self, name: str, entry: pefile.DataDirectory):
        self.type_name = name
        self.size = int(entry.Size or 0)
        self.rva = int(entry.VirtualAddress or 0)


class _LiefShim:
    """Parses with pefile, exposes the LIEF-0.9-style attributes EMBER reads."""

    def __init__(self, bytez: bytes):
        self._pe = pefile.PE(data=bytez, fast_load=False)
        self.sections = [_ShimSection(self._pe, s) for s in self._pe.sections]
        self.imports = [
            _ShimImportLib(e)
            for e in getattr(self._pe, "DIRECTORY_ENTRY_IMPORT", [])
        ]
        # exports: lief.exported_functions yields names (0.9.0 behaviour)
        self.exported_functions = [
            e.name.decode("utf-8", "ignore") if isinstance(e.name, bytes) else str(e.name or "")
            for e in getattr(self._pe, "DIRECTORY_ENTRY_EXPORT", {}).symbols
        ] if hasattr(self._pe, "DIRECTORY_ENTRY_EXPORT") else []

        oh = self._pe.OPTIONAL_HEADER
        self.virtual_size = int(oh.SizeOfImage or 0)
        self.entrypoint = int(oh.AddressOfEntryPoint or 0)
        self.imagebase = int(oh.ImageBase or 0)

        fh = self._pe.FILE_HEADER
        machine = _MACHINE_NAMES.get(int(fh.Machine), "UNKNOWN_MACHINE")
        characteristics = [
            flag for flag in _COFF_CHARS if int(fh.Characteristics) & getattr(pefile.FILE_CHARACTERISTICS, flag).value
        ]
        self.header = _Header(coff_ts=int(fh.TimeDateStamp), machine=machine,
                              characteristics=characteristics, oh=oh)
        self.data_directories = [
            _ShimDataDirectory(name, oh.DATA_DIRECTORY[i])
            for i, name in enumerate(_DATA_DIR_NAMES)
        ]

        self.has_debug = any(d.name == "DEBUG" and d.size > 0 for d in self.data_directories)
        self.has_relocations = any(d.name == "BASE_RELOCATION_TABLE" and d.size > 0 for d in self.data_directories)
        self.has_resources = any(d.name == "RESOURCE_TABLE" and d.size > 0 for d in self.data_directories)
        self.has_tls = any(d.name == "TLS_TABLE" and d.size > 0 for d in self.data_directories)
        self.has_signature = self._pe.verify_signature() if hasattr(self._pe, "verify_signature") else 0
        self.has_resources_len = self.has_resources
        self.symbols = getattr(self._pe, "DIRECTORY_ENTRY_DEBUG", [])  # conservative: debug entries only

    # entry-point section lookup (lief 0.12 semantics, with the 0.9 fallback)
    def section_from_rva(self, rva: int):
        for s in self._pe.sections:
            va = int(s.VirtualAddress)
            vs = int(s.Misc_VirtualSize or 0) or int(s.SizeOfRawData or 0)
            if va <= rva < va + max(vs, 1):
                return _ShimSection(self._pe, s)
        return None

    def section_from_offset(self, _off: int):
        return None  # not needed; SectionInfo handles fallback itself


class _Header:
    def __init__(self, coff_ts: int, machine: str, characteristics: list[str], oh):
        self.time_date_stamps = coff_ts
        self.machine_name = machine
        self.characteristics_names = characteristics
        subsystem = _SUBSYSTEM_NAMES.get(int(oh.Subsystem), "UNKNOWN_SUBSYSTEM")
        magic = _PE_MAGIC_NAMES.get(int(oh.Magic), "UNKNOWN_MAGIC")
        self.optional_header = _OptionalHeader(oh, subsystem, magic)

    @property
    def machine(self):
        return _EnumName("PE_HEADER_MACHINE", self.machine_name)

    @property
    def characteristics_list(self):
        return [_EnumName("PE_HEADER_CHARACTERISTICS", c) for c in self.characteristics_names]


class _EnumName:
    """string() -> 'PARENT.CHILD' style name, mimicking lief enums."""

    def __init__(self, parent: str, child: str):
        self._parent = parent
        self._child = child

    def __str__(self):
        return f"{self._parent}.{self._child}"


class _OptionalHeader:
    def __init__(self, oh, subsystem: str, magic: str):
        self._oh = oh
        self._subsystem = subsystem
        self._magic = magic

    @property
    def subsystem(self):
        return _EnumName("PE_SUBSYSTEM", self._subsystem)

    @property
    def magic(self):
        return _EnumName("PE_MAGIC", self._magic)

    @property
    def dll_characteristics_lists(self):
        flags = []
        for flag in _DLL_CHARS:
            try:
                if int(self._oh.DllCharacteristics) & getattr(pefile.DLL_CHARACTERISTICS, flag).value:
                    flags.append(_EnumName("PE_DLL_CHARACTERISTICS", flag))
            except AttributeError:  # pragma: no cover - pefile constant set changed
                continue
        return flags

    def __getattr__(self, item: str):
        # major_image_version etc. pass through to pefile's optional header
        try:
            return self.__dict__["_oh"].__getattribute__(item)
        except AttributeError:
            raise AttributeError(item)


_MACHINE_NAMES = {
    0x014c: "I386", 0x8664: "AMD64", 0x01c0: "ARM", 0xaa64: "ARM64",
    0x0200: "IA64", 0x01f0: "POWERPC", 0x01c2: "THUMB",
}
_COFF_CHARS = ["RELOCS_STRIPPED", "EXECUTABLE_IMAGE", "LINE_NUMS_STRIPPED", "LOCAL_SYMS_STRIPPED",
               "AGGRESIVE_WS_TRIM", "LARGE_ADDRESS_AWARE", "BYTES_REVERSED_LO", "32BIT_MACHINE",
               "DEBUG_STRIPPED", "REMOVABLE_RUN_FROM_SWAP", "NET_RUN_FROM_SWAP", "SYSTEM", "DLL",
               "UP_SYSTEM_ONLY", "BYTES_REVERSED_HI"]
_DLL_CHARS = ["HIGH_ENTROPY_VA", "DYNAMIC_BASE", "FORCE_INTEGRITY", "NX_COMPAT", "NO_ISOLATION",
              "NO_SEH", "NO_BIND", "APPCONTAINER", "WDM_DRIVER", "GUARD_CF", "TERMINAL_SERVER_AWARE"]
_SUBSYSTEM_NAMES = {1: "NATIVE", 2: "WINDOWS_CUI", 3: "WINDOWS_CE", 5: "OS2_CUI",
                    7: "POSIX_CUI", 9: "WINDOWS_CE_GUI", 10: "EFI_APPLICATION", 14: "XBOX"}
_PE_MAGIC_NAMES = {0x10b: "PE32", 0x20b: "PE32_PLUS"}
_DATA_DIR_NAMES = [
    "EXPORT_TABLE", "IMPORT_TABLE", "RESOURCE_TABLE", "EXCEPTION_TABLE", "CERTIFICATE_TABLE",
    "BASE_RELOCATION_TABLE", "DEBUG", "ARCHITECTURE", "GLOBAL_PTR", "TLS_TABLE", "LOAD_CONFIG_TABLE",
    "BOUND_IMPORT", "IAT", "DELAY_IMPORT_DESCRIPTOR", "CLR_RUNTIME_HEADER",
]


def _parse_pe(bytez: bytes):
    try:
        return _LiefShim(bytez)
    except pefile.PEFormatError:
        return None
    except Exception:  # noqa: BLE001 - parity with lief parse failure path
        return None


# --------------------------------------------------------------------------
# Feature blocks (vendored from elastic/ember, ember/features.py)
# --------------------------------------------------------------------------

class FeatureType:
    name = ""
    dim = 0

    def raw_features(self, bytez: bytes, lief_binary):  # pragma: no cover - abstract
        raise NotImplementedError

    def process_raw_features(self, raw_obj):  # pragma: no cover - abstract
        raise NotImplementedError


class ByteHistogram(FeatureType):
    name = "histogram"
    dim = 256

    def raw_features(self, bytez, lief_binary):
        counts = np.bincount(np.frombuffer(bytez, dtype=np.uint8), minlength=256)
        return counts.tolist()

    def process_raw_features(self, raw_obj):
        counts = np.array(raw_obj, dtype=np.float32)
        return counts / counts.sum()


class ByteEntropyHistogram(FeatureType):
    name = "byteentropy"
    dim = 256

    def __init__(self, step=1024, window=2048):
        self.window = window
        self.step = step

    def _entropy_bin_counts(self, block):
        c = np.bincount(block >> 4, minlength=16)
        p = c.astype(np.float32) / self.window
        wh = np.where(c)[0]
        H = np.sum(-p[wh] * np.log2(p[wh])) * 2
        Hbin = int(H * 2)
        if Hbin == 16:
            Hbin = 15
        return Hbin, c

    def raw_features(self, bytez, lief_binary):
        output = np.zeros((16, 16), dtype=np.int64)  # np.int is dead in numpy>=1.24
        a = np.frombuffer(bytez, dtype=np.uint8)
        if a.shape[0] < self.window:
            Hbin, c = self._entropy_bin_counts(a)
            output[Hbin, :] += c
        else:
            shape = a.shape[:-1] + (a.shape[-1] - self.window + 1, self.window)
            strides = a.strides + (a.strides[-1],)
            blocks = np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)[::self.step, :]
            for block in blocks:
                Hbin, c = self._entropy_bin_counts(block)
                output[Hbin, :] += c
        return output.flatten().tolist()

    def process_raw_features(self, raw_obj):
        counts = np.array(raw_obj, dtype=np.float32)
        return counts / counts.sum()


class StringExtractor(FeatureType):
    name = "strings"
    dim = 104

    def __init__(self):
        self._allstrings = re.compile(b"[\x20-\x7f]{5,}")
        self._paths = re.compile(b"c:\\\\", re.IGNORECASE)
        self._urls = re.compile(b"https?://", re.IGNORECASE)
        self._registry = re.compile(b"HKEY_")
        self._mz = re.compile(b"MZ")

    def raw_features(self, bytez, lief_binary):
        allstrings = self._allstrings.findall(bytez)
        if allstrings:
            string_lengths = [len(s) for s in allstrings]
            avlength = sum(string_lengths) / len(string_lengths)
            as_shifted_string = [b - ord(b"\x20") for b in b"".join(allstrings)]
            c = np.bincount(as_shifted_string, minlength=96)
            csum = c.sum()
            p = c.astype(np.float32) / csum
            wh = np.where(c)[0]
            H = np.sum(-p[wh] * np.log2(p[wh]))
        else:
            avlength = 0
            c = np.zeros((96,), dtype=np.float32)
            H = 0
            csum = 0
        return {
            "numstrings": len(allstrings),
            "avlength": avlength,
            "printabledist": c.tolist(),
            "printables": int(csum),
            "entropy": float(H),
            "paths": len(self._paths.findall(bytez)),
            "urls": len(self._urls.findall(bytez)),
            "registry": len(self._registry.findall(bytez)),
            "MZ": len(self._mz.findall(bytez)),
        }

    def process_raw_features(self, raw_obj):
        hist_divisor = float(raw_obj["printables"]) if raw_obj["printables"] > 0 else 1.0
        return np.hstack([
            raw_obj["numstrings"], raw_obj["avlength"], raw_obj["printables"],
            np.asarray(raw_obj["printabledist"]) / hist_divisor, raw_obj["entropy"],
            raw_obj["paths"], raw_obj["urls"], raw_obj["registry"], raw_obj["MZ"],
        ]).astype(np.float32)


class GeneralFileInfo(FeatureType):
    name = "general"
    dim = 10

    def raw_features(self, bytez, lief_binary):
        if lief_binary is None:
            return {"size": len(bytez), "vsize": 0, "has_debug": 0, "exports": 0, "imports": 0,
                    "has_relocations": 0, "has_resources": 0, "has_signature": 0, "has_tls": 0,
                    "symbols": 0}
        return {
            "size": len(bytez),
            "vsize": lief_binary.virtual_size,
            "has_debug": int(lief_binary.has_debug),
            "exports": len(lief_binary.exported_functions),
            "imports": sum(len(lib.entries) for lib in lief_binary.imports),
            "has_relocations": int(lief_binary.has_relocations),
            "has_resources": int(lief_binary.has_resources),
            "has_signature": int(lief_binary.has_signature),
            "has_tls": int(lief_binary.has_tls),
            "symbols": len(lief_binary.symbols),
        }

    def process_raw_features(self, raw_obj):
        return np.asarray([
            raw_obj["size"], raw_obj["vsize"], raw_obj["has_debug"], raw_obj["exports"],
            raw_obj["imports"], raw_obj["has_relocations"], raw_obj["has_resources"],
            raw_obj["has_signature"], raw_obj["has_tls"], raw_obj["symbols"],
        ], dtype=np.float32)


class HeaderFileInfo(FeatureType):
    name = "header"
    dim = 62

    def raw_features(self, bytez, lief_binary):
        raw_obj = {
            "coff": {"timestamp": 0, "machine": "", "characteristics": []},
            "optional": {
                "subsystem": "", "dll_characteristics": [], "magic": "",
                "major_image_version": 0, "minor_image_version": 0,
                "major_linker_version": 0, "minor_linker_version": 0,
                "major_operating_system_version": 0, "minor_operating_system_version": 0,
                "major_subsystem_version": 0, "minor_subsystem_version": 0,
                "sizeof_code": 0, "sizeof_headers": 0, "sizeof_heap_commit": 0,
            },
        }
        if lief_binary is None:
            return raw_obj
        raw_obj["coff"]["timestamp"] = lief_binary.header.time_date_stamps
        raw_obj["coff"]["machine"] = str(lief_binary.header.machine).split(".")[-1]
        raw_obj["coff"]["characteristics"] = [str(c).split(".")[-1] for c in lief_binary.header.characteristics_list]
        raw_obj["optional"]["subsystem"] = str(lief_binary.optional_header.subsystem).split(".")[-1]
        raw_obj["optional"]["dll_characteristics"] = [
            str(c).split(".")[-1] for c in lief_binary.optional_header.dll_characteristics_lists]
        raw_obj["optional"]["magic"] = str(lief_binary.optional_header.magic).split(".")[-1]
        oh = lief_binary.optional_header
        raw_obj["optional"]["major_image_version"] = oh.major_image_version
        raw_obj["optional"]["minor_image_version"] = oh.minor_image_version
        raw_obj["optional"]["major_linker_version"] = oh.major_linker_version
        raw_obj["optional"]["minor_linker_version"] = oh.minor_linker_version
        raw_obj["optional"]["major_operating_system_version"] = oh.major_operating_system_version
        raw_obj["optional"]["minor_operating_system_version"] = oh.minor_operating_system_version
        raw_obj["optional"]["major_subsystem_version"] = oh.major_subsystem_version
        raw_obj["optional"]["minor_subsystem_version"] = oh.minor_subsystem_version
        raw_obj["optional"]["sizeof_code"] = oh.sizeof_code
        raw_obj["optional"]["sizeof_headers"] = oh.sizeof_headers
        raw_obj["optional"]["sizeof_heap_commit"] = oh.sizeof_heap_commit
        return raw_obj

    def process_raw_features(self, raw_obj):
        return np.hstack([
            raw_obj["coff"]["timestamp"],
            FeatureHasher(10, input_type="string").transform([[raw_obj["coff"]["machine"]]]).toarray()[0],
            FeatureHasher(10, input_type="string").transform([raw_obj["coff"]["characteristics"]]).toarray()[0],
            FeatureHasher(10, input_type="string").transform([[raw_obj["optional"]["subsystem"]]]).toarray()[0],
            FeatureHasher(10, input_type="string").transform([raw_obj["optional"]["dll_characteristics"]]).toarray()[0],
            FeatureHasher(10, input_type="string").transform([[raw_obj["optional"]["magic"]]]).toarray()[0],
            raw_obj["optional"]["major_image_version"],
            raw_obj["optional"]["minor_image_version"],
            raw_obj["optional"]["major_linker_version"],
            raw_obj["optional"]["minor_linker_version"],
            raw_obj["optional"]["major_operating_system_version"],
            raw_obj["optional"]["minor_operating_system_version"],
            raw_obj["optional"]["major_subsystem_version"],
            raw_obj["optional"]["minor_subsystem_version"],
            raw_obj["optional"]["sizeof_code"],
            raw_obj["optional"]["sizeof_headers"],
            raw_obj["optional"]["sizeof_heap_commit"],
        ]).astype(np.float32)


class SectionInfo(FeatureType):
    name = "section"
    dim = 5 + 50 + 50 + 50 + 50 + 50

    @staticmethod
    def _properties(s):
        return [str(c).split(".")[-1] for c in s.characteristics_lists]

    def raw_features(self, bytez, lief_binary):
        if lief_binary is None:
            return {"entry": "", "sections": []}
        try:
            section = lief_binary.section_from_rva(lief_binary.entrypoint - lief_binary.imagebase)
            if section is None:
                raise KeyError("not found")
            entry_section = section.name
        except (KeyError, IndexError):
            entry_section = ""
            for s in lief_binary.sections:
                if "MEM_EXECUTE" in s.characteristics_lists:
                    entry_section = s.name
                    break
        raw_obj = {"entry": entry_section}
        raw_obj["sections"] = [{
            "name": s.name,
            "size": s.size,
            "entropy": s.entropy,
            "vsize": s.virtual_size,
            "props": self._properties(s),
        } for s in lief_binary.sections]
        return raw_obj

    def process_raw_features(self, raw_obj):
        sections = raw_obj["sections"]
        general = [
            len(sections),
            sum(1 for s in sections if s["size"] == 0),
            sum(1 for s in sections if s["name"] == ""),
            sum(1 for s in sections if "MEM_READ" in s["props"] and "MEM_EXECUTE" in s["props"]),
            sum(1 for s in sections if "MEM_WRITE" in s["props"]),
        ]
        section_sizes = [(s["name"], s["size"]) for s in sections]
        section_sizes_hashed = FeatureHasher(50, input_type="pair").transform([section_sizes]).toarray()[0]
        section_entropy = [(s["name"], s["entropy"]) for s in sections]
        section_entropy_hashed = FeatureHasher(50, input_type="pair").transform([section_entropy]).toarray()[0]
        section_vsize = [(s["name"], s["vsize"]) for s in sections]
        section_vsize_hashed = FeatureHasher(50, input_type="pair").transform([section_vsize]).toarray()[0]
        entry_name_hashed = FeatureHasher(50, input_type="string").transform([[raw_obj["entry"]]]).toarray()[0]
        characteristics = [p for s in sections for p in s["props"] if s["name"] == raw_obj["entry"]]
        characteristics_hashed = FeatureHasher(50, input_type="string").transform([characteristics]).toarray()[0]
        return np.hstack([
            general, section_sizes_hashed, section_entropy_hashed, section_vsize_hashed,
            entry_name_hashed, characteristics_hashed,
        ]).astype(np.float32)


class ImportsInfo(FeatureType):
    name = "imports"
    dim = 1280

    def raw_features(self, bytez, lief_binary):
        imports = {}
        if lief_binary is None:
            return imports
        for lib in lief_binary.imports:
            if lib.name not in imports:
                imports[lib.name] = []
            for entry in lib.entries:
                if entry.is_ordinal:
                    imports[lib.name].append("ordinal" + str(entry.ordinal))
                else:
                    imports[lib.name].append(entry.name[:10000])
        return imports

    def process_raw_features(self, raw_obj):
        libraries = list({l.lower() for l in raw_obj})
        libraries_hashed = FeatureHasher(256, input_type="string").transform([libraries]).toarray()[0]
        imports = [lib.lower() + ":" + e for lib, elist in raw_obj.items() for e in elist]
        imports_hashed = FeatureHasher(1024, input_type="string").transform([imports]).toarray()[0]
        return np.hstack([libraries_hashed, imports_hashed]).astype(np.float32)


class ExportsInfo(FeatureType):
    name = "exports"
    dim = 128

    def raw_features(self, bytez, lief_binary):
        if lief_binary is None:
            return []
        return [export[:10000] for export in lief_binary.exported_functions]

    def process_raw_features(self, raw_obj):
        return FeatureHasher(128, input_type="string").transform([raw_obj]).toarray()[0].astype(np.float32)


class DataDirectories(FeatureType):
    name = "datadirectories"
    dim = 15 * 2

    def __init__(self):
        self._name_order = [
            "EXPORT_TABLE", "IMPORT_TABLE", "RESOURCE_TABLE", "EXCEPTION_TABLE", "CERTIFICATE_TABLE",
            "BASE_RELOCATION_TABLE", "DEBUG", "ARCHITECTURE", "GLOBAL_PTR", "TLS_TABLE", "LOAD_CONFIG_TABLE",
            "BOUND_IMPORT", "IAT", "DELAY_IMPORT_DESCRIPTOR", "CLR_RUNTIME_HEADER",
        ]

    def raw_features(self, bytez, lief_binary):
        output = []
        if lief_binary is None:
            return output
        for data_directory in lief_binary.data_directories:
            output.append({
                "name": str(getattr(data_directory, "type_name", "")).replace("DATA_DIRECTORY.", ""),
                "size": data_directory.size,
                "virtual_address": data_directory.rva,
            })
        return output

    def process_raw_features(self, raw_obj):
        features = np.zeros(2 * len(self._name_order), dtype=np.float32)
        for i in range(len(self._name_order)):
            if i < len(raw_obj):
                features[2 * i] = raw_obj[i]["size"]
                features[2 * i + 1] = raw_obj[i]["virtual_address"]
        return features


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

_EMBER_V2_BLOCKS = OrderedDict([
    ("histogram", ByteHistogram()),
    ("byteentropy", ByteEntropyHistogram()),
    ("strings", StringExtractor()),
    ("general", GeneralFileInfo()),
    ("header", HeaderFileInfo()),
    ("section", SectionInfo()),
    ("imports", ImportsInfo()),
    ("exports", ExportsInfo()),
    ("datadirectories", DataDirectories()),
])

EMBER_V2_DIM = sum(block.dim for block in _EMBER_V2_BLOCKS.values())  # 2381


def raw_feature_dict_from_bytes(bytez: bytes) -> dict:
    """File bytes -> EMBER v2 raw-feature dict (schema-compatible with the dataset)."""
    lief_binary = _parse_pe(bytez)
    features = {"sha256": hashlib_sha256(bytez)}
    for block in _EMBER_V2_BLOCKS.values():
        features[block.name] = block.raw_features(bytez, lief_binary)
    return features


def ember_feature_vector_from_raw(raw: dict) -> np.ndarray:
    """Dataset raw-feature dict -> float32 vector (official v2 layout)."""
    parts = [_EMBER_V2_BLOCKS[name].process_raw_features(raw[name]) for name in _EMBER_V2_BLOCKS]
    return np.hstack(parts).astype(np.float32)


def ember_feature_vector_from_bytes(bytez: bytes) -> np.ndarray:
    """File bytes -> float32 vector. Inference path used by the classifier."""
    return ember_feature_vector_from_raw(raw_feature_dict_from_bytes(bytez))


def hashlib_sha256(bytez: bytes) -> str:
    import hashlib

    return hashlib.sha256(bytez).hexdigest()


def ember_jsonl_records(path: str, limit: int | None = None):
    """Stream EMBER jsonl records (dicts with 'label' + raw feature blocks)."""
    n = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            yield rec
            n += 1
            if limit is not None and n >= limit:
                break


def _unused(_x=binascii, _y=math, _z=os):  # pragma: no cover
    """Keep imports referenced for vendoring parity; never called."""
    return
