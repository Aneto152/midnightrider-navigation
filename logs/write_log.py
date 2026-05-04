#!/usr/bin/env python3
"""
OC Logger — écrit logs/latest.json après chaque tâche.
Usage: python3 logs/write_log.py --init --task "description"
       python3 logs/write_log.py --step "nom" --cmd "commande" --out "output" --ok
       python3 logs/write_log.py --finalize --ok
"""
import json, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone

LOG_FILE = Path("logs/latest.json")
HIST_DIR = Path("logs/history")

def load():
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except:
            pass
    return {"task": "", "started": "", "steps": [], "status": "running", "sha": ""}

def save(data):
    LOG_FILE.parent.mkdir(exist_ok=True)
    # Toujours mettre à jour le SHA courant
    try:
        r = subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True)
        data["sha"] = r.stdout.strip()[:8]
    except:
        pass
    data["updated"] = datetime.now(timezone.utc).isoformat()
    LOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def init_task(task_name):
    data = {
        "task": task_name,
        "started": datetime.now(timezone.utc).isoformat(),
        "updated": "",
        "status": "running",
        "sha": "",
        "steps": []
    }
    save(data)
    print(f"✅ Log initialisé : {task_name}")

def add_step(name, cmd, output, ok):
    data = load()
    data["steps"].append({
        "step": name,
        "cmd": cmd[:200] if cmd else "",
        "output": output[:500] if output else "",
        "ok": ok,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    save(data)

def finalize(ok, commit=True):
    data = load()
    data["status"] = "success" if ok else "failed"
    save(data)
    # Archiver dans history/
    HIST_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    hist = HIST_DIR / f"{ts}.json"
    hist.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    if commit:
        subprocess.run("git add logs/ && git commit -m 'log: " + data['task'][:60] + " — " + data['status'] + "'", shell=True)
        subprocess.run("git push origin main", shell=True)
    print(f"{'✅' if ok else '❌'} Log finalisé : {data['status']}")

# CLI
if __name__ == "__main__":
    args = sys.argv[1:]
    def get(flag):
        return args[args.index(flag)+1] if flag in args else ""
    if "--init" in args:
        init_task(get("--task"))
    elif "--step" in args:
        add_step(get("--step"), get("--cmd"), get("--out"), "--ok" in args)
    elif "--finalize" in args:
        finalize("--ok" in args)
    else:
        print(json.dumps(load(), indent=2))
