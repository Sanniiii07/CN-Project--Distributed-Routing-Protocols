# AI Use Disclosure

This document discloses the use of AI tools in the development of the **Distributed Routing Protocols** project, in adherence to academic honesty policies.

## 1. Tool Used
- **Assistant:** Antigravity (Google DeepMind)
- **Primary Model:** Gemini 3.8 Flash

## 2. Scope of Assistance
AI assistance was utilized for:
- Code review, structuring modular interfaces, and debugging repository inconsistencies.
- Explaining computer networking concepts (Bellman-Ford, Split Horizon, Poisoned Reverse, Count-to-Infinity, Path Vector loop detection, Dijkstra differences).
- Generating test boilerplate and test suite validation (`tests/test_distance_vector.py`, `tests/test_path_vector.py`, `tests/test_event_engine.py`, `tests/test_scenarios.py`, `tests/test_pv_router_udp.py`, `tests/run_all_tests.py`).
- Structuring modular file interfaces for dynamic network events, convergence timelines, comparative protocol benchmarks (`experiments/run_experiments.py`), count-to-infinity loop experiments (`experiments/count_to_infinity.py`), and independent UDP socket process execution (`router/dv_router.py`, `router/pv_router.py`).

## 3. Human Authorship & Contribution Verification
- **Sanniva** (Member 2): Distance Vector algorithm implementation, RoutingTable data structure, Split Horizon and Poisoned Reverse loop mitigations, UDP socket integration for Distance Vector (`router/dv_router.py`), Count-to-Infinity experiment and comparative validation (`experiments/count_to_infinity.py`), and dedicated unit tests (`tests/test_distance_vector.py`).
- **Sreejita** (Member 4): Path Vector routing with loop detection, dynamic Event Engine, convergence visualization, comparative benchmarks (`experiments/run_experiments.py`), anomaly scenarios (`events/scenarios.py`), Path Vector UDP router (`router/pv_router.py`), and master test orchestration.
- **Sagar** (Member 3): Link State routing logic, Dijkstra shortest-path calculations, and LSA database flooding.
- **Naitik** (Member 1): Base network topology loader, router socket infrastructure, and C communication layers.
