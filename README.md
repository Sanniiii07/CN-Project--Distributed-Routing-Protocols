# P7 Distributed Routing Protocols — C / Windows MinGW

## What this code currently provides

- Weighted topology loaded from `config/topology.conf`
- One independent process per router
- UDP communication using Windows Winsock2
- Router message encoding/decoding
- Sequence number and TTL fields
- Local link failure/recovery/cost-change controls
- Per-router send/receive logs
- A clean transport API for later DV, LS and Path Vector modules

This is the networking infrastructure layer. It is intentionally not the final DV/LS/PV algorithm implementation.

## Required environment

- Windows
- MinGW GCC (tested for compatibility with older GCC-style Windows toolchains such as MinGW GCC 6.3)
- No `make` command is required for the steps below

## Build — recommended PowerShell command

Open PowerShell in the project root and run:

```powershell
gcc -Wall -Wextra -std=c11 -O2 router/router.c router/network.c router/messages.c -o router_app.exe -lws2_32
```

Or double-click `build.bat`.

## Start routers

Open four VS Code terminals in the project root.

Terminal 1:

```powershell
.\router_app.exe R1 config/topology.conf
```

Terminal 2:

```powershell
.\router_app.exe R2 config/topology.conf
```

Terminal 3:

```powershell
.\router_app.exe R3 config/topology.conf
```

Terminal 4:

```powershell
.\router_app.exe R4 config/topology.conf
```

## Test communication

In the R1 terminal:

```text
hello R2
```

R1 should show:

```text
[SEND] HELLO -> R2
```

R2 should show a received `HELLO` message.

Then test a routing-style message from R1:

```text
send R2 DV_UPDATE R1=0;R2=2;R3=5;R4=8
```

## Test local events

```text
show
topology
fail R2
show
recover R2
cost R2 10
show
```

## Important architecture rule for the team

The DV, Link State and Path Vector implementations should use:

```text
network_send()
network_receive()
```

They should not create another UDP implementation. This keeps the project modular.

## GitHub

Recommended repository name:

`P7-distributed-routing`

Do not commit `router_app.exe`, object files, or generated logs.
