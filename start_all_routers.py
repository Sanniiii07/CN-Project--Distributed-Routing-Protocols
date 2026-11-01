#!/usr/bin/env python3
"""
Process Launcher Script for Distributed Routing Protocols.
Launches all configured router instances in separate terminal windows with one command.

Supports:
  - C Winsock router instances (router_app.exe)
  - Distance Vector Python routers (DVRouter)
  - Path Vector Python routers (PVRouterProcess)
  - Link State Python routers (LSRouter)
"""

import argparse
import os
import subprocess
import sys
import time
from typing import List

# Setup project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.topology_loader import load_topology, Topology


def check_and_build_c_executable() -> str:
    """Verifies that router_app.exe exists, compiling it if necessary."""
    exe_name = "router_app.exe" if sys.platform == "win32" else "router_app"
    exe_path = os.path.join(PROJECT_ROOT, exe_name)

    if os.path.isfile(exe_path):
        return exe_path

    print(f"[*] {exe_name} not found. Attempting to compile from C sources...")
    src_files = [
        os.path.join(PROJECT_ROOT, "router", "router.c"),
        os.path.join(PROJECT_ROOT, "router", "network.c"),
        os.path.join(PROJECT_ROOT, "router", "messages.c"),
    ]
    compile_cmd = ["gcc", "-Wall", "-Wextra", "-std=c11", "-O2"] + src_files + ["-o", exe_path]
    if sys.platform == "win32":
        compile_cmd.append("-lws2_32")

    result = subprocess.run(compile_cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"[ERROR] Compilation failed with exit code {result.returncode}.")
        sys.exit(1)

    print(f"[*] Compilation successful: {exe_name}")
    return exe_path


def launch_in_new_window(cmd_args: List[str], window_title: str) -> subprocess.Popen:
    """
    Spawns a process in a new independent terminal/console window.
    Supports Windows (CREATE_NEW_CONSOLE / cmd.exe start) and POSIX.
    """
    if sys.platform == "win32":
        # Launch cmd.exe /k so window remains open even if program finishes or prints errors
        full_cmd = f'start "{window_title}" cmd.exe /k ' + " ".join(f'"{arg}"' for arg in cmd_args)
        return subprocess.Popen(full_cmd, shell=True, cwd=PROJECT_ROOT)
    elif sys.platform == "darwin":
        # macOS Terminal.app via osascript
        cmd_str = " ".join(cmd_args)
        osa_cmd = f'tell application "Terminal" to do script "{cmd_str}"'
        return subprocess.Popen(["osascript", "-e", osa_cmd], cwd=PROJECT_ROOT)
    else:
        # Linux / X11 terminal fallback
        terms = ["x-terminal-emulator", "gnome-terminal", "xterm", "konsole"]
        for term in terms:
            try:
                return subprocess.Popen([term, "-e"] + cmd_args, cwd=PROJECT_ROOT)
            except FileNotFoundError:
                continue
        # Fallback to background process
        return subprocess.Popen(cmd_args, cwd=PROJECT_ROOT)


def launch_c_routers(topology: Topology, conf_path: str) -> List[subprocess.Popen]:
    """Launches one router_app.exe instance per configured router."""
    exe_path = check_and_build_c_executable()
    router_ids = topology.get_all_router_ids()
    rel_conf = os.path.relpath(conf_path, PROJECT_ROOT)

    procs = []
    print(f"\n[*] Launching {len(router_ids)} C router instances in separate windows...")
    for r_id in router_ids:
        r_info = topology.get_router(r_id)
        port = r_info.port if r_info else "?"
        title = f"Router {r_id} [Port {port}]"
        cmd = [exe_path, r_id, rel_conf]
        print(f"  -> Starting {r_id} (Port {port}): {cmd[0]} {r_id} {rel_conf}")
        proc = launch_in_new_window(cmd, title)
        procs.append(proc)
        time.sleep(0.3)

    return procs


def launch_python_dv_routers(topology: Topology) -> List[subprocess.Popen]:
    """Launches Python Distance Vector router instances."""
    router_ids = topology.get_all_router_ids()
    procs = []
    print(f"\n[*] Launching {len(router_ids)} Python DV router instances in separate windows...")

    for r_id in router_ids:
        r_info = topology.get_router(r_id)
        port = r_info.port if r_info else 5000
        nbrs = topology.get_neighbors(r_id)
        title = f"DV Router {r_id} [Port {port}]"

        py_code = (
            f"import os, sys; sys.path.insert(0, r'{PROJECT_ROOT}'); "
            f"from router.dv_router import DVRouter; "
            f"r = DVRouter(router_id='{r_id}', port={port}, neighbours={nbrs}); "
            f"r.start(); print('Router {r_id} running on port {port}. Press Ctrl+C to stop.'); "
            f"import time; "
            f"try:\n"
            f"    while True: time.sleep(1)\n"
            f"except KeyboardInterrupt:\n"
            f"    r.stop()"
        )

        cmd = [sys.executable, "-c", py_code]
        proc = launch_in_new_window(cmd, title)
        procs.append(proc)
        time.sleep(0.3)

    return procs


def main():
    parser = argparse.ArgumentParser(
        description="Launch all distributed router instances in separate terminal windows."
    )
    parser.add_argument(
        "--config",
        "-c",
        default=os.path.join(PROJECT_ROOT, "config", "topology.conf"),
        help="Path to topology configuration file (default: config/topology.conf)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["c", "dv", "pv"],
        default="c",
        help="Router implementation mode to launch (c=router_app.exe, dv=Distance Vector, pv=Path Vector)",
    )

    args = parser.parse_args()

    print("=========================================================")
    print("      Distributed Routing Protocols: Process Launcher    ")
    print("=========================================================")

    try:
        topo = load_topology(args.config)
    except Exception as exc:
        print(f"[ERROR] Failed to load topology file: {exc}")
        sys.exit(1)

    topo.display()

    if args.mode == "c":
        launch_c_routers(topo, args.config)
        print("\n[OK] All C router processes have been opened in separate console windows.")
        print("Try interactive commands in the R1 window:")
        print("  hello R2")
        print("  send R2 DV_UPDATE R1=0;R2=2;R3=5;R4=8")
        print("  topology")
        print("  fail R2")
        print("  recover R2")
    elif args.mode == "dv":
        launch_python_dv_routers(topo)
        print("\n[OK] All Python Distance Vector routers opened in separate windows.")
    elif args.mode == "pv":
        print("\n[*] For automated Path Vector testing, you can also run: python tests/test_pv_router_udp.py")
        launch_python_dv_routers(topo)

    print("\nPress Enter to exit launcher (spawned router windows will remain open)...")
    try:
        input()
    except EOFError:
        pass


if __name__ == "__main__":
    main()
