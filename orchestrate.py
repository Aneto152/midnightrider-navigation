#!/usr/bin/env python3
"""
OC Orchestrator — Pipeline PLAN → CODE → VERIFY → COMMIT

Commandes Telegram reconnues (insensible à la casse) :
 TASK <description> → initialise la tâche, OC génère le plan
 GO → valide le plan, OC exécute le code (PHASE 2)
 VERIFY → lance la vérification automatique (PHASE 3)
 STATUS → état de la tâche en cours
 STOP → annule sans commit

Usage shell direct :
 python3 orchestrate.py init "description"
 python3 orchestrate.py verify
 python3 orchestrate.py status
 python3 orchestrate.py stop
"""
import json, subprocess, sys, os
from pathlib import Path
from datetime import datetime

TASK_FILE = Path("/tmp/oc-task.json")
REPO_ROOT = Path(__file__).parent


def run(cmd, cwd=None):
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(REPO_ROOT)
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def load_task():
    if TASK_FILE.exists():
        try:
            return json.loads(TASK_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_task(t):
    TASK_FILE.write_text(json.dumps(t, indent=2, ensure_ascii=False))


def cmd_init(description):
    """PHASE 1 : initialise une nouvelle tâche."""
    task = {
        "task": description,
        "created": datetime.now().isoformat(),
        "phase": "PLAN",
        "files": [],
        "criteria": [],
        "risks": [],
        "commit_msg": ""
    }
    save_task(task)
    return (
        f"📋 *PLAN EN COURS*\n"
        f"Tâche : _{description}_\n\n"
        f"OC analyse et génère le plan...\n"
        f"Quand le plan est prêt, réponds *GO* pour exécuter."
    )


def cmd_verify():
    """PHASE 3 : vérification automatique des critères."""
    task = load_task()
    if not task:
        return "❌ Pas de tâche en cours. Commence par : TASK <description>"

    criteria = task.get("criteria", [])
    if not criteria:
        return (
            "⚠️ *VERIFY*\n"
            "Aucun critère défini dans task.json.\n"
            "OC doit remplir le champ `criteria` pendant la PHASE 2.\n"
            "Vérifie manuellement et dis-moi si c'est OK."
        )

    lines = [f"🔍 *VERIFY — {task.get('task','')}*\n"]
    results = []
    for c in criteria:
        cmd = c.get("cmd", "")
        expected = c.get("expected", "")
        desc = c.get("desc", cmd[:60])
        code, out, err = run(cmd)
        ok = (expected.lower() in out.lower()) if expected else (code == 0)
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} {desc}")
        if not ok:
            lines.append(f" Attendu : `{expected}`")
            lines.append(f" Obtenu : `{(out or err)[:120]}`")
        results.append(ok)

    if all(results):
        # Commit automatique
        files = task.get("files", [])
        if files:
            run(f"git add {' '.join(files)}")
        else:
            run("git add -A")

        code, diff, _ = run("git diff --staged --stat")
        if not diff:
            lines.append("\nℹ️ Rien à commiter (déjà commité ou pas de changement).")
        else:
            msg = task.get("commit_msg") or f"feat: {task.get('task','update')[:60]}"
            run(f'git commit -m "{msg}"')
            run("git push origin main")
            _, sha_remote, _ = run("git ls-remote origin main")
            _, sha_local, _ = run("git rev-parse HEAD")
            ok_push = sha_local[:8] in sha_remote
            lines.append(f"\n✅ *Commit* : `{sha_local[:8]}`")
            lines.append(f"{'✅' if ok_push else '❌'} Push GitHub vérifié")

        # Nettoyer task.json
        TASK_FILE.unlink(missing_ok=True)
        lines.append("\n🏁 *DONE* — tâche terminée.")
    else:
        n_fail = sum(1 for r in results if not r)
        lines.append(f"\n❌ *{n_fail}/{len(results)} critère(s) échoué(s)* — commit annulé.")
        lines.append("Retour en PHASE 1. OC doit corriger et relancer.")

    return "\n".join(lines)


def cmd_status():
    task = load_task()
    if not task:
        return "ℹ️ Aucune tâche en cours."
    return (
        f"📊 *STATUS*\n"
        f"Tâche : _{task.get('task','?')}_\n"
        f"Phase : `{task.get('phase','?')}`\n"
        f"Fichiers : `{', '.join(task.get('files') or ['non défini'])}`\n"
        f"Critères : {len(task.get('criteria', []))} définis"
    )


def cmd_stop():
    if TASK_FILE.exists():
        task = load_task()
        TASK_FILE.unlink()
        return f"🛑 *Annulé* : _{task.get('task','')}_\nAucun fichier modifié, aucun commit."
    return "ℹ️ Pas de tâche en cours."


def route_telegram(message: str):
    """
    Point d'entrée depuis le handler Telegram d'OC.
    Retourne une réponse str si la commande est reconnue, None sinon.
    """
    msg = message.strip()
    upper = msg.upper()

    if upper.startswith("TASK ") or upper.startswith("TÂCHE "):
        desc = msg.split(" ", 1)[1].strip()
        return cmd_init(desc)
    elif upper == "GO":
        task = load_task()
        if not task:
            return "❌ Pas de tâche. Commence par : TASK <description>"
        task["phase"] = "CODE"
        save_task(task)
        return (
            f"⚙️ *PHASE CODE*\n"
            f"Tâche : _{task.get('task','')}_\n\n"
            f"OC exécute le plan. Une fois terminé, réponds *VERIFY*."
        )
    elif upper == "VERIFY":
        return cmd_verify()
    elif upper == "STATUS":
        return cmd_status()
    elif upper == "STOP":
        return cmd_stop()
    else:
        return None  # Pas une commande orchestrateur → OC traite normalement


# ── CLI direct ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "init":
        desc = " ".join(sys.argv[2:]) or "tâche test"
        print(cmd_init(desc))
    elif cmd == "verify":
        print(cmd_verify())
    elif cmd == "status":
        print(cmd_status())
    elif cmd == "stop":
        print(cmd_stop())
    else:
        print(f"Commande inconnue : {cmd}")
        sys.exit(1)
