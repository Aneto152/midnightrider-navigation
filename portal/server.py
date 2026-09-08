#!/usr/bin/env python3
"""Midnight Rider Portal Server — port 8888"""
import http.server, socketserver, subprocess, json, logging, urllib.request, urllib.error
from pathlib import Path
from logging.handlers import RotatingFileHandler

PORT = 8888
ROOT = Path(__file__).parent.parent
PORTAL = ROOT / "portal"
REGATTA = ROOT / "regatta"
AIS = ROOT / "ais"

ALLOWED = [PORTAL.resolve(), REGATTA.resolve(), AIS.resolve()]
MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
}

def _setup_logger():
    log_dir = ROOT / "logs" / "services"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("portal")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = RotatingFileHandler(log_dir / "portal.log", maxBytes=5*1024*1024, backupCount=3)
        h.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"))
        logger.addHandler(h)
    return logger

log = _setup_logger()

class PortalHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        msg = fmt % args
        if "favicon" not in msg:
            log.info(msg)

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        if path.startswith("/api/"): self._proxy("GET")
        elif path in ("/", ""): self._serve(PORTAL / "index.html")
        elif path == "/manifest.json": self._serve(PORTAL / "static" / "manifest.json")
        elif path in ("/mcp", "/mcp/"): self._serve(PORTAL / "mcp.html")
        elif path in ("/reporter", "/reporter/"): self._serve(PORTAL / "reporter.html")
        elif path in ("/ais", "/ais/"): self._serve(AIS / "tracker.html")
        elif path in ("/ais/fleet_db", "/ais/fleet_db/"): self._serve(AIS / "fleet_db.html")
        elif path.startswith("/ais/"): self._serve(AIS / path[5:])
        elif path.startswith("/regatta/"): self._serve(REGATTA / path[9:])
        elif path.startswith("/static/"): self._serve(PORTAL / "static" / path[8:])
        else:
            try: self._serve(PORTAL / path.lstrip("/"))
            except: self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/"): self._proxy("POST")
        else: self.send_error(404)

    def _serve(self, filepath):
        filepath = Path(filepath)
        try:
            if not any(filepath.resolve().is_relative_to(root) for root in ALLOWED):
                self.send_error(403)
                return
        except: self.send_error(403); return
        if not filepath.exists(): self.send_error(404); return
        suffix = filepath.suffix.lower()
        ct = MIME.get(suffix, "application/octet-stream")
        data = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        if suffix == ".html": self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        url = f"http://localhost:5000{self.path}"
        req = urllib.request.Request(url, data=body, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read()
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            log.error(f"Proxy error {self.path}: {e}")
            self.send_error(502)

class MidnightRiderPortal(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    log.info(f"[STARTUP] Midnight Rider Portal v2.0 — port {PORT}")
    with MidnightRiderPortal(("", PORT), PortalHandler) as httpd:
        log.info(f"[STARTUP] Listening 0.0.0.0:{PORT}")
        try: httpd.serve_forever()
        except KeyboardInterrupt: log.info("[SHUTDOWN] Portal stopped")
