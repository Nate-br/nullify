#ifndef NULLIFY_HASH_H
#define NULLIFY_HASH_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void nullify_md5(const uint8_t *data, size_t len, char out_hex[33]);
void nullify_sha1(const uint8_t *data, size_t len, char out_hex[41]);
void nullify_sha256(const uint8_t *data, size_t len, char out_hex[65]);

#ifdef __cplusplus
}
#endif

#endif /* NULLIFY_HASH_H */
