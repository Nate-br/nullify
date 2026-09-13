#include "nullify.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static uint16_t read_u16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t read_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t read_u64(const uint8_t *p) {
    return (uint64_t)read_u32(p) | ((uint64_t)read_u32(p + 4) << 32);
}

typedef struct {
    const char *name;
    const char *family;
} known_api_hint_t;

static const known_api_hint_t KNOWN_APIS[] = {
    {"URLDownloadToFile", "trojan"},
    {"WinExec", "trojan"},
    {"CreateRemoteThread", "trojan"},
    {"ShellExecute", "trojan"},
    {"InternetOpenUrl", "trojan"},
    {"WSAStartup", "trojan"},
    {"InternetConnect", "trojan"},

    {"SetWindowsHookEx", "spyware"},
    {"GetAsyncKeyState", "spyware"},
    {"BitBlt", "spyware"},
    {"GetClipboardData", "spyware"},
    {"GetKeyState", "spyware"},
    {"WaveOut", "spyware"},

    {"CryptEncrypt", "ransomware"},
    {"CryptGenKey", "ransomware"},
    {"CryptAcquireContext", "ransomware"},
    {"FindFirstFile", "ransomware"},
    {"WriteFile", "ransomware"},
    {"DeleteFile", "ransomware"},

    {"WNetOpenEnum", "worm"},
    {"WNetEnumResource", "worm"},
    {"NetShareEnum", "worm"},
    {"CreateFile", "worm"},
    {"CopyFile", "worm"},

    {"DeviceIoControl", "rootkit"},
    {"NtLoadDriver", "rootkit"},
    {"ZwLoadDriver", "rootkit"},
    {"OpenSCManager", "rootkit"},
    {"CreateService", "rootkit"},
    {NULL, NULL}
};

static void record_api_match(nullify_pe_imports_result_t *out, const char *api, const char *family) {
    for (uint32_t i = 0; i < out->matched_count; ++i) {
        if (strcmp(out->matched_apis[i], api) == 0) {
            return; /* already recorded */
        }
    }

    if (out->matched_count < 64) {
        snprintf(out->matched_apis[out->matched_count], 64, "%s", api);
        snprintf(out->matched_families[out->matched_count], 16, "%s", family);
        out->matched_count++;
    }

    if (strcmp(family, "trojan") == 0) out->trojan_hits++;
    else if (strcmp(family, "spyware") == 0) out->spyware_hits++;
    else if (strcmp(family, "ransomware") == 0) out->ransomware_hits++;
    else if (strcmp(family, "worm") == 0) out->worm_hits++;
    else if (strcmp(family, "rootkit") == 0) out->rootkit_hits++;
}

static size_t rva_to_file_offset(
    uint32_t rva,
    const uint8_t *data,
    size_t len,
    size_t section_headers_offset,
    uint16_t num_sections
) {
    for (uint16_t i = 0; i < num_sections; ++i) {
        size_t sec_offset = section_headers_offset + (i * 40);
        if (sec_offset + 40 > len) break;

        uint32_t virt_size = read_u32(data + sec_offset + 8);
        uint32_t virt_addr = read_u32(data + sec_offset + 12);
        uint32_t raw_size  = read_u32(data + sec_offset + 16);
        uint32_t raw_ptr   = read_u32(data + sec_offset + 20);

        uint32_t eff_size = virt_size ? virt_size : raw_size;
        if (rva >= virt_addr && rva < virt_addr + eff_size) {
            size_t diff = rva - virt_addr;
            if (raw_ptr + diff < len) {
                return raw_ptr + diff;
            }
        }
    }
    return 0;
}

int nullify_parse_pe_imports(
    const uint8_t *data,
    size_t len,
    nullify_pe_imports_result_t *out
) {
    if (!out) return -1;
    memset(out, 0, sizeof(nullify_pe_imports_result_t));

    if (!data || len < 0x40) return -2;
    if (data[0] != 'M' || data[1] != 'Z') return -3;

    uint32_t pe_offset = read_u32(data + 0x3C);
    if (pe_offset + 24 > len || memcmp(data + pe_offset, "PE\0\0", 4) != 0) {
        goto fallback_search;
    }

    uint16_t num_sections = read_u16(data + pe_offset + 6);
    uint16_t size_opt_header = read_u16(data + pe_offset + 20);
    size_t opt_header_offset = pe_offset + 24;

    if (opt_header_offset + size_opt_header > len || size_opt_header < 28) {
        goto fallback_search;
    }

    uint16_t magic = read_u16(data + opt_header_offset);
    int is_64bit = (magic == 0x20B);

    /* Data directory offset: 96 for PE32 (at opt + 96), 112 for PE32+ (at opt + 112) */
    size_t data_dir_offset = opt_header_offset + (is_64bit ? 112 : 96);
    /* Import Directory is Entry index 1 */
    size_t import_dir_entry = data_dir_offset + (1 * 8);

    if (import_dir_entry + 8 > len) {
        goto fallback_search;
    }

    uint32_t import_rva = read_u32(data + import_dir_entry);
    uint32_t import_size = read_u32(data + import_dir_entry + 4);

    size_t section_headers_offset = opt_header_offset + size_opt_header;

    if (import_rva > 0 && import_size > 0) {
        size_t desc_offset = rva_to_file_offset(import_rva, data, len, section_headers_offset, num_sections);
        if (desc_offset > 0) {
            /* Traverse IMAGE_IMPORT_DESCRIPTOR array (20 bytes per entry) */
            for (size_t d = desc_offset; d + 20 <= len; d += 20) {
                uint32_t orig_thunk = read_u32(data + d);
                uint32_t name_rva   = read_u32(data + d + 12);
                uint32_t first_thunk = read_u32(data + d + 16);

                if (orig_thunk == 0 && name_rva == 0 && first_thunk == 0) {
                    break; /* End of descriptors */
                }

                /* Extract Library Name */
                size_t name_offset = rva_to_file_offset(name_rva, data, len, section_headers_offset, num_sections);
                if (name_offset > 0 && name_offset < len) {
                    if (out->total_libraries < 32) {
                        snprintf(out->libraries[out->total_libraries], 64, "%s", (const char *)(data + name_offset));
                        out->total_libraries++;
                    }
                }

                /* Traverse Thunks */
                uint32_t thunk_rva = orig_thunk ? orig_thunk : first_thunk;
                size_t thunk_offset = rva_to_file_offset(thunk_rva, data, len, section_headers_offset, num_sections);

                if (thunk_offset > 0) {
                    size_t t_ptr = thunk_offset;
                    while (t_ptr + (is_64bit ? 8 : 4) <= len) {
                        uint64_t val = is_64bit ? read_u64(data + t_ptr) : (uint64_t)read_u32(data + t_ptr);
                        t_ptr += (is_64bit ? 8 : 4);

                        if (val == 0) break;

                        /* Check if import by ordinal */
                        uint64_t ord_flag = is_64bit ? (1ULL << 63) : (1ULL << 31);
                        if (val & ord_flag) {
                            out->total_imports++;
                            continue;
                        }

                        /* Import by name: val is RVA pointing to IMAGE_IMPORT_BY_NAME */
                        size_t ibn_offset = rva_to_file_offset((uint32_t)val, data, len, section_headers_offset, num_sections);
                        if (ibn_offset + 2 < len) {
                            const char *fn_name = (const char *)(data + ibn_offset + 2);
                            out->total_imports++;

                            /* Match against known API hints */
                            for (int k = 0; KNOWN_APIS[k].name != NULL; ++k) {
                                if (strcmp(fn_name, KNOWN_APIS[k].name) == 0) {
                                    record_api_match(out, KNOWN_APIS[k].name, KNOWN_APIS[k].family);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

fallback_search:
    /* Fallback heuristic string search if import table had 0 matches or was obfuscated */
    if (out->matched_count == 0) {
        for (int k = 0; KNOWN_APIS[k].name != NULL; ++k) {
            size_t name_len = strlen(KNOWN_APIS[k].name);
            if (name_len > len) continue;

            for (size_t i = 0; i + name_len <= len; ++i) {
                if (data[i] == (uint8_t)KNOWN_APIS[k].name[0]) {
                    if (memcmp(data + i, KNOWN_APIS[k].name, name_len) == 0) {
                        record_api_match(out, KNOWN_APIS[k].name, KNOWN_APIS[k].family);
                        break;
                    }
                }
            }
        }
    }

    return 0;
}
