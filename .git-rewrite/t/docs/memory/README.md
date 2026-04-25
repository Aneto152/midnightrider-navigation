# 📚 Memory System for MidnightRider Assistant

This directory contains the **persistent memory** for the MidnightRider assistant.

## Why This Exists

The assistant restarts with every new session and has no built-in memory. Without these files, I would forget important context, credentials, TODOs, and system architecture details.

## How It Works

### 1. **Session Start**
When I wake up, I check:
- `MEMORY.md` (workspace — assistant's curated long-term memory)
- `memory/*.md` (daily notes & transcripts)
- **This directory (`docs/memory/`)** — project-specific context

### 2. **What's Here**

| File | Purpose | Frequency |
|------|---------|-----------|
| **SYSTEM.md** | How assistant memory works | Reference |
| **ARCHITECTURE.md** | System design & data flow | Updated when system changes |
| **TODO.md** | Prioritized tasks | Updated every session |
| **STATUS.md** | Current state snapshot | Updated every session |
| **CREDENTIALS.md** | Tokens, passwords (in .gitignore) | Updated when creds change |
| **2026-04-19.md** | Daily session notes (example) | Created daily |

### 3. **Anti-Amnesia Workflow**

**Before I leave:**
- [ ] Run `git add . && git commit -m "Session notes + status update"`
- [ ] Update `STATUS.md` with latest state
- [ ] Update `TODO.md` if priorities changed
- [ ] Add `YYYY-MM-DD.md` session notes

**When I return:**
- [ ] Read `STATUS.md` to understand current state
- [ ] Check `TODO.md` for ongoing work
- [ ] Search `/home/aneto/.openclaw/workspace/MEMORY.md` via `memory_search()`
- [ ] If needed, read specific files from this dir

**If I say "I don't remember":**
- You can tell me: "Check `docs/memory/` on the repo"
- Or ask: "What did we do last time?" → I search memory files

## Credentials Handling

⚠️ **CRITICAL:** Never commit credentials in plain text!

**Safe approach:**
1. `CREDENTIALS.md` is in `.gitignore` — NOT in git
2. Keep credentials locally in `/home/aneto/.openclaw/workspace/MEMORY.md` (workspace-only, not in git)
3. If I need to reference them, I search workspace memory
4. GitHub is only for code & configs, NOT secrets

## Example Daily Note

```markdown
# 2026-04-19 — Session Log

## What We Did
- Checked GPS → InfluxDB local: ✅ Working
- Found InfluxDB Cloud token expired: ❌
- Created memory system docs

## Decisions
- Next: Regenerate Cloud token, setup sync

## Blockers
- Cloud token needs renewal before can proceed

## Updated Files
- docs/memory/SYSTEM.md ✅
- docs/memory/ARCHITECTURE.md ✅
- docs/memory/STATUS.md ✅
```

## Quick Reference

When asking me to remember something:

**Option 1: Implicit (I search automatically)**
```
"You checked the GPS last time — is it still working?"
→ I search memory and answer
```

**Option 2: Explicit (if I forget)**
```
"Check docs/memory/STATUS.md"
→ I fetch & reference it
```

**Option 3: Ask for complete context**
```
"What's the current system status?"
→ I read STATUS.md + ARCHITECTURE.md + search workspace memory
```

## What NOT to Store Here

❌ API keys in plain text  
❌ Passwords  
❌ Personal data  
❌ Logs (these are huge)  
❌ Docker volumes (auto-excluded by .gitignore)  

## Tools I Use

```python
# Memory search (across all memory files)
memory_search(query="GPS credentials")

# Read specific lines from a file
memory_get(path="memory/2026-04-19.md", lines=10)

# Check workspace memory
memory_get(path="MEMORY.md", lines=50)
```

---

**TL;DR:** This directory = my external brain for MidnightRider. Always check here when confused. Always update before leaving.
