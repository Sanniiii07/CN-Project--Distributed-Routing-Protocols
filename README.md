# P7: Distributed Routing Protocols

A distributed routing system simulating independent router processes communicating over UDP sockets. This project implements and compares **Distance Vector (Bellman-Ford)**, **Link State (Dijkstra / LSA flooding)**, and **Path Vector (BGP-style loop detection)** protocols, along with dynamic event injection (link failure, recovery, cost change, node crash) and routing loop mitigations.

---

## Team & Ownership

| Member | Main Ownership | Key Files & Modules |
| :--- | :--- | :--- |
| **Naitik** *(Member 1)* | Topology loader, router infrastructure, C transport, launcher | `config/topology.conf`, `config/topology_loader.py`, `router/router.c`, `router/network.c`, `router/messages.c`, `start_all_routers.bat`, `start_all_routers.py` |
| **Sanniva** *(Member 2)* | **Distance Vector (Bellman-Ford)**, Split Horizon, Poisoned Reverse, Count-to-Infinity | `algorithms/distance_vector.py`, `router/routing_table.py`, `router/dv_router.py`, `experiments/count_to_infinity.py`, `tests/test_distance_vector.py` |
| **Sagar** *(Member 3)* | **Link State**, LSA flooding, sequence numbers, Dijkstra | `algorithms/link_state.py`, `algorithms/dijkstra.py`, `router.py`, `test_dijkstra.py` |
| **Sreejita** *(Member 4)* | **Path Vector**, dynamic event engine, visualization, benchmarks | `algorithms/path_vector.py`, `router/pv_router.py`, `events/`, `visualization/`, `experiments/run_experiments.py` |

---

## Project Structure

```text
CN-Project--Distributed-Routing-Protocols/
├── algorithms/
│   ├── distance_vector.py      # Distance Vector routing engine (Bellman-Ford + loop prevention)
│   ├── path_vector.py          # Path Vector routing with AS-path loop detection
│   └── link_state.py           # Link State LSA database and flooding
├── router/
│   ├── routing_table.py        # Generic RoutingTable and RouteEntry data structures
│   ├── dv_router.py            # Standalone UDP process for Distance Vector routing
│   ├── pv_router.py            # Standalone UDP process for Path Vector routing
│   ├── router.c / network.c    # C Winsock UDP infrastructure
│   └── messages.c / messages.h # C message encoding/decoding
├── events/
│   ├── event_engine.py         # Dynamic network event injector (link drop, recovery, cost change)
│   └── scenarios.py            # Demonstrations: transient loops, black holes, link flapping
├── visualization/
│   └── convergence.py          # Convergence timeline tracking and loop detection
├── experiments/
│   ├── count_to_infinity.py    # Classic Count-to-Infinity simulation & mitigation demo
│   └── run_experiments.py      # Protocol benchmark suite (rounds & message volume)
├── tests/
│   ├── run_all_tests.py        # Master test runner (discovers and executes all tests)
│   ├── test_distance_vector.py # 12 unit tests for DV, Split Horizon, Poisoned Reverse
│   ├── test_path_vector.py     # Unit tests for Path Vector routing
│   ├── test_pv_router_udp.py   # 4-router UDP integration test
│   ├── test_event_engine.py    # Unit tests for event injection
│   ├── test_scenarios.py       # Unit tests for network anomaly scenarios
│   └── test_topology_loader.py # 8 unit tests for topology configuration loader
├── config/
│   ├── topology.conf           # C-style configuration
│   ├── topology.txt            # Python plain-text edge list
│   └── topology_loader.py      # Shared Python topology & port loader module
├── start_all_routers.py        # One-command process launcher (C/Python routers)
├── start_all_routers.bat       # Windows 1-click batch launcher for 4 router windows
└── start.bat                   # Quick launcher shortcut
```

---

## Quick Start & Execution Guide

### 0. Launch All 4 Routers in Separate Terminal Windows (One Command)
Start independent router instances (`R1`, `R2`, `R3`, `R4`) in their own dedicated console windows with one command:

**Option A: Windows Batch Launcher (Double-click or run):**
```powershell
.\start_all_routers.bat
# Or simply:
.\start.bat
```

**Option B: Python Cross-Platform Launcher:**
```powershell
# Launch C Winsock routers (router_app.exe)
python start_all_routers.py --mode c

# Launch Python Distance Vector routers
python start_all_routers.py --mode dv
```

---

### 1. Run the Count-to-Infinity Experiment (Distance Vector)
Simulates link failure on a 3-node linear network ($A \longleftrightarrow B \longleftrightarrow C$) and compares convergence across three modes:
- **No Prevention (`NONE`)**: Demonstrates metric bouncing step-by-step up to 16.
- **Split Horizon (`SPLIT_HORIZON`)**: Omits routes sent to the next hop, converging immediately.
- **Poisoned Reverse (`POISONED_REVERSE`)**: Advertises routes to the next hop with metric 16 (infinity), stopping loops instantly.

```powershell
python experiments/count_to_infinity.py
```

### 2. Run the Distance Vector Router over UDP
Launches independent router instances on localhost UDP sockets that exchange `DV_UPDATE` packets and dynamically recalculate shortest paths:

```powershell
python router/dv_router.py
```

### 3. Test the Routing Table Data Structure
```powershell
python router/routing_table.py
```

### 4. Run Comparative Protocol Benchmarks
Measures convergence rounds and message overhead across dynamic network topologies:

```powershell
python experiments/run_experiments.py
```

### 5. Run Network Anomaly Scenarios
Simulates real-world networking phenomena including transient forwarding loops, black holes, and link flapping storms:

```powershell
python events/scenarios.py
```

---

##  Running Unit & Integration Tests

The project includes an automated test suite containing **36 tests** across all modules.

### Run All Tests:
```powershell
python tests/run_all_tests.py
```

### Run Distance Vector Tests Specifically:
```powershell
python tests/test_distance_vector.py
```

Distance Vector tests verify:
- Initial route storage and self-route ($Cost = 0$).
- Route cost updates when cheaper paths are discovered (Bellman-Ford).
- Route retraction and marking destinations as `16 (UNREACHABLE)`.
- Split Horizon omission of next-hop routes.
- Poisoned Reverse advertising metric 16 back to the next hop.
- Step-by-step verification of the Count-to-Infinity simulation.
- JSON serialization and UDP message helpers.

---

##  Key Concepts & Theoretical Principles

### 1. Bellman-Ford Equation
Each router $x$ updates its estimated distance to destination $y$ based on the vectors advertised by direct neighbours $v$:
$$D_x(y) = \min_v \{ c(x, v) + D_v(y) \}$$

### 2. Count-to-Infinity Problem
When a link drops in simple Distance Vector without loop prevention, two adjacent routers can form a mutually dependent loop where each router believes the other has a valid path. The metric bounces upward ($3 \rightarrow 4 \rightarrow 5 \dots$) until reaching the metric infinity limit ($16$), causing slow convergence.

### 3. Split Horizon vs. Poisoned Reverse
- **Split Horizon**: A router does not advertise a route back out of the interface through which it learned it.
- **Poisoned Reverse**: A router advertises the route back to that neighbour, but sets the metric to $\infty = 16$ ("poisoning" the route). This provides an explicit guarantee that the neighbour cannot choose this router as a viable detour.
