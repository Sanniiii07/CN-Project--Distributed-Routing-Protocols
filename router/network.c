#include "network.h"

#include <stdio.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
typedef int router_socklen_t;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>
typedef socklen_t router_socklen_t;
#endif

static void network_log(Router *router,
                        const char *direction,
                        const char *peer,
                        const char *data)
{
    FILE *fp;
    time_t now;
    struct tm *tm_info;
    char timestamp[32];

    if (!router) {
        return;
    }

    fp = fopen(router->log_file, "a");
    if (!fp) {
        return;
    }

    now = time(NULL);
    tm_info = localtime(&now);

    if (tm_info) {
        strftime(timestamp, sizeof(timestamp),
                 "%Y-%m-%d %H:%M:%S", tm_info);
    } else {
        snprintf(timestamp, sizeof(timestamp), "unknown-time");
    }

    fprintf(fp, "[%s] %s %s %s\n",
            timestamp,
            direction ? direction : "-",
            peer ? peer : "-",
            data ? data : "");

    fclose(fp);
}

static void close_socket(router_socket_t sock)
{
#ifdef _WIN32
    closesocket(sock);
#else
    close(sock);
#endif
}

int network_start(Router *router)
{
    struct sockaddr_in addr;
    int reuse = 1;

    if (!router) {
        return -1;
    }

#ifdef _WIN32
    {
        WSADATA wsa;

        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
            fprintf(stderr, "WSAStartup failed.\n");
            return -1;
        }
    }
#endif

    router->sockfd = socket(AF_INET, SOCK_DGRAM, 0);

    if (router->sockfd == ROUTER_INVALID_SOCKET) {
        fprintf(stderr, "socket() failed.\n");
#ifdef _WIN32
        WSACleanup();
#endif
        return -1;
    }

    if (setsockopt(router->sockfd,
                   SOL_SOCKET,
                   SO_REUSEADDR,
                   (const char *)&reuse,
                   sizeof(reuse)) < 0) {
        fprintf(stderr, "setsockopt() failed.\n");
        close_socket(router->sockfd);
#ifdef _WIN32
        WSACleanup();
#endif
        router->sockfd = ROUTER_INVALID_SOCKET;
        return -1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)router->port);

    {
        unsigned long ip_value = inet_addr(router->ip);

        if (ip_value == INADDR_NONE && strcmp(router->ip, "255.255.255.255") != 0) {
            fprintf(stderr, "Invalid IP address: %s\n", router->ip);
        close_socket(router->sockfd);
#ifdef _WIN32
        WSACleanup();
#endif
            router->sockfd = ROUTER_INVALID_SOCKET;
            return -1;
        }

        addr.sin_addr.s_addr = ip_value;
    }

    if (bind(router->sockfd,
             (struct sockaddr *)&addr,
             sizeof(addr)) < 0) {
        fprintf(stderr, "bind() failed for %s:%d.\n",
                router->ip, router->port);
        close_socket(router->sockfd);
#ifdef _WIN32
        WSACleanup();
#endif
        router->sockfd = ROUTER_INVALID_SOCKET;
        return -1;
    }

    return 0;
}

void network_stop(Router *router)
{
    if (!router) {
        return;
    }

    if (router->sockfd != ROUTER_INVALID_SOCKET) {
        close_socket(router->sockfd);
        router->sockfd = ROUTER_INVALID_SOCKET;
    }

#ifdef _WIN32
    WSACleanup();
#endif
}

int network_send_raw(Router *router,
                     const char *ip,
                     int port,
                     const char *data)
{
    struct sockaddr_in destination;
    int sent;

    if (!router ||
        router->sockfd == ROUTER_INVALID_SOCKET ||
        !ip ||
        !data) {
        return -1;
    }

    memset(&destination, 0, sizeof(destination));
    destination.sin_family = AF_INET;
    destination.sin_port = htons((unsigned short)port);

    {
        unsigned long ip_value = inet_addr(ip);

        if (ip_value == INADDR_NONE && strcmp(ip, "255.255.255.255") != 0) {
            return -1;
        }

        destination.sin_addr.s_addr = ip_value;
    }

    sent = sendto(router->sockfd,
                  data,
                  (int)strlen(data),
                  0,
                  (struct sockaddr *)&destination,
                  sizeof(destination));

    if (sent < 0) {
        fprintf(stderr, "sendto() failed.\n");
        return -1;
    }

    return sent;
}

int network_send(Router *router,
                 const char *neighbor_id,
                 const Message *message)
{
    const RouterInfo *peer;
    char buffer[MAX_MESSAGE_SIZE];
    int encoded;
    int index;

    if (!router || !neighbor_id || !message) {
        return -1;
    }

    index = router_find_neighbor(router, neighbor_id);

    if (index < 0) {
        fprintf(stderr,
                "ERROR: %s is not a neighbor of %s.\n",
                neighbor_id, router->id);
        return -1;
    }

    if (!router->topology->neighbors[index].up) {
        fprintf(stderr,
                "ERROR: link to %s is DOWN.\n",
                neighbor_id);
        return -1;
    }

    peer = topology_find_router(router->topology, neighbor_id);

    if (!peer) {
        return -1;
    }

    encoded = message_encode(message,
                              buffer,
                              sizeof(buffer));

    if (encoded < 0) {
        fprintf(stderr,
                "ERROR: message encoding failed.\n");
        return -1;
    }

    if (network_send_raw(router,
                          peer->ip,
                          peer->port,
                          buffer) < 0) {
        return -1;
    }

    network_log(router, "SEND", neighbor_id, buffer);

    return 0;
}

int network_receive(Router *router,
                    Message *message,
                    char *sender_ip,
                    size_t sender_ip_size,
                    int timeout_ms)
{
    fd_set readfds;
    struct timeval timeout;
    struct sockaddr_in sender;
    router_socklen_t sender_len;
    char buffer[MAX_MESSAGE_SIZE];
    char *ip_string;
    int ready;
    int received;

    if (!router ||
        router->sockfd == ROUTER_INVALID_SOCKET ||
        !message) {
        return -1;
    }

    FD_ZERO(&readfds);
    FD_SET(router->sockfd, &readfds);

    timeout.tv_sec = timeout_ms / 1000;
    timeout.tv_usec = (timeout_ms % 1000) * 1000;

    ready = select(0,
                   &readfds,
                   NULL,
                   NULL,
                   &timeout);

    if (ready == 0) {
        return 0;
    }

    if (ready < 0) {
        fprintf(stderr, "select() failed.\n");
        return -1;
    }

    sender_len = (router_socklen_t)sizeof(sender);

    received = recvfrom(router->sockfd,
                        buffer,
                        sizeof(buffer) - 1,
                        0,
                        (struct sockaddr *)&sender,
                        &sender_len);

    if (received < 0) {
        fprintf(stderr, "recvfrom() failed.\n");
        return -1;
    }

    buffer[received] = '\0';

    ip_string = inet_ntoa(sender.sin_addr);

    if (!ip_string) {
        ip_string = "unknown";
    }

    if (sender_ip && sender_ip_size > 0) {
        snprintf(sender_ip,
                 sender_ip_size,
                 "%s",
                 ip_string);
    }

    if (message_decode(buffer, message) != 0) {
        fprintf(stderr,
                "Received invalid message: %s\n",
                buffer);
        return -1;
    }

    network_log(router,
                "RECV",
                message->sender,
                buffer);

    return received;
}
