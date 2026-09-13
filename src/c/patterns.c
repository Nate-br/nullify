#include "nullify.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static int iequals_substr(const uint8_t *data, size_t data_len, const char *sub) {
    size_t sub_len = strlen(sub);
    if (sub_len > data_len) return 0;

    for (size_t i = 0; i + sub_len <= data_len; ++i) {
        size_t match = 0;
        for (size_t j = 0; j < sub_len; ++j) {
            if (tolower(data[i + j]) == tolower((unsigned char)sub[j])) {
                match++;
            } else {
                break;
            }
        }
        if (match == sub_len) return (int)i;
    }
    return -1;
}

static void save_snippet(char dest[128], const uint8_t *data, size_t len, size_t pos, size_t match_len) {
    size_t start = (pos > 10) ? pos - 10 : 0;
    size_t end = (pos + match_len + 20 < len) ? pos + match_len + 20 : len;
    size_t out_len = end - start;
    if (out_len > 120) out_len = 120;

    for (size_t i = 0; i < out_len; ++i) {
        uint8_t c = data[start + i];
        dest[i] = (c >= 0x20 && c <= 0x7E) ? (char)c : '.';
    }
    dest[out_len] = '\0';
}

int nullify_scan_suspicious_patterns(
    const uint8_t *data,
    size_t len,
    nullify_pattern_matches_t *out
) {
    if (!out) return -1;
    memset(out, 0, sizeof(nullify_pattern_matches_t));
    if (!data || len == 0) return 0;

    /* 1. Registry Run Key Persistence */
    int idx = iequals_substr(data, len, "CurrentVersion\\Run");
    if (idx < 0) idx = iequals_substr(data, len, "CurrentVersion\\\\Run");
    if (idx < 0) idx = iequals_substr(data, len, "Software\\Microsoft\\Windows\\CurrentVersion\\Run");
    if (idx >= 0) {
        out->has_registry_run = 1;
        save_snippet(out->match_snippets[0], data, len, (size_t)idx, 18);
    }

    /* 2. Scheduled Task Creation */
    idx = iequals_substr(data, len, "schtasks");
    if (idx < 0) idx = iequals_substr(data, len, "ITaskService");
    if (idx >= 0) {
        out->has_scheduled_task = 1;
        save_snippet(out->match_snippets[1], data, len, (size_t)idx, 8);
    }

    /* 3. PowerShell Download Cradle */
    idx = iequals_substr(data, len, "powershell");
    if (idx < 0) idx = iequals_substr(data, len, "pwsh");
    if (idx >= 0) {
        int cradle = iequals_substr(data + idx, (len > (size_t)idx + 256) ? 256 : (len - (size_t)idx), "-enc");
        if (cradle < 0) cradle = iequals_substr(data + idx, (len > (size_t)idx + 256) ? 256 : (len - (size_t)idx), "downloadstring");
        if (cradle < 0) cradle = iequals_substr(data + idx, (len > (size_t)idx + 256) ? 256 : (len - (size_t)idx), "downloadfile");
        if (cradle < 0) cradle = iequals_substr(data + idx, (len > (size_t)idx + 256) ? 256 : (len - (size_t)idx), "iex");
        if (cradle < 0) cradle = iequals_substr(data + idx, (len > (size_t)idx + 256) ? 256 : (len - (size_t)idx), "invoke-expression");
        if (cradle >= 0) {
            out->has_powershell_cradle = 1;
            save_snippet(out->match_snippets[2], data, len, (size_t)idx, 30);
        }
    }

    /* 4. Hardcoded IPv4 Address */
    for (size_t i = 0; i + 7 <= len; ++i) {
        if (isdigit(data[i])) {
            int dots = 0;
            size_t k = i;
            while (k < len && (isdigit(data[k]) || data[k] == '.')) {
                if (data[k] == '.') dots++;
                k++;
            }
            if (dots == 3 && (k - i) >= 7 && (k - i) <= 15) {
                out->has_hardcoded_ip = 1;
                save_snippet(out->match_snippets[3], data, len, i, k - i);
                break;
            }
        }
    }

    /* 5. Executable Drop Path */
    idx = iequals_substr(data, len, "\\Temp\\");
    if (idx < 0) idx = iequals_substr(data, len, "\\AppData\\");
    if (idx < 0) idx = iequals_substr(data, len, "\\ProgramData\\");
    if (idx < 0) idx = iequals_substr(data, len, "%TEMP%");
    if (idx < 0) idx = iequals_substr(data, len, "%APPDATA%");
    if (idx >= 0) {
        out->has_drop_path = 1;
        save_snippet(out->match_snippets[4], data, len, (size_t)idx, 15);
    }

    /* 6. Ransom Note String */
    idx = iequals_substr(data, len, "encrypted");
    if (idx < 0) idx = iequals_substr(data, len, "readme for decrypt");
    if (idx < 0) idx = iequals_substr(data, len, "send btc");
    if (idx < 0) idx = iequals_substr(data, len, "send bitcoin");
    if (idx < 0) idx = iequals_substr(data, len, "xmr");
    if (idx < 0) idx = iequals_substr(data, len, "monero");
    if (idx >= 0) {
        out->has_ransom_note = 1;
        save_snippet(out->match_snippets[5], data, len, (size_t)idx, 20);
    }

    return 0;
}
