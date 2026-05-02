#!/usr/bin/env python3
"""
Midnight Rider Portal Server — port 8888
Wraps SimpleHTTPServer + /api/shutdown endpoint
"""
import http.server
import socketserver
import subprocess
import json
import sys
from pathlib import Path

PORT = 8888
BASE_DIR = Path(__file__).parent.parent

class ShutdownHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_POST(self):
        if self.path == "/api/shutdown":
            self._handle_shutdown()
        else:
            self.send_error(404, "Not Found")

    def _handle_shutdown(self):
        length = int(self.headers.get("Content-Length", 0)) or 0
        if length > 0:
            self.rfile.read(length)

        response = json.dumps({"status": "ok", "message": "Shutdown initiated"})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode())
        self.wfile.flush()

        print("[SHUTDOWN] Shutdown requested from portal")
        try:
            subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            print(f"[ERROR] Shutdown failed: {e}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if args and "/api/" in args[0]:
            print(f"[Portal API] {format % args}")

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ShutdownHandler) as httpd:
        print(f"✅ Portal server running on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Portal] Shutting down...")
            sys.exit(0)
