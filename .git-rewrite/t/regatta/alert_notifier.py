#!/usr/bin/env python3
"""
MidnightRider — Notificateur d'alertes
Lit la queue des alertes et les envoie via OpenClaw Telegram
Lancé toutes les 2 minutes par cron
"""

import json, time, os, urllib.request, urllib.parse

ALERT_QUEUE = "/tmp/mr_alerts.json"
SENT_MARKER = "/tmp/mr_alerts_sent.json"
OPENCLAW_URL = "http://localhost:18791"  # API OpenClaw locale

def get_unsent_alerts():
    if not os.path.exists(ALERT_QUEUE):
        return []
    try:
        with open(ALERT_QUEUE) as f:
            alerts = json.load(f)
    except:
        return []

    # Charger les alertes déjà envoyées
    sent = set()
    if os.path.exists(SENT_MARKER):
        try:
            with open(SENT_MARKER) as f:
                sent = set(json.load(f))
        except:
            pass

    # Filtrer : non envoyées et récentes (< 10 min)
    now = time.time()
    new_alerts = []
    for a in alerts:
        key = f"{a.get('time',0):.0f}_{hash(a.get('message',''))}"
        if key not in sent and now - a.get("time", 0) < 600:
            new_alerts.append((key, a))

    return new_alerts

def send_telegram(message):
    """Envoyer via l'API OpenClaw locale"""
    try:
        payload = json.dumps({
            "channel": "telegram",
            "to": "8686179485",
            "text": message
        }).encode()
        req = urllib.request.Request(
            f"{OPENCLAW_URL}/api/message",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        # Fallback: écrire dans un fichier que l'agent lira
        with open("/tmp/mr_pending_message.txt", "a") as f:
            f.write(f"{message}\n---\n")
        return False

def main():
    unsent = get_unsent_alerts()
    if not unsent:
        return

    sent = set()
    if os.path.exists(SENT_MARKER):
        try:
            with open(SENT_MARKER) as f:
                sent = set(json.load(f))
        except:
            pass

    for key, alert in unsent:
        msg = alert.get("message", "")
        if msg:
            send_telegram(msg)
            sent.add(key)

    # Sauvegarder les clés envoyées (garder 1h)
    with open(SENT_MARKER, "w") as f:
        json.dump(list(sent), f)

if __name__ == "__main__":
    main()
