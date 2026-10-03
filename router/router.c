#include "router.h"
#include "network.h"
#include "messages.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif

typedef struct {
    char a[MAX_ID_LEN];
    char b[MAX_ID_LEN];
    int cost;
} Link;

static Link g_links[MAX_ROUTERS * MAX_ROUTERS];
static int g_link_count = 0;

static void trim_newline(char *s)
{
    size_t len;

    if (!s) {
        return;
    }

    len = strlen(s);

    while (len > 0 &&
           (s[len - 1] == '\n' ||
            s[len - 1] == '\r')) {
        s[len - 1] = '\0';
        len--;
    }
}

static int add_router_info(Topology *topology,
                           const char *id,
                           const char *ip,
                           int port)
{
    RouterInfo *r;

    if (topology->router_count >= MAX_ROUTERS) {
        return -1;
    }

    if (topology_find_router(topology, id)) {
        fprintf(stderr,
                "Duplicate router ID: %s\n",
                id);
        return -1;
    }

    r = &topology->routers[topology->router_count++];

    snprintf(r->id, sizeof(r->id), "%s", id);
    snprintf(r->ip, sizeof(r->ip), "%s", ip);
    r->port = port;

    return 0;
}

int topology_load(const char *filename,
                  Topology *topology)
{
    FILE *fp;
    char line[256];

    if (!filename || !topology) {
        return -1;
    }

    memset(topology, 0, sizeof(*topology));
    g_link_count = 0;

    fp = fopen(filename, "r");

    if (!fp) {
        fprintf(stderr,
                "Cannot open topology file: %s\n",
                filename);
        return -1;
    }

    while (fgets(line, sizeof(line), fp)) {
        char type[16];
        char a[MAX_ID_LEN];
        char b[MAX_ID_LEN];
        char ip[MAX_IP_LEN];
        int port;
        int cost;

        trim_newline(line);

        if (line[0] == '\0' ||
            line[0] == '#') {
            continue;
        }

        if (sscanf(line, "%15s", type) != 1) {
            continue;
        }

        if (strcmp(type, "ROUTER") == 0) {
            if (sscanf(line,
                       "%*s %31s %63s %d",
                       a, ip, &port) != 3) {
                fprintf(stderr,
                        "Invalid ROUTER line: %s\n",
                        line);
                fclose(fp);
                return -1;
            }

            if (add_router_info(topology,
                                a, ip, port) != 0) {
                fclose(fp);
                return -1;
            }
        } else if (strcmp(type, "LINK") == 0) {
            if (sscanf(line,
                       "%*s %31s %31s %d",
                       a, b, &cost) != 3) {
                fprintf(stderr,
                        "Invalid LINK line: %s\n",
                        line);
                fclose(fp);
                return -1;
            }

            if (cost < 0 ||
                g_link_count >=
                    MAX_ROUTERS * MAX_ROUTERS) {
                fprintf(stderr,
                        "Invalid link or too many links.\n");
                fclose(fp);
                return -1;
            }

            snprintf(g_links[g_link_count].a,
                     sizeof(g_links[g_link_count].a),
                     "%s", a);

            snprintf(g_links[g_link_count].b,
                     sizeof(g_links[g_link_count].b),
                     "%s", b);

            g_links[g_link_count].cost = cost;
            g_link_count++;
        }
    }

    fclose(fp);

    if (topology->router_count == 0) {
        fprintf(stderr,
                "Topology contains no routers.\n");
        return -1;
    }

    return 0;
}

const RouterInfo *topology_find_router(
    const Topology *topology,
    const char *id)
{
    int i;

    if (!topology || !id) {
        return NULL;
    }

    for (i = 0;
         i < topology->router_count;
         i++) {
        if (strcmp(topology->routers[i].id,
                   id) == 0) {
            return &topology->routers[i];
        }
    }

    return NULL;
}

int topology_get_link_cost(const Topology *topology,
                           const char *a,
                           const char *b)
{
    int i;

    (void)topology;

    for (i = 0; i < g_link_count; i++) {
        if ((strcmp(g_links[i].a, a) == 0 &&
             strcmp(g_links[i].b, b) == 0) ||
            (strcmp(g_links[i].a, b) == 0 &&
             strcmp(g_links[i].b, a) == 0)) {
            return g_links[i].cost;
        }
    }

    return -1;
}

int router_init(Router *router,
                Topology *topology,
                const char *router_id)
{
    const RouterInfo *info;
    int i;

    if (!router ||
        !topology ||
        !router_id) {
        return -1;
    }

    memset(router, 0, sizeof(*router));

    info = topology_find_router(topology,
                                router_id);

    if (!info) {
        fprintf(stderr,
                "Router %s not found in topology.\n",
                router_id);
        return -1;
    }

    snprintf(router->id,
             sizeof(router->id),
             "%s",
             info->id);

    snprintf(router->ip,
             sizeof(router->ip),
             "%s",
             info->ip);

    router->port = info->port;
    router->running = 1;
    router->sequence = 1;
    router->topology = topology;
    router->sockfd = ROUTER_INVALID_SOCKET;

    snprintf(router->log_file,
             sizeof(router->log_file),
             "logs/%s.log",
             router_id);

    topology->neighbor_count = 0;

    for (i = 0; i < g_link_count; i++) {
        const char *peer = NULL;

        if (strcmp(g_links[i].a,
                   router_id) == 0) {
            peer = g_links[i].b;
        } else if (strcmp(g_links[i].b,
                          router_id) == 0) {
            peer = g_links[i].a;
        }

        if (peer) {
            Neighbor *n;

            if (topology->neighbor_count >=
                MAX_NEIGHBORS) {
                return -1;
            }

            n = &topology->neighbors[
                topology->neighbor_count++];

            {
                size_t peer_len = strlen(peer);
                if (peer_len >= sizeof(n->id)) {
                    peer_len = sizeof(n->id) - 1;
                }
                memcpy(n->id, peer, peer_len);
                n->id[peer_len] = '\0';
            }

            n->cost = g_links[i].cost;
            n->up = 1;
        }
    }

    return 0;
}

int router_find_neighbor(const Router *router,
                         const char *neighbor_id)
{
    int i;

    if (!router ||
        !neighbor_id ||
        !router->topology) {
        return -1;
    }

    for (i = 0;
         i < router->topology->neighbor_count;
         i++) {
        if (strcmp(router->topology
                       ->neighbors[i].id,
                   neighbor_id) == 0) {
            return i;
        }
    }

    return -1;
}

int router_set_neighbor_state(Router *router,
                              const char *neighbor_id,
                              int up)
{
    int index;

    index = router_find_neighbor(router,
                                 neighbor_id);

    if (index < 0) {
        return -1;
    }

    router->topology->neighbors[index].up =
        up ? 1 : 0;

    return 0;
}

int router_set_neighbor_cost(Router *router,
                             const char *neighbor_id,
                             int cost)
{
    int index;

    if (cost < 0) {
        return -1;
    }

    index = router_find_neighbor(router,
                                 neighbor_id);

    if (index < 0) {
        return -1;
    }

    router->topology->neighbors[index].cost =
        cost;

    return 0;
}

void router_print_topology(const Router *router)
{
    int i;

    if (!router || !router->topology) {
        return;
    }

    printf("\nAll routers:\n");

    for (i = 0;
         i < router->topology->router_count;
         i++) {
        const RouterInfo *r =
            &router->topology->routers[i];

        printf("  %-5s  %s:%d\n",
               r->id,
               r->ip,
               r->port);
    }

    printf("\nLinks:\n");

    for (i = 0; i < g_link_count; i++) {
        printf("  %s --(%d)-- %s\n",
               g_links[i].a,
               g_links[i].cost,
               g_links[i].b);
    }

    printf("\n");
}

void router_print_neighbors(const Router *router)
{
    int i;

    if (!router || !router->topology) {
        return;
    }

    printf("\nRouter %s neighbors:\n",
           router->id);

    for (i = 0;
         i < router->topology->neighbor_count;
         i++) {
        const Neighbor *n =
            &router->topology->neighbors[i];

        printf("  %-5s cost=%-3d state=%s\n",
               n->id,
               n->cost,
               n->up ? "UP" : "DOWN");
    }

    printf("\n");
}

static void send_hello(Router *router,
                       const char *neighbor)
{
    Message msg;

    message_init(&msg,
                 "HELLO",
                 router->id,
                 neighbor,
                 router->sequence++,
                 16,
                 "router-online");

    if (network_send(router,
                     neighbor,
                     &msg) == 0) {
        printf("[SEND] HELLO -> %s\n",
               neighbor);
    }
}

static void send_custom(Router *router,
                        const char *neighbor,
                        const char *type,
                        const char *payload)
{
    Message msg;

    message_init(&msg,
                 type,
                 router->id,
                 neighbor,
                 router->sequence++,
                 16,
                 payload ? payload : "");

    if (network_send(router,
                     neighbor,
                     &msg) == 0) {
        printf("[SEND] %s -> %s\n",
               type,
               neighbor);
    }
}

static void process_message(Router *router,
                            const Message *msg)
{
    if (!router || !msg) {
        return;
    }

    printf("\n[RECEIVED]\n");
    message_print(msg);

    if (strcmp(msg->type,
               "LINK_FAILURE") == 0) {
        if (router_set_neighbor_state(
                router,
                msg->sender,
                0) == 0) {
            printf("Link to %s marked DOWN locally.\n",
                   msg->sender);
        }
    } else if (strcmp(msg->type,
                      "LINK_RECOVERY") == 0) {
        if (router_set_neighbor_state(
                router,
                msg->sender,
                1) == 0) {
            printf("Link to %s marked UP locally.\n",
                   msg->sender);
        }
    } else if (strcmp(msg->type,
                      "COST_CHANGE") == 0) {
        int new_cost;

        if (sscanf(msg->payload,
                   "%d",
                   &new_cost) == 1) {
            if (router_set_neighbor_cost(
                    router,
                    msg->sender,
                    new_cost) == 0) {
                printf("Cost to %s changed to %d.\n",
                       msg->sender,
                       new_cost);
            }
        }
    }
}

static void print_help(void)
{
    printf("\nCommands:\n");
    printf("  help                         Show commands\n");
    printf("  show                         Show local neighbors\n");
    printf("  topology                    Show topology\n");
    printf("  hello <neighbor>            Send HELLO\n");
    printf("  send <neighbor> <type> <payload>\n");
    printf("  fail <neighbor>             Mark local link DOWN\n");
    printf("  recover <neighbor>          Mark local link UP\n");
    printf("  cost <neighbor> <new_cost>  Change local cost\n");
    printf("  crash                       Stop router\n");
    printf("  quit                        Exit router\n");
    printf("\nTypes:\n");
    printf("  HELLO DV_UPDATE LSA PATH_VECTOR\n");
    printf("  LINK_FAILURE LINK_RECOVERY COST_CHANGE\n");
    printf("  NODE_CRASH NODE_RECOVERY\n\n");
}

#ifdef _WIN32
static DWORD WINAPI receiver_thread(
    LPVOID arg)
{
    Router *router = (Router *)arg;

    while (router->running) {
        Message msg;
        char sender_ip[64];

        int result = network_receive(
            router,
            &msg,
            sender_ip,
            sizeof(sender_ip),
            500);

        if (result > 0) {
            process_message(router, &msg);
        }
    }

    return 0;
}
#else
static void *receiver_thread(void *arg)
{
    Router *router = (Router *)arg;

    while (router->running) {
        Message msg;
        char sender_ip[64];

        int result = network_receive(
            router,
            &msg,
            sender_ip,
            sizeof(sender_ip),
            500);

        if (result > 0) {
            process_message(router, &msg);
        }
    }

    return NULL;
}
#endif

static void command_loop(Router *router)
{
    char line[1024];

    print_help();

    while (router->running) {
        char command[32];

        printf("%s> ", router->id);
        fflush(stdout);

        if (!fgets(line,
                   sizeof(line),
                   stdin)) {
            break;
        }

        trim_newline(line);

        if (sscanf(line,
                   "%31s",
                   command) != 1) {
            continue;
        }

        if (strcmp(command, "help") == 0) {
            print_help();

        } else if (strcmp(command, "show") == 0) {
            router_print_neighbors(router);

        } else if (strcmp(command, "topology") == 0) {
            router_print_topology(router);

        } else if (strcmp(command, "hello") == 0) {
            char neighbor[MAX_ID_LEN];

            if (sscanf(line,
                       "%*s %31s",
                       neighbor) == 1) {
                send_hello(router, neighbor);
            } else {
                printf("Usage: hello <neighbor>\n");
            }

        } else if (strcmp(command, "send") == 0) {
            char neighbor[MAX_ID_LEN];
            char type[MSG_TYPE_LEN];
            char payload[700];

            memset(payload, 0, sizeof(payload));

            if (sscanf(line,
                       "%*s %31s %31s %699[^\n]",
                       neighbor,
                       type,
                       payload) >= 2) {
                send_custom(router,
                            neighbor,
                            type,
                            payload);
            } else {
                printf("Usage: send <neighbor> <type> <payload>\n");
            }

        } else if (strcmp(command, "fail") == 0) {
            char neighbor[MAX_ID_LEN];

            if (sscanf(line,
                       "%*s %31s",
                       neighbor) == 1) {
                if (router_set_neighbor_state(
                        router,
                        neighbor,
                        0) == 0) {
                    printf("Local link to %s is DOWN.\n",
                           neighbor);
                } else {
                    printf("Unknown neighbor: %s\n",
                           neighbor);
                }
            }

        } else if (strcmp(command, "recover") == 0) {
            char neighbor[MAX_ID_LEN];

            if (sscanf(line,
                       "%*s %31s",
                       neighbor) == 1) {
                if (router_set_neighbor_state(
                        router,
                        neighbor,
                        1) == 0) {
                    printf("Local link to %s is UP.\n",
                           neighbor);
                } else {
                    printf("Unknown neighbor: %s\n",
                           neighbor);
                }
            }

        } else if (strcmp(command, "cost") == 0) {
            char neighbor[MAX_ID_LEN];
            int cost;

            if (sscanf(line,
                       "%*s %31s %d",
                       neighbor,
                       &cost) == 2) {
                if (router_set_neighbor_cost(
                        router,
                        neighbor,
                        cost) == 0) {
                    printf("Cost to %s changed to %d locally.\n",
                           neighbor,
                           cost);
                } else {
                    printf("Invalid neighbor or cost.\n");
                }
            } else {
                printf("Usage: cost <neighbor> <new_cost>\n");
            }

        } else if (strcmp(command, "crash") == 0) {
            router->running = 0;
            printf("Router %s stopped.\n",
                   router->id);

        } else if (strcmp(command, "quit") == 0) {
            router->running = 0;

        } else {
            printf("Unknown command. Type 'help'.\n");
        }
    }
}

int main(int argc, char *argv[])
{
    Topology topology;
    Router router;

    if (argc != 3) {
        fprintf(stderr,
                "Usage: %s <router_id> <topology_file>\n",
                argv[0]);

        fprintf(stderr,
                "Example: %s R1 config/topology.conf\n",
                argv[0]);

        return EXIT_FAILURE;
    }

    if (topology_load(argv[2],
                      &topology) != 0) {
        return EXIT_FAILURE;
    }

    if (router_init(&router,
                    &topology,
                    argv[1]) != 0) {
        return EXIT_FAILURE;
    }

#ifdef _WIN32
    CreateDirectoryA("logs", NULL);
#else
    (void)system("mkdir -p logs");
#endif

    if (network_start(&router) != 0) {
        return EXIT_FAILURE;
    }

    printf("\n========================================\n");
    printf(" Distributed Router Infrastructure\n");
    printf(" Router : %s\n", router.id);
    printf(" UDP    : %s:%d\n",
           router.ip,
           router.port);
    printf("========================================\n");

    router_print_neighbors(&router);

#ifdef _WIN32
    {
        HANDLE thread = CreateThread(
            NULL,
            0,
            receiver_thread,
            &router,
            0,
            NULL);

        if (!thread) {
            fprintf(stderr,
                    "Could not create receiver thread.\n");
            network_stop(&router);
            return EXIT_FAILURE;
        }

        command_loop(&router);
        router.running = 0;

        WaitForSingleObject(thread, 2000);
        CloseHandle(thread);
    }
#else
    {
        pthread_t thread;

        if (pthread_create(&thread,
                           NULL,
                           receiver_thread,
                           &router) != 0) {
            fprintf(stderr,
                    "Could not create receiver thread.\n");
            network_stop(&router);
            return EXIT_FAILURE;
        }

        command_loop(&router);
        router.running = 0;
        pthread_join(thread, NULL);
    }
#endif

    network_stop(&router);

    printf("Router %s exited.\n",
           router.id);

    return EXIT_SUCCESS;
}
