#include "nullify.h"
#include "hash.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static uint16_t read_u16_le(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t read_u32_le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void parse_pe(const uint8_t *data, size_t len, nullify_triage_result_t *res) {
    res->magic = NULLIFY_MAGIC_PE;
    res->is_executable = 1;

    if (len < 0x40) {
        snprintf(res->architecture, sizeof(res->architecture), "PE (truncated)");
        return;
    }

    uint32_t pe_offset = read_u32_le(data + 0x3C);
    if (pe_offset + 24 > len) {
        snprintf(res->architecture, sizeof(res->architecture), "PE (corrupt header)");
        return;
    }

    if (memcmp(data + pe_offset, "PE\0\0", 4) != 0) {
        snprintf(res->architecture, sizeof(res->architecture), "MS-DOS");
        return;
    }

    uint16_t machine = read_u16_le(data + pe_offset + 4);
    uint16_t num_sections = read_u16_le(data + pe_offset + 6);
    uint16_t size_optional_header = read_u16_le(data + pe_offset + 20);

    res->num_sections = (int32_t)num_sections;

    switch (machine) {
        case 0x014C: snprintf(res->architecture, sizeof(res->architecture), "I386"); break;
        case 0x8664: snprintf(res->architecture, sizeof(res->architecture), "AMD64"); break;
        case 0xAA64: snprintf(res->architecture, sizeof(res->architecture), "ARM64"); break;
        case 0x01C0: snprintf(res->architecture, sizeof(res->architecture), "ARM"); break;
        case 0x0200: snprintf(res->architecture, sizeof(res->architecture), "IA64"); break;
        default:     snprintf(res->architecture, sizeof(res->architecture), "PE-0x%04X", machine); break;
    }

    /* Optional Header & Entrypoint */
    uint32_t entry_point_rva = 0;
    if (size_optional_header >= 28 && (pe_offset + 24 + size_optional_header) <= len) {
        uint16_t opt_magic = read_u16_le(data + pe_offset + 24);
        if (opt_magic == 0x10B || opt_magic == 0x20B) {
            entry_point_rva = read_u32_le(data + pe_offset + 24 + 16);
        }
    }

    /* Section Table Parsing */
    size_t section_table_offset = pe_offset + 24 + size_optional_header;
    int found_entry_sec = 0;

    for (uint16_t i = 0; i < num_sections; ++i) {
        size_t sec_offset = section_table_offset + (i * 40);
        if (sec_offset + 40 > len) break;

        char sec_name[9];
        memset(sec_name, 0, sizeof(sec_name));
        memcpy(sec_name, data + sec_offset, 8);

        uint32_t virt_size = read_u32_le(data + sec_offset + 8);
        uint32_t virt_addr = read_u32_le(data + sec_offset + 12);
        uint32_t raw_size  = read_u32_le(data + sec_offset + 16);

        /* Check for known packer signatures */
        if (strstr(sec_name, "UPX") != NULL ||
            strstr(sec_name, "aspack") != NULL ||
            strstr(sec_name, "ASPack") != NULL ||
            strstr(sec_name, "MPRESS") != NULL ||
            strstr(sec_name, "fsg") != NULL ||
            strstr(sec_name, "PEC2") != NULL) {
            res->is_packed = 1;
        }

        /* Detect virtual size significantly larger than raw data size (common in unpackers) */
        if (raw_size > 0 && virt_size > (raw_size * 4) && virt_size > 65536) {
            res->is_packed = 1;
        }

        /* Match entry point */
        if (!found_entry_sec && entry_point_rva > 0) {
            uint32_t effective_size = virt_size ? virt_size : raw_size;
            if (entry_point_rva >= virt_addr && entry_point_rva < virt_addr + effective_size) {
                snprintf(res->entry_section, sizeof(res->entry_section), "%s", sec_name);
                found_entry_sec = 1;
            }
        }
    }

    if (!found_entry_sec && num_sections > 0) {
        /* Fallback: use first section name */
        char first_sec[9];
        memset(first_sec, 0, sizeof(first_sec));
        memcpy(first_sec, data + section_table_offset, 8);
        snprintf(res->entry_section, sizeof(res->entry_section), "%s", first_sec);
    }
}

static void parse_elf(const uint8_t *data, size_t len, nullify_triage_result_t *res) {
    res->magic = NULLIFY_MAGIC_ELF;
    res->is_executable = 1;

    if (len < 16) {
        snprintf(res->architecture, sizeof(res->architecture), "ELF (truncated)");
        return;
    }

    uint8_t elf_class = data[4];     /* 1 = 32-bit, 2 = 64-bit */
    uint8_t elf_data = data[5];      /* 1 = little-endian, 2 = big-endian */

    if (len < (elf_class == 2 ? 64 : 52)) {
        snprintf(res->architecture, sizeof(res->architecture), "ELF (truncated header)");
        return;
    }

    uint16_t machine = 0;
    if (elf_data == 1) {
        machine = read_u16_le(data + 18);
    } else {
        machine = ((uint16_t)data[18] << 8) | (uint16_t)data[19];
    }

    const char *arch_str = "ELF";
    switch (machine) {
        case 0x03: arch_str = (elf_class == 2 ? "x86_64" : "I386"); break;
        case 0x3E: arch_str = "AMD64"; break;
        case 0x28: arch_str = "ARM"; break;
        case 0xB7: arch_str = "ARM64"; break;
        case 0xF3: arch_str = "RISCV"; break;
        case 0x08: arch_str = "MIPS"; break;
        default: break;
    }

    snprintf(res->architecture, sizeof(res->architecture), "%s (%s)",
             arch_str, (elf_class == 2 ? "64-bit" : "32-bit"));

    /* Section count */
    if (elf_class == 2 && len >= 62) {
        res->num_sections = (int32_t)read_u16_le(data + 60);
    } else if (elf_class == 1 && len >= 50) {
        res->num_sections = (int32_t)read_u16_le(data + 48);
    }
}

int nullify_triage_buffer(const uint8_t *data, size_t len, nullify_triage_result_t *res) {
    if (!res) return -1;
    memset(res, 0, sizeof(nullify_triage_result_t));

    res->size_bytes = (uint64_t)len;

    if (!data || len == 0) {
        snprintf(res->architecture, sizeof(res->architecture), "empty");
        return 0;
    }

    /* Hashes */
    nullify_md5(data, len, res->md5);
    nullify_sha1(data, len, res->sha1);
    nullify_sha256(data, len, res->sha256);

    /* Shannon Entropy */
    res->entropy = nullify_entropy(data, len);

    /* Sniff Magic Bytes */
    if (len >= 2 && data[0] == 'M' && data[1] == 'Z') {
        parse_pe(data, len, res);
    } else if (len >= 4 && data[0] == 0x7F && data[1] == 'E' && data[2] == 'L' && data[3] == 'F') {
        parse_elf(data, len, res);
    } else if (len >= 2 && data[0] == '#' && data[1] == '!') {
        res->magic = NULLIFY_MAGIC_SCRIPT;
        res->is_executable = 1;
        snprintf(res->architecture, sizeof(res->architecture), "Script");
    } else {
        res->magic = NULLIFY_MAGIC_UNKNOWN;
        res->is_executable = 0;
        snprintf(res->architecture, sizeof(res->architecture), "Data / Unknown");
    }

    /* Check if target is an AppImage (Type 1 or 2 magic 'AI\x01' or 'AI\x02' in ELF e_ident) */
    int is_appimage = (len >= 11 && data[0] == 0x7F && data[1] == 'E' && data[2] == 'L' && data[3] == 'F' &&
                       data[8] == 'A' && data[9] == 'I' && (data[10] == 0x01 || data[10] == 0x02));

    /* Entropy heuristic for packed binary (exclude compressed AppImage application bundles) */
    if (res->is_executable && res->entropy >= 7.2 && !is_appimage) {
        res->is_packed = 1;
    }

    return 0;
}

int nullify_triage_file(const char *path, nullify_triage_result_t *res) {
    if (!path || !res) return -1;

    FILE *f = fopen(path, "rb");
    if (!f) {
        return -2;
    }

    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return -3;
    }

    long file_len = ftell(f);
    if (file_len < 0) {
        fclose(f);
        return -3;
    }
    rewind(f);

    size_t size = (size_t)file_len;
    uint8_t *buf = NULL;

    if (size > 0) {
        buf = (uint8_t *)malloc(size);
        if (!buf) {
            fclose(f);
            return -4;
        }

        size_t read_bytes = fread(buf, 1, size, f);
        if (read_bytes != size) {
            free(buf);
            fclose(f);
            return -5;
        }
    }

    fclose(f);

    int rc = nullify_triage_buffer(buf, size, res);
    if (buf) {
        free(buf);
    }

    return rc;
}
