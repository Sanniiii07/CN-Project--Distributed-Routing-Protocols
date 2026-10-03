#ifndef NETWORK_H
#define NETWORK_H

#include "router.h"
#include "messages.h"

int network_start(Router *router);
void network_stop(Router *router);

int network_send(Router *router,
                 const char *neighbor_id,
                 const Message *message);

int network_send_raw(Router *router,
                     const char *ip,
                     int port,
                     const char *data);

int network_receive(Router *router,
                     Message *message,
                     char *sender_ip,
                     size_t sender_ip_size,
                     int timeout_ms);

#endif
