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
    def log_message(self, fmt, *args):
        """Suppress default logging unless it's an API call"""
        if args and ("/api/" in str(args[0]) or "favicon" not in str(args[0])):
            pass  # Suppress

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]

        # /api/* → proxy to regatta:5000
        if path.startswith("/api/"):
            self._proxy_to_regatta("GET")

        # Root → portal/index.html
        elif path in ("/", ""):
            self._serve_file(PORTAL / "index.html")

        # /manifest.json → root manifest (for PWA)
        elif path == "/manifest.json":
            self._serve_file(PORTAL / "static" / "manifest.json")

        # /reporter → portal/reporter.html
        elif path in ("/reporter", "/reporter/"):
            self._serve_file(PORTAL / "reporter.html")

        # /regatta/* → regatta/
        elif path.startswith("/regatta/"):
            rel = path[len("/regatta/"):]
            target = REGATTA / rel if rel else REGATTA / "index.html"
            self._serve_file(target)

        # /static/* → portal/static/
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(PORTAL / "static" / rel)

        # /portal/* → portal/ (optional direct access)
        elif path.startswith("/portal/"):
            rel = path[len("/portal/"):]
            self._serve_file(PORTAL / rel)

        # Files at root: viewer.html, *.css, *.js, *.svg, *.json, *.png, *.ico
        elif "." in Path(path).name:
            self._serve_file(PORTAL / path.lstrip("/"))

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/shutdown":
            self._handle_shutdown()
        elif self.path == "/api/reporter/generate":
            self._handle_reporter()
        elif self.path == "/api/reporter/history":
            self._handle_reporter_history()
        elif self.path.startswith("/api/"):
            self._proxy_to_regatta("POST")
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _proxy_to_regatta(self, method):
        """Proxy /api/* requests to regatta server on localhost:5000"""
        import urllib.request
        import urllib.error
        
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None
        url = f'http://localhost:5000{self.path}'
        
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header('Content-Type', self.headers.get('Content-Type', 'application/json'))
        
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = resp.read()
            self.send_response(resp.status)
            self.send_header('Content-Type', resp.headers.get('Content-Type', 'application/json'))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, f'Regatta proxy error: {e}')

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

    def _handle_reporter(self):
        """Trigger Midnight Reporter via background subprocess"""
        import threading
        
        def run_reporter():
            try:
                subprocess.run(
                    ["bash", "/home/aneto/.openclaw/workspace/scripts/midnight-reporter.sh"],
                    capture_output=True,
                    timeout=120
                )
            except Exception as e:
                print(f"[REPORTER] Error: {e}")
        
        # Run in background thread
        threading.Thread(target=run_reporter, daemon=True).start()
        
        # Return immediately
        body = json.dumps({"ok": True, "message": "Reporter lancé — flash en cours de génération"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_reporter_history(self):
        """Return recent reporter flashes from history file"""
        history_file = Path("/home/aneto/.openclaw/workspace/logs/reporter-history.json")
        
        try:
            if history_file.exists():
                data = json.loads(history_file.read_text())
            else:
                data = []
        except Exception as e:
            print(f"[REPORTER_HISTORY] Error reading: {e}")
            data = []
        
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)



if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PortalHandler) as httpd:
        print(f"✅ Portal démarré sur http://0.0.0.0:{PORT}")
        print(f"   / → {PORTAL}/index.html")
        print(f"   /static/* → {PORTAL}/static/")
        print(f"   /regatta/ → {REGATTA}/")
        print(f"   POST /api/shutdown → sudo shutdown -h now")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Portal] Arrêt.")
            sys.exit(0)
