#ifndef ROUTER_H
#define ROUTER_H

#include <stddef.h>

#ifdef _WIN32
#include <winsock2.h>
typedef SOCKET router_socket_t;
#define ROUTER_INVALID_SOCKET INVALID_SOCKET
#else
typedef int router_socket_t;
#define ROUTER_INVALID_SOCKET (-1)
#endif

#define MAX_ROUTERS 64
#define MAX_ID_LEN 32
#define MAX_IP_LEN 64
#define MAX_NEIGHBORS 64
#define MAX_MESSAGE_SIZE 4096
#define LOG_FILE_SIZE 128

typedef struct {
    char id[MAX_ID_LEN];
    char ip[MAX_IP_LEN];
    int port;
} RouterInfo;

typedef struct {
    char id[MAX_ID_LEN];
    int cost;
    int up;
} Neighbor;

typedef struct {
    RouterInfo routers[MAX_ROUTERS];
    int router_count;
    Neighbor neighbors[MAX_NEIGHBORS];
    int neighbor_count;
} Topology;

typedef struct {
    char id[MAX_ID_LEN];
    char ip[MAX_IP_LEN];
    int port;
    int running;
    unsigned long sequence;
    Topology *topology;
    router_socket_t sockfd;
    char log_file[LOG_FILE_SIZE];
} Router;

int topology_load(const char *filename, Topology *topology);
const RouterInfo *topology_find_router(const Topology *topology, const char *id);
int topology_get_link_cost(const Topology *topology, const char *a, const char *b);

int router_init(Router *router, Topology *topology, const char *router_id);
int router_find_neighbor(const Router *router, const char *neighbor_id);
void router_print_topology(const Router *router);
void router_print_neighbors(const Router *router);
int router_set_neighbor_state(Router *router, const char *neighbor_id, int up);
int router_set_neighbor_cost(Router *router, const char *neighbor_id, int cost);

#endif
