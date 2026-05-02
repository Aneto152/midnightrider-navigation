#!/usr/bin/env python3
"""
Midnight Rider Portal Server — port 8888
- Serve portal/ as root (/)
- Serve regatta/ under /regatta/
- POST /api/shutdown → sudo shutdown -h now
- Block access outside portal/ and regatta/ (security)
"""
import http.server
import socketserver
import subprocess
import json
import sys
from pathlib import Path

PORT = 8888
ROOT = Path(__file__).parent.parent
PORTAL = ROOT / "portal"
REGATTA = ROOT / "regatta"

class PortalHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]

        # Root → portal/index.html
        if path in ("/", ""):
            self._serve_file(PORTAL / "index.html")

        # /regatta/* → regatta/
        elif path.startswith("/regatta/"):
            rel = path[len("/regatta/"):]
            target = REGATTA / rel if rel else REGATTA / "index.html"
            self._serve_file(target)

        # /portal/* → portal/ (optional direct access)
        elif path.startswith("/portal/"):
            rel = path[len("/portal/"):]
            self._serve_file(PORTAL / rel)

        # Files at root: viewer.html, *.css, *.js, *.svg
        elif "." in Path(path).name:
            self._serve_file(PORTAL / path.lstrip("/"))

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/shutdown":
            self._handle_shutdown()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_file(self, filepath):
        filepath = Path(filepath)
        
        # Security: verify file is within portal/ or regatta/
        try:
            filepath.resolve().relative_to(ROOT.resolve())
        except ValueError:
            self.send_error(403, "Forbidden")
            return

        if not filepath.exists():
            self.send_error(404, f"Not Found: {filepath.name}")
            return

        # MIME types
        MIME = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        mime = MIME.get(filepath.suffix, "application/octet-stream")
        data = filepath.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_shutdown(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            self.rfile.read(length)

        body = json.dumps({"status": "ok", "message": "Arrêt initié"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

        print("[SHUTDOWN] Arrêt demandé depuis le portal")
        try:
            subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            print(f"[ERROR] shutdown failed: {e}")

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            print(f"[Portal] {fmt % args}")

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PortalHandler) as httpd:
        print(f"✅ Portal démarré sur http://0.0.0.0:{PORT}")
        print(f"   / → {PORTAL}/index.html")
        print(f"   /regatta/ → {REGATTA}/")
        print(f"   POST /api/shutdown → sudo shutdown -h now")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Portal] Arrêt.")
            sys.exit(0)
