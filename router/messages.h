#ifndef MESSAGES_H
#define MESSAGES_H

#include <stddef.h>

#define MSG_TYPE_LEN 32
#define MSG_PAYLOAD_LEN 3072
#define MAX_MESSAGE_SIZE 4096

typedef struct {
    char type[MSG_TYPE_LEN];
    char sender[32];
    char target[32];
    unsigned long sequence;
    int ttl;
    char payload[MSG_PAYLOAD_LEN];
} Message;

void message_init(Message *msg,
                  const char *type,
                  const char *sender,
                  const char *target,
                  unsigned long sequence,
                  int ttl,
                  const char *payload);

int message_encode(const Message *msg, char *buffer, size_t buffer_size);
int message_decode(const char *buffer, Message *msg);
void message_print(const Message *msg);

#endif
