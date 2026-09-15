#include "nullify.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static int iequals_substr(const uint8_t *data, size_t data_len, const char *sub) {
    size_t sub_len = strlen(sub);
    if (sub_len > data_len) return -1;

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
    if (idx >= 0) {
        size_t window = (len > (size_t)idx + 64) ? 64 : (len - (size_t)idx);
        if (iequals_substr(data + idx, window, "/create") >= 0 ||
            iequals_substr(data + idx, window, "-create") >= 0) {
            out->has_scheduled_task = 1;
            save_snippet(out->match_snippets[1], data, len, (size_t)idx, 16);
        }
    }
    if (!out->has_scheduled_task) {
        idx = iequals_substr(data, len, "ITaskService");
        if (idx >= 0) {
            out->has_scheduled_task = 1;
            save_snippet(out->match_snippets[1], data, len, (size_t)idx, 12);
        }
    }

    /* 3. PowerShell Download Cradle */
    idx = iequals_substr(data, len, "powershell");
    if (idx < 0) idx = iequals_substr(data, len, "pwsh");
    if (idx >= 0) {
        size_t win = (len > (size_t)idx + 128) ? 128 : (len - (size_t)idx);
        int cradle = iequals_substr(data + idx, win, "-enc");
        if (cradle < 0) cradle = iequals_substr(data + idx, win, "downloadstring");
        if (cradle < 0) cradle = iequals_substr(data + idx, win, "downloadfile");
        if (cradle < 0) cradle = iequals_substr(data + idx, win, "invoke-expression");
        if (cradle < 0) {
            int p = iequals_substr(data + idx, win, "iex");
            if (p >= 0) {
                size_t abs_p = (size_t)idx + (size_t)p;
                int before_ok = (abs_p == 0 || !isalnum(data[abs_p - 1]));
                int after_ok = (abs_p + 3 >= len || !isalnum(data[abs_p + 3]));
                if (before_ok && after_ok) {
                    cradle = p;
                }
            }
        }
        if (cradle >= 0) {
            out->has_powershell_cradle = 1;
            save_snippet(out->match_snippets[2], data, len, (size_t)idx, 30);
        }
    }

    /* 4. Hardcoded IPv4 Address */
    for (size_t i = 0; i + 7 <= len; ++i) {
        if (isdigit(data[i])) {
            if (i > 0 && (isalnum(data[i - 1]) || data[i - 1] == '.' || data[i - 1] == '_')) {
                continue;
            }

            int octets[4] = {0};
            int octet_idx = 0;
            size_t k = i;
            int valid = 1;

            while (k < len && octet_idx < 4) {
                if (!isdigit(data[k])) {
                    valid = 0;
                    break;
                }
                size_t num_digits = 0;
                int val = 0;
                while (k < len && isdigit(data[k]) && num_digits < 3) {
                    val = val * 10 + (data[k] - '0');
                    num_digits++;
                    k++;
                }
                if (num_digits == 0 || val > 255) {
                    valid = 0;
                    break;
                }
                if (num_digits > 1 && data[k - num_digits] == '0') {
                    valid = 0;
                    break;
                }
                octets[octet_idx++] = val;

                if (octet_idx < 4) {
                    if (k < len && data[k] == '.') {
                        k++;
                    } else {
                        valid = 0;
                        break;
                    }
                }
            }

            if (valid && octet_idx == 4) {
                if (k < len && (isalnum(data[k]) || data[k] == '.' || data[k] == '_')) {
                    valid = 0;
                }
            } else {
                valid = 0;
            }

            if (valid && octets[0] >= 1 && octets[0] <= 255 && octets[0] != 127) {
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

    /* 6. Ransom Note String (multi-word, unambiguous phrases) */
    static const char * const ransom_patterns[] = {
        "your files are encrypted",
        "your files have been encrypted",
        "all your files have been encrypted",
        "all of your files are encrypted",
        "files have been encrypted",
        "files are encrypted",
        "readme for decrypt",
        "readme_for_decrypt",
        "readme-for-decrypt",
        "how to decrypt",
        "how to recover files",
        "how to restore files",
        "restore your files",
        "send btc",
        "send bitcoin",
        "send xmr",
        "send monero",
        "pay the ransom",
        "pay ransom",
        "bitcoin wallet",
        "monero wallet",
        NULL
    };

    for (int p = 0; ransom_patterns[p] != NULL; ++p) {
        idx = iequals_substr(data, len, ransom_patterns[p]);
        if (idx >= 0) {
            out->has_ransom_note = 1;
            save_snippet(out->match_snippets[5], data, len, (size_t)idx, strlen(ransom_patterns[p]));
            break;
        }
    }

    return 0;
}
