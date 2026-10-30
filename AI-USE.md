# AI Use Disclosure

This document discloses the use of AI tools in the development of the **Distributed Routing Protocols** project, in adherence to academic honesty policies.

## 1. Tool Used
- **Assistant:** Antigravity (Google DeepMind)
- **Primary Model:** Gemini 3.8 Flash

## 2. Scope of Assistance
AI assistance was utilized for:
- Code review and debugging existing repository inconsistencies.
- Explaining computer networking concepts (Path Vector, BGP-style AS-Path loop detection, event engines, Dijkstra differences).
- Generating test boilerplate and test suite validation (`tests/test_path_vector.py`, `tests/test_event_engine.py`, `tests/test_scenarios.py`, `tests/test_pv_router_udp.py`).
- Structuring modular file interfaces for dynamic network events, convergence timelines, comparative protocol benchmarks (`experiments/run_experiments.py`), anomaly demonstrations (`events/scenarios.py`), and independent UDP socket process execution (`router/pv_router.py`).

## 3. Human Authorship & Contribution Verification
- Core protocol logic, loop rejection algorithms, dynamic topology event scheduling (link failures, router crashes, cost changes), convergence anomaly detection, benchmarking, network anomaly scenarios (transient loops, black holes, link flapping), and real UDP process communication were reviewed, verified, and integrated by **Sreejita** (Path Vector routing, Event Engine, Convergence Visualization, Comparative Experiments, Anomaly Scenarios, PV UDP Router).
- Existing teammate contributions (Naitik's C network architecture, Sagar's Link State router, Sanniva's Distance Vector protocol) were preserved without unauthorized overwrites.
