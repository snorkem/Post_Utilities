"""
Script Generators
Generates helper scripts for running the directory indexer viewer
"""

import os
from ..config.settings import ServerConfig


def generate_server_script(output_dir: str, html_filename: str, port: int = ServerConfig.DEFAULT_PORT) -> str:
    """
    Generate a simple Python HTTP server script for viewing the database mode files.

    Args:
        output_dir: Directory where the server script will be created
        html_filename: Name of the HTML file to serve
        port: Port number for the server (default from ServerConfig)

    Returns:
        Path to the generated server script
    """
    server_script = f'''#!/usr/bin/env python3
"""
Simple HTTP Server for Directory Index Viewer
Serves the HTML file and database with proper CORS headers

Usage:
    python serve.py [port]

Default port: {port}
"""
import http.server
import socketserver
import socket
import os
import sys

# Port configuration
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else {port}

# If using default port, check availability and find next available port
if len(sys.argv) <= 1:
    def is_port_available(port):
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False

    original_port = PORT
    while not is_port_available(PORT):
        PORT += 1
        if PORT > 65535:  # Max valid port number
            print(f"Error: Could not find available port starting from {{original_port}}")
            sys.exit(1)

    if PORT != original_port:
        print(f"Note: Default port {{original_port}} was in use, using port {{PORT}} instead")

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers for local file access"""

    def end_headers(self):
        # Allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        # Prevent caching for development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        # Customize log format
        sys.stderr.write("[%s] %s\\n" % (self.log_date_time_string(), format % args))

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    Handler = CORSRequestHandler

    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            # Output port for launcher scripts to parse (flush immediately)
            print(f"ACTUAL_PORT={{PORT}}", flush=True)
            sys.stdout.flush()
            print("=" * 60)
            print("Directory Index Viewer Server")
            print("=" * 60)
            print(f"Serving at http://localhost:{{PORT}}")
            print(f"\\nOpen in browser: http://localhost:{{PORT}}/{html_filename}")
            print("\\nPress Ctrl+C to stop the server")
            print("=" * 60)
            sys.stdout.flush()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\n\\nServer stopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {{PORT}} is already in use.")
            print(f"Try a different port: python serve.py <port_number>")
            sys.exit(1)
        else:
            raise
'''

    server_path = os.path.join(output_dir, 'serve.py')
    with open(server_path, 'w') as f:
        f.write(server_script)

    # Make executable on Unix-like systems
    try:
        os.chmod(server_path, 0o755)
    except (NotImplementedError, OSError):
        pass  # Windows doesn't support chmod or filesystem doesn't support permissions

    return server_path


def generate_launcher_scripts(
    macos_dir: str,
    windows_dir: str,
    html_filename: str,
    port: int = ServerConfig.DEFAULT_PORT
) -> tuple:
    """
    Generate cross-platform launcher scripts for macOS and Windows.

    Args:
        macos_dir: Directory where macOS .command script will be created
        windows_dir: Directory where Windows .bat script will be created
        html_filename: Name of the HTML file to open
        port: Port number for the server (default from ServerConfig)

    Returns:
        Tuple of (macos_script_path, windows_script_path)
    """
    # macOS .command script (zsh) - navigates to ../data/
    macos_script = f'''#!/bin/zsh
# Directory Index Viewer Launcher (macOS)
# Double-click this file to start the server and open the viewer

# Get the directory where this script is located and navigate to data folder
SCRIPT_DIR="${{0:a:h}}"
cd "$SCRIPT_DIR/../data"

echo "============================================================"
echo "Starting Directory Index Viewer"
echo "============================================================"
echo ""
echo "Working directory: $(pwd)"
echo ""

# Create temporary log file using mktemp for better cleanup
LOG_FILE=$(mktemp /tmp/serve_output_XXXXXX.log)

# Start the Python server in background and capture output
# Note: Not passing port argument to allow auto-port detection
python3 serve.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

echo "Server PID: $SERVER_PID"
echo "Server starting..."
echo ""

# Wait for server to start and output port (polling with timeout)
ACTUAL_PORT=""
MAX_ATTEMPTS=20  # 20 attempts * 0.5s = 10 seconds max wait
ATTEMPT=0

while [ -z "$ACTUAL_PORT" ] && [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 0.5
    ACTUAL_PORT=$(grep -m 1 "^ACTUAL_PORT=" "$LOG_FILE" 2>/dev/null | cut -d= -f2)
    ATTEMPT=$((ATTEMPT + 1))
done

if [ -z "$ACTUAL_PORT" ]; then
    echo "Warning: Could not detect server port, using default {port}"
    ACTUAL_PORT={port}
fi

echo "Server started on http://localhost:$ACTUAL_PORT"
echo ""

# Open in default browser
echo "Opening browser..."
open "http://localhost:$ACTUAL_PORT/{html_filename}"
echo ""
echo "Server is running. Close this window to stop the server."
echo "============================================================"
echo ""

# Tail server output in background
tail -f "$LOG_FILE" &
TAIL_PID=$!

# Cleanup function
cleanup() {{
    echo "\\nStopping server..."
    kill $SERVER_PID 2>/dev/null
    kill $TAIL_PID 2>/dev/null
    rm -f "$LOG_FILE"
}}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Wait for user to close terminal (keeps server running)
wait $SERVER_PID
'''

    # Windows .bat script - navigates to ..\data\
    windows_script = f'''@echo off
REM Directory Index Viewer Launcher (Windows)
REM Double-click this file to start the server and open the viewer

REM Get the directory where this script is located and navigate to data folder
cd /d "%~dp0..\\data"

echo ============================================================
echo Starting Directory Index Viewer
echo ============================================================
echo.
echo Working directory: %CD%
echo.

REM Set temporary files
set LOG_FILE=%TEMP%\\serve_output_%RANDOM%.log
set PID_FILE=%TEMP%\\serve_pid_%RANDOM%.txt

REM Start the Python server in background and capture output
REM Note: Not passing port argument to allow auto-port detection
start /b cmd /c "python serve.py > %LOG_FILE% 2>&1"

REM Capture the PID using WMIC (wait a moment for process to start)
timeout /t 1 /nobreak >nul
for /f "tokens=2 delims=," %%i in ('wmic process where "commandline like '%%python%%serve.py%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    echo %%i > %PID_FILE%
)

echo Server starting...
echo.

REM Wait for server to start and output port
timeout /t 2 /nobreak >nul

REM Extract the actual port from server output
set ACTUAL_PORT=
for /f "tokens=2 delims==" %%i in ('findstr /b "ACTUAL_PORT=" %LOG_FILE% 2^>nul') do set ACTUAL_PORT=%%i

REM If port not found, use default
if "%ACTUAL_PORT%"=="" (
    echo Warning: Could not detect server port, using default {port}
    set ACTUAL_PORT={port}
)

echo Server started on http://localhost:%ACTUAL_PORT%
echo.

REM Open in default browser
echo Opening browser...
start http://localhost:%ACTUAL_PORT%/{html_filename}

echo.
echo Server is running. Press any key to stop the server.
echo ============================================================
echo.

REM Keep window open and wait
pause >nul

REM Cleanup
echo.
echo Stopping server...

REM Use stored PID if available, otherwise fall back to command line matching
if exist %PID_FILE% (
    set /p SERVER_PID=<%PID_FILE%
    taskkill /f /pid %SERVER_PID% >nul 2>&1
    del /f /q %PID_FILE% >nul 2>&1
) else (
    REM Fallback: find and kill by command line
    for /f "tokens=2 delims=," %%i in ('wmic process where "commandline like '%%python%%serve.py%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
        taskkill /f /pid %%i >nul 2>&1
    )
)

del /f /q %LOG_FILE% >nul 2>&1
'''

    # Write macOS script
    macos_path = os.path.join(macos_dir, 'start-viewer.command')
    with open(macos_path, 'w') as f:
        f.write(macos_script)

    # Make macOS script executable
    try:
        os.chmod(macos_path, 0o755)
    except (NotImplementedError, OSError):
        pass

    # Write Windows script
    windows_path = os.path.join(windows_dir, 'start-viewer.bat')
    with open(windows_path, 'w') as f:
        f.write(windows_script)

    return macos_path, windows_path
