import re
from pathlib import Path

import numpy as np
import pefile


def extract_features(file_path: Path | str) -> np.ndarray:
    """
    EMBER-style feature extraction from a PE file.
    Outputs a fixed-length numeric vector (2351 dimensions to match EMBER dataset).
    Works degraded on non-PE files.
    """
    path = Path(file_path)
    features = np.zeros(2351, dtype=np.float32)
    if not path.exists():
        return features
        
    try:
        data = path.read_bytes()
    except Exception:  # noqa: BLE001
        return features

    if not data:
        return features

    # 1. Byte histogram (256 dims) - index 0 to 255
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    features[0:256] = counts / len(data)
    
    # 2. Byte entropy histogram (256 dims) - EMBER uses a sliding window, we'll approximate or leave zero to avoid slow computation
    # For now, leaving as zeros (index 256 to 511)
    
    # 3. String statistics (104 dims) - index 512 to 615
    strings = re.findall(b'[\x20-\x7e]{5,}', data)
    if strings:
        lengths = [len(s) for s in strings]
        features[512] = len(strings)
        features[513] = np.mean(lengths)
        features[514] = np.max(lengths)
        # 95 printable chars histogram (index 515 to 609)
        string_chars = b''.join(strings)
        char_counts = np.bincount(np.frombuffer(string_chars, dtype=np.uint8), minlength=256)
        if len(string_chars) > 0:
            features[515:610] = (char_counts[32:127] / len(string_chars))
    
    # PE specific features
    try:
        pe = pefile.PE(data=data, fast_load=True)
        # We degrade gracefully if not PE
        
        # 4. General file info (10 dims) - index 616 to 625
        features[616] = len(pe.sections)
        # 5. Header info (62 dims) - index 626 to 687
        features[626] = pe.FILE_HEADER.Machine
        features[627] = pe.FILE_HEADER.TimeDateStamp
        
        # 6. Section info (255 dims) - index 688 to 942
        # Calculate section entropy
        entropies = []
        for section in pe.sections:
            sec_data = section.get_data()
            if sec_data:
                scounts = np.bincount(np.frombuffer(sec_data, dtype=np.uint8), minlength=256)
                p = scounts / len(sec_data)
                p = p[p > 0]
                ent = -np.sum(p * np.log2(p))
                entropies.append(ent)
        if entropies:
            features[688] = np.min(entropies)
            features[689] = np.mean(entropies)
            features[690] = np.max(entropies)
            
        # 7. Imports info (1280 dims) - index 943 to 2222
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]
        ])
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            libs = []
            funcs = []
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                if entry.dll:
                    libs.append(entry.dll.decode('utf-8', 'ignore').lower())
                if entry.imports:
                    for imp in entry.imports:
                        if imp.name:
                            funcs.append(imp.name.decode('utf-8', 'ignore').lower())
            
            # Simple feature hashing for imports
            for lib in libs:
                idx = hash(lib) % 256
                features[943 + idx] += 1.0
            for func in funcs:
                idx = hash(func) % 1024
                features[943 + 256 + idx] += 1.0
                
        # 8. Exports info (128 dims) - index 2223 to 2350
        # Not heavily used, leaving zeros or simple hash
            
    except pefile.PEFormatError:
        pass # Non-PE file, gracefully degraded
        
    return features
