#ifndef NULLIFY_H
#define NULLIFY_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef BUILDING_NULLIFY
    #define NULLIFY_API __declspec(dllexport)
  #else
    #define NULLIFY_API __declspec(dllimport)
  #endif
#else
  #if defined(__GNUC__) && __GNUC__ >= 4
    #define NULLIFY_API __attribute__((visibility("default")))
  #else
    #define NULLIFY_API
  #endif
#endif

typedef enum {
    NULLIFY_MAGIC_UNKNOWN = 0,
    NULLIFY_MAGIC_PE      = 1,
    NULLIFY_MAGIC_ELF     = 2,
    NULLIFY_MAGIC_SCRIPT  = 3
} nullify_magic_t;

typedef struct {
    uint64_t size_bytes;
    double entropy;
    int32_t magic;              /* nullify_magic_t */
    char architecture[32];      /* e.g., "AMD64", "I386", "ARM64", "ELF64" */
    int32_t is_executable;
    int32_t is_packed;
    int32_t num_sections;
    char entry_section[32];
    char md5[33];
    char sha1[41];
    char sha256[65];
} nullify_triage_result_t;

typedef struct {
    uint32_t count;
    double avg_length;
    uint32_t char_counts[96];   /* Printable ASCII 0x20..0x7E counts */
    double char_entropy;
    uint32_t num_paths;         /* Matches for c:\ */
    uint32_t num_urls;          /* Matches for http:// or https:// */
    uint32_t num_registry;      /* Matches for HKEY_ */
    uint32_t num_mz;            /* Matches for MZ */
} nullify_string_stats_t;

typedef struct {
    uint32_t total_imports;
    uint32_t total_libraries;
    char libraries[32][64];
    uint32_t trojan_hits;
    uint32_t spyware_hits;
    uint32_t ransomware_hits;
    uint32_t worm_hits;
    uint32_t rootkit_hits;
    char matched_apis[64][64];
    char matched_families[64][16];
    uint32_t matched_count;
} nullify_pe_imports_result_t;

typedef struct {
    uint32_t has_registry_run;
    uint32_t has_scheduled_task;
    uint32_t has_powershell_cradle;
    uint32_t has_hardcoded_ip;
    uint32_t has_drop_path;
    uint32_t has_ransom_note;
    char match_snippets[6][128];
} nullify_pattern_matches_t;

/* --- Core Functions --- */

/**
 * Compute Shannon entropy over buffer [0.0 .. 8.0].
 */
NULLIFY_API double nullify_entropy(const uint8_t *data, size_t len);

/**
 * Triage raw memory buffer.
 */
NULLIFY_API int nullify_triage_buffer(const uint8_t *data, size_t len, nullify_triage_result_t *res);

/**
 * Triage file path directly using streaming buffer/mmap.
 */
NULLIFY_API int nullify_triage_file(const char *path, nullify_triage_result_t *res);

/**
 * Compute all 3 hashes (MD5, SHA1, SHA256) over buffer or file.
 */
NULLIFY_API void nullify_hashes_buffer(const uint8_t *data, size_t len, char md5[33], char sha1[41], char sha256[65]);
NULLIFY_API int nullify_hashes_file(const char *path, char md5[33], char sha1[41], char sha256[65]);

/**
 * Compute 256-bin byte frequency histogram over raw buffer.
 */
NULLIFY_API void nullify_byte_histogram(const uint8_t *data, size_t len, uint32_t out_histogram[256]);

/**
 * Compute 2D (16x16) Byte Entropy Histogram over sliding window (EMBER specification).
 * Output is 256 int64 elements.
 */
NULLIFY_API void nullify_byte_entropy_histogram(
    const uint8_t *data,
    size_t len,
    size_t step,
    size_t window,
    int64_t out_matrix[256]
);

/**
 * Extract ASCII string statistics and heuristics (length, 96-bin distribution, entropy).
 */
NULLIFY_API void nullify_extract_strings(
    const uint8_t *data,
    size_t len,
    nullify_string_stats_t *out_stats
);

/**
 * Fast native PE import table parsing and malicious capability classification.
 */
NULLIFY_API int nullify_parse_pe_imports(
    const uint8_t *data,
    size_t len,
    nullify_pe_imports_result_t *out_imports
);

/**
 * Fast native multi-pattern scanner for suspicious strings, registry keys, and drop paths.
 */
NULLIFY_API int nullify_scan_suspicious_patterns(
    const uint8_t *data,
    size_t len,
    nullify_pattern_matches_t *out_matches
);

#ifdef __cplusplus
}
#endif

#endif /* NULLIFY_H */
