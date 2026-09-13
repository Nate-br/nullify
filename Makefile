CC ?= gcc
CFLAGS ?= -O3 -Wall -Wextra -pedantic -std=c11 -fPIC -Isrc/c/include
LDFLAGS ?= -shared
LDLIBS ?= -lm

SRC_DIR = src/c
INCLUDE_DIR = src/c/include
LIB_DIR = lib
BIN_DIR = bin

LIB_SRCS = $(SRC_DIR)/entropy.c $(SRC_DIR)/ember_fast.c $(SRC_DIR)/hash.c $(SRC_DIR)/pe_elf.c
LIB_OBJS = $(LIB_SRCS:.c=.o)
TARGET_LIB = $(LIB_DIR)/libnullify.so

CLI_SRCS = $(SRC_DIR)/main_core.c
CLI_OBJS = $(CLI_SRCS:.c=.o)
TARGET_CLI = $(BIN_DIR)/nullify-core

.PHONY: all clean test-c

all: $(TARGET_LIB) $(TARGET_CLI)

$(LIB_DIR):
	mkdir -p $(LIB_DIR)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET_LIB): $(LIB_OBJS) | $(LIB_DIR)
	$(CC) $(LDFLAGS) -o $@ $(LIB_OBJS) $(LDLIBS)

$(TARGET_CLI): $(CLI_OBJS) $(LIB_OBJS) | $(BIN_DIR)
	$(CC) -O3 -Wall -Wextra -I$(INCLUDE_DIR) -o $@ $(CLI_OBJS) $(LIB_OBJS) $(LDLIBS)

test-c: $(TARGET_CLI)
	./$(TARGET_CLI) /bin/bash
	./$(TARGET_CLI) /bin/bash --json

clean:
	rm -f $(SRC_DIR)/*.o
	rm -f $(TARGET_LIB) $(TARGET_CLI)
