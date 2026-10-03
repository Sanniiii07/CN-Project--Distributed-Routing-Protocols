@echo off
setlocal

echo ========================================
echo Building P7 Distributed Routing Project
echo ========================================

gcc -Wall -Wextra -std=c11 -O2 router/router.c router/network.c router/messages.c -o router_app.exe -lws2_32

if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo BUILD SUCCESSFUL: router_app.exe
pause
