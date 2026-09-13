#include "nullify.h"
#include <math.h>
#include <string.h>

double nullify_entropy(const uint8_t *data, size_t len) {
    if (!data || len == 0) {
        return 0.0;
    }

    uint64_t freq[256];
    memset(freq, 0, sizeof(freq));

    for (size_t i = 0; i < len; ++i) {
        freq[data[i]]++;
    }

    double entropy = 0.0;
    double inv_len = 1.0 / (double)len;

    for (int i = 0; i < 256; ++i) {
        if (freq[i] > 0) {
            double p = (double)freq[i] * inv_len;
            entropy -= p * log2(p);
        }
    }

    return entropy;
}

void nullify_byte_histogram(const uint8_t *data, size_t len, uint32_t out_histogram[256]) {
    if (!out_histogram) return;
    memset(out_histogram, 0, sizeof(uint32_t) * 256);

    if (!data || len == 0) return;

    for (size_t i = 0; i < len; ++i) {
        out_histogram[data[i]]++;
    }
}
