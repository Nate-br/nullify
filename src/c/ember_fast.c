#include "nullify.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

static void entropy_bin_counts(const uint8_t *block, size_t block_len, size_t window, int *out_hbin, int64_t *out_c) {
    memset(out_c, 0, sizeof(int64_t) * 16);

    for (size_t i = 0; i < block_len; ++i) {
        uint8_t nibble = block[i] >> 4;
        out_c[nibble]++;
    }

    double H = 0.0;
    double inv_window = 1.0 / (double)window;

    for (int i = 0; i < 16; ++i) {
        if (out_c[i] > 0) {
            double p = (double)out_c[i] * inv_window;
            H += -p * log2(p);
        }
    }

    H *= 2.0;
    int Hbin = (int)(H * 2.0);
    if (Hbin >= 16) {
        Hbin = 15;
    }
    if (Hbin < 0) {
        Hbin = 0;
    }
    *out_hbin = Hbin;
}

void nullify_byte_entropy_histogram(
    const uint8_t *data,
    size_t len,
    size_t step,
    size_t window,
    int64_t out_matrix[256]
) {
    if (!out_matrix) return;
    memset(out_matrix, 0, sizeof(int64_t) * 256);

    if (!data || len == 0) return;
    if (window == 0) window = 2048;
    if (step == 0) step = 1024;

    int64_t c[16];
    int hbin = 0;

    if (len < window) {
        entropy_bin_counts(data, len, window, &hbin, c);
        for (int j = 0; j < 16; ++j) {
            out_matrix[hbin * 16 + j] += c[j];
        }
    } else {
        for (size_t offset = 0; offset + window <= len; offset += step) {
            entropy_bin_counts(data + offset, window, window, &hbin, c);
            for (int j = 0; j < 16; ++j) {
                out_matrix[hbin * 16 + j] += c[j];
            }
        }
    }
}

static int iequals_prefix(const uint8_t *data, const char *prefix, size_t n) {
    for (size_t k = 0; k < n; ++k) {
        if (tolower(data[k]) != tolower((unsigned char)prefix[k])) {
            return 0;
        }
    }
    return 1;
}

void nullify_extract_strings(
    const uint8_t *data,
    size_t len,
    nullify_string_stats_t *out_stats
) {
    if (!out_stats) return;
    memset(out_stats, 0, sizeof(nullify_string_stats_t));
    if (!data || len == 0) return;

    size_t current_len = 0;
    size_t total_str_bytes = 0;
    uint32_t string_count = 0;

    /* Single pass over the data */
    for (size_t i = 0; i <= len; ++i) {
        uint8_t b = (i < len) ? data[i] : 0;
        int is_printable = (b >= 0x20 && b <= 0x7E);

        if (is_printable) {
            current_len++;
        } else {
            if (current_len >= 5) {
                string_count++;
                total_str_bytes += current_len;
                size_t start = i - current_len;
                for (size_t j = 0; j < current_len; ++j) {
                    uint8_t ch = data[start + j];
                    out_stats->char_counts[ch - 0x20]++;
                }
            }
            current_len = 0;
        }

        /* Keyword and heuristic scans */
        if (i + 2 <= len) {
            if (data[i] == 'M' && data[i + 1] == 'Z') {
                out_stats->num_mz++;
            }
        }
        if (i + 3 <= len) {
            if ((data[i] == 'c' || data[i] == 'C') && data[i + 1] == ':' && data[i + 2] == '\\') {
                out_stats->num_paths++;
            }
        }
        if (i + 5 <= len) {
            if (memcmp(data + i, "HKEY_", 5) == 0) {
                out_stats->num_registry++;
            }
        }
        if (i + 7 <= len) {
            if (iequals_prefix(data + i, "http://", 7)) {
                out_stats->num_urls++;
            }
        }
        if (i + 8 <= len) {
            if (iequals_prefix(data + i, "https://", 8)) {
                out_stats->num_urls++;
            }
        }
    }

    out_stats->count = string_count;
    if (string_count > 0) {
        out_stats->avg_length = (double)total_str_bytes / (double)string_count;
    }

    /* Calculate printable character distribution entropy */
    if (total_str_bytes > 0) {
        double H = 0.0;
        double inv_total = 1.0 / (double)total_str_bytes;
        for (int k = 0; k < 96; ++k) {
            if (out_stats->char_counts[k] > 0) {
                double p = (double)out_stats->char_counts[k] * inv_total;
                H += -p * log2(p);
            }
        }
        out_stats->char_entropy = H;
    }
}
