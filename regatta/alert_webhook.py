#!/usr/bin/env python3
"""
MidnightRider — Webhook d'alertes Grafana
Reçoit les alertes Grafana et les envoie via OpenClaw (fichier queue)
Port: 5001
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json, time, os, threading

ALERT_QUEUE = "/tmp/mr_alerts.json"
ALERT_LOG = "/home/aneto/docker/signalk/alerts.log"

# File d'attente des alertes en mémoire
alerts_queue = []
queue_lock = threading.Lock()

def log_alert(msg):
    ts = time.strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}\n"
    try:
        with open(ALERT_LOG, "a") as f:
            f.write(line)
    except:
        pass

def format_alert(data):
    """Formater une alerte Grafana en message lisible"""
    title = data.get("title", "Alerte")
    state = data.get("state", "alerting")
    msg = data.get("message", "")

    icon = "🚨" if state == "alerting" else "✅" if state == "ok" else "⚠️"

    lines = [f"{icon} **{title}**"]
    if msg:
        lines.append(msg)

    # Extraire les valeurs des évaluations
    evals = data.get("evalMatches", []) or []
    for e in evals:
        metric = e.get("metric", "")
        value = e.get("value", "")
        if metric and value is not None:
            lines.append(f"  • {metric}: {value:.1f}" if isinstance(value, float) else f"  • {metric}: {value}")

    # Annotations Grafana 9+
    alerts = data.get("alerts", [])
    for a in alerts[:3]:
        labels = a.get("labels", {})
        vals = a.get("values", {})
        ann = a.get("annotations", {})
        summary = ann.get("summary", "") or ann.get("description", "")
        if summary:
            lines.append(f"  {summary}")
        for k, v in vals.items():
            try:
                lines.append(f"  • {k}: {float(v):.1f}")
            except:
                lines.append(f"  • {k}: {v}")

    return "\n".join(lines)

class AlertHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

        try:
            data = json.loads(body)
            msg = format_alert(data)
            log_alert(msg.replace("\n", " | "))

            # Écrire dans la queue pour OpenClaw
            with queue_lock:
                alerts_queue.append({
                    "time": time.time(),
                    "message": msg,
                    "state": data.get("state", "alerting")
                })
                # Conserver seulement les 50 dernières
                while len(alerts_queue) > 50:
                    alerts_queue.pop(0)

            # Écrire dans le fichier queue
            with open(ALERT_QUEUE, "w") as f:
                json.dump(alerts_queue[-10:], f)

        except Exception as e:
            log_alert(f"Parse error: {e}")

    def do_GET(self):
        if self.path == "/alerts":
            body = json.dumps(alerts_queue[-20:]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    server = HTTPServer(("0.0.0.0", 5001), AlertHandler)
    print("Alert webhook on :5001", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    start_server()
