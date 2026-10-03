#include "messages.h"

#include <stdio.h>
#include <string.h>

void message_init(Message *msg,
                  const char *type,
                  const char *sender,
                  const char *target,
                  unsigned long sequence,
                  int ttl,
                  const char *payload)
{
    if (!msg) {
        return;
    }

    memset(msg, 0, sizeof(*msg));

    snprintf(msg->type, sizeof(msg->type), "%s", type ? type : "");
    snprintf(msg->sender, sizeof(msg->sender), "%s", sender ? sender : "");
    snprintf(msg->target, sizeof(msg->target), "%s", target ? target : "");
    msg->sequence = sequence;
    msg->ttl = ttl;

    if (payload) {
        snprintf(msg->payload, sizeof(msg->payload), "%s", payload);
    }
}

int message_encode(const Message *msg, char *buffer, size_t buffer_size)
{
    int written;

    if (!msg || !buffer || buffer_size == 0) {
        return -1;
    }

    /* Wire format:
       TYPE|SENDER|TARGET|SEQUENCE|TTL|PAYLOAD
       Payload must not contain '|'. */
    written = snprintf(buffer, buffer_size,
                       "%s|%s|%s|%lu|%d|%s",
                       msg->type,
                       msg->sender,
                       msg->target,
                       msg->sequence,
                       msg->ttl,
                       msg->payload);

    if (written < 0 || (size_t)written >= buffer_size) {
        return -1;
    }

    return written;
}

int message_decode(const char *buffer, Message *msg)
{
    char temp[MAX_MESSAGE_SIZE];
    char *parts[6];
    char *token;
    int count = 0;

    if (!buffer || !msg) {
        return -1;
    }

    memset(msg, 0, sizeof(*msg));
    snprintf(temp, sizeof(temp), "%s", buffer);

    token = strtok(temp, "|");
    while (token && count < 6) {
        parts[count++] = token;
        token = strtok(NULL, "|");
    }

    if (count != 6) {
        return -1;
    }

    snprintf(msg->type, sizeof(msg->type), "%s", parts[0]);
    snprintf(msg->sender, sizeof(msg->sender), "%s", parts[1]);
    snprintf(msg->target, sizeof(msg->target), "%s", parts[2]);

    if (sscanf(parts[3], "%lu", &msg->sequence) != 1) {
        return -1;
    }

    if (sscanf(parts[4], "%d", &msg->ttl) != 1) {
        return -1;
    }

    snprintf(msg->payload, sizeof(msg->payload), "%s", parts[5]);

    return 0;
}

void message_print(const Message *msg)
{
    if (!msg) {
        return;
    }

    printf("Message {\n");
    printf("  type     : %s\n", msg->type);
    printf("  sender   : %s\n", msg->sender);
    printf("  target   : %s\n", msg->target);
    printf("  sequence : %lu\n", msg->sequence);
    printf("  ttl      : %d\n", msg->ttl);
    printf("  payload  : %s\n", msg->payload);
    printf("}\n");
}
