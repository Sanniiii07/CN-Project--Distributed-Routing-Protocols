# AI Use Disclosure

This document discloses the use of AI tools in the development of the **Distributed Routing Protocols** project, in adherence to academic honesty policies.

## 1. Tool Used
- **Assistant:** Antigravity (Google DeepMind)
- **Primary Model:** Gemini 3.8 Flash

## 2. Scope of Assistance
AI assistance was utilized for:
- Code review and debugging existing repository inconsistencies.
- Explaining computer networking concepts (Path Vector, BGP-style AS-Path loop detection, event engines, Dijkstra differences).
- Generating test boilerplate and test suite validation (`tests/test_path_vector.py`, `tests/test_event_engine.py`).
- Structuring modular file interfaces for dynamic network events, convergence timelines, and comparative protocol benchmarks (`experiments/run_experiments.py`).

## 3. Human Authorship & Contribution Verification
- Core protocol logic, loop rejection algorithms, dynamic topology event scheduling (link failures, router crashes, cost changes), convergence anomaly detection, and convergence benchmarking were reviewed, verified, and integrated by **Sreejita** (Path Vector routing, Event Engine, Convergence Visualization, Comparative Experiments).
- Existing teammate contributions (Naitik's C network architecture, Sagar's Link State router) were preserved without unauthorized overwrites.
