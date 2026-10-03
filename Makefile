CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2
TARGET = router_app.exe
SRC = router/router.c router/network.c router/messages.c

all:
	$(CC) $(CFLAGS) $(SRC) -o $(TARGET) -lws2_32

clean:
	del /Q $(TARGET) 2>NUL

.PHONY: all clean
