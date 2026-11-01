@echo off
setlocal

echo =========================================================
echo   P7 Distributed Routing: 4-Router Process Launcher
echo =========================================================

REM Check if router_app.exe exists, build if missing
if not exist "router_app.exe" (
    echo [*] router_app.exe not found. Building with gcc...
    gcc -Wall -Wextra -std=c11 -O2 router/router.c router/network.c router/messages.c -o router_app.exe -lws2_32
    if errorlevel 1 (
        echo [ERROR] Build failed. Please ensure MinGW gcc is in your PATH.
        pause
        exit /b 1
    )
    echo [*] Build successful!
)

set TOPOLOGY=config\topology.conf
if not exist "%TOPOLOGY%" (
    echo [ERROR] Topology file "%TOPOLOGY%" not found!
    pause
    exit /b 1
)

echo.
echo Launching 4 router processes in separate terminal windows...
echo  - Router R1 (Port 5001)
echo  - Router R2 (Port 5002)
echo  - Router R3 (Port 5003)
echo  - Router R4 (Port 5004)
echo.

start "Router R1 [Port 5001]" cmd.exe /k "router_app.exe R1 %TOPOLOGY%"
start "Router R2 [Port 5002]" cmd.exe /k "router_app.exe R2 %TOPOLOGY%"
start "Router R3 [Port 5003]" cmd.exe /k "router_app.exe R3 %TOPOLOGY%"
start "Router R4 [Port 5004]" cmd.exe /k "router_app.exe R4 %TOPOLOGY%"

echo All 4 router processes launched successfully!
echo.
echo Quick interactive test commands in Router R1 window:
echo   hello R2
echo   send R2 DV_UPDATE R1=0;R2=2;R3=5;R4=8
echo   topology
echo   fail R2
echo   recover R2
echo.
pause
