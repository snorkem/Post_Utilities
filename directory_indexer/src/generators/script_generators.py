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
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else {port}

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
            print("=" * 60)
            print("Directory Index Viewer Server")
            print("=" * 60)
            print(f"Serving at http://localhost:{{PORT}}")
            print(f"\\nOpen in browser: http://localhost:{{PORT}}/{html_filename}")
            print("\\nPress Ctrl+C to stop the server")
            print("=" * 60)
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

# Start the Python server in background
python3 serve.py {port} &
SERVER_PID=$!

echo "Server starting on http://localhost:{port}"
echo "Server PID: $SERVER_PID"
echo ""

# Wait for server to initialize
sleep 2

# Open in default browser
echo "Opening browser..."
open "http://localhost:{port}/{html_filename}"
echo ""
echo "Server is running. Close this window to stop the server."
echo "============================================================"
echo ""

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

REM Start the Python server
echo Starting server on http://localhost:{port}
start /b python serve.py {port}

REM Wait for server to initialize
timeout /t 2 /nobreak >nul

REM Open in default browser
echo Opening browser...
start http://localhost:{port}/{html_filename}

echo.
echo Server is running. Press Ctrl+C or close this window to stop.
echo ============================================================
echo.

REM Keep window open and wait
pause
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
