#define _POSIX_C_SOURCE 200809L
#include "nullify.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void print_banner(void) {
    printf("\033[1;36m");
    printf("███╗   ██╗██╗   ██╗██╗     ██╗     ██╗███████╗██╗   ██╗\n");
    printf("████╗  ██║██║   ██║██║     ██║     ██║██╔════╝╚██╗ ██╔╝\n");
    printf("██╔██╗ ██║██║   ██║██║     ██║     ██║█████╗   ╚████╔╝ \n");
    printf("██║╚██╗██║██║   ██║██║     ██║     ██║██╔══╝    ╚██╔╝  \n");
    printf("██║ ╚████║╚██████╔╝███████╗███████╗██║██║        ██║   \n");
    printf("╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝╚═╝╚═╝        ╚═╝   \n");
    printf("\033[0m");
    printf("\033[2m  NULLIFY C-CORE ACCELERATOR // ULTRA-LOW LATENCY TRIAGE\033[0m\n\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_banner();
        fprintf(stderr, "Usage: %s <target_file> [--json]\n", argv[0]);
        return 1;
    }

    const char *target_path = argv[1];
    int json_output = 0;
    if (argc >= 3 && strcmp(argv[2], "--json") == 0) {
        json_output = 1;
    } else if (argc >= 2 && strcmp(argv[1], "--json") == 0 && argc >= 3) {
        json_output = 1;
        target_path = argv[2];
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    nullify_triage_result_t triage;
    int rc = nullify_triage_file(target_path, &triage);

    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed_ms = (double)(end.tv_sec - start.tv_sec) * 1000.0 +
                        (double)(end.tv_nsec - start.tv_nsec) / 1000000.0;

    if (rc != 0) {
        if (json_output) {
            printf("{\"error\": \"Failed to read or parse file\", \"code\": %d, \"path\": \"%s\"}\n", rc, target_path);
        } else {
            fprintf(stderr, "\033[1;31m[-] Error:\033[0m Could not triage file '%s' (error code: %d)\n", target_path, rc);
        }
        return 2;
    }

    const char *magic_str = "UNKNOWN";
    if (triage.magic == NULLIFY_MAGIC_PE) magic_str = "PE (Portable Executable)";
    else if (triage.magic == NULLIFY_MAGIC_ELF) magic_str = "ELF (Executable and Linkable Format)";
    else if (triage.magic == NULLIFY_MAGIC_SCRIPT) magic_str = "Script";

    if (json_output) {
        printf("{\n");
        printf("  \"path\": \"%s\",\n", target_path);
        printf("  \"size_bytes\": %llu,\n", (unsigned long long)triage.size_bytes);
        printf("  \"magic\": \"%s\",\n", magic_str);
        printf("  \"architecture\": \"%s\",\n", triage.architecture);
        printf("  \"entropy\": %.6f,\n", triage.entropy);
        printf("  \"is_executable\": %s,\n", triage.is_executable ? "true" : "false");
        printf("  \"is_packed\": %s,\n", triage.is_packed ? "true" : "false");
        printf("  \"num_sections\": %d,\n", triage.num_sections);
        printf("  \"entry_section\": \"%s\",\n", triage.entry_section);
        printf("  \"md5\": \"%s\",\n", triage.md5);
        printf("  \"sha256\": \"%s\",\n", triage.sha256);
        printf("  \"triage_latency_ms\": %.3f\n", elapsed_ms);
        printf("}\n");
    } else {
        print_banner();
        printf("\033[1;34m[>] Target:\033[0m       %s\n", target_path);
        printf("\033[1;34m[+] Size:\033[0m         %llu bytes\n", (unsigned long long)triage.size_bytes);
        printf("\033[1;34m[+] Magic:\033[0m        %s\n", magic_str);
        printf("\033[1;34m[+] Architecture:\033[0m %s\n", triage.architecture);
        printf("\033[1;34m[+] Sections:\033[0m     %d (Entry: '%s')\n", triage.num_sections, triage.entry_section);
        printf("\033[1;34m[+] MD5:\033[0m          %s\n", triage.md5);
        printf("\033[1;34m[+] SHA-256:\033[0m      %s\n", triage.sha256);

        if (triage.entropy >= 7.2) {
            printf("\033[1;33m[!] Entropy:\033[0m      %.4f / 8.0 \033[1;31m[HIGH / PACKED]\033[0m\n", triage.entropy);
        } else {
            printf("\033[1;32m[+] Entropy:\033[0m      %.4f / 8.0 [NORMAL]\n", triage.entropy);
        }

        if (triage.is_packed) {
            printf("\033[1;31m[!] Packing:\033[0m      PACKED / OBFUSCATED\n");
        } else {
            printf("\033[1;32m[+] Packing:\033[0m      NOT PACKED\n");
        }

        printf("\n\033[2mProcessed in %.3f ms natively with C\033[0m\n", elapsed_ms);
    }

    return 0;
}
