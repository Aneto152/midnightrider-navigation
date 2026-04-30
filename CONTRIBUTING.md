# Contributing to Midnight Rider 🌊

Thank you for interest in contributing! This is an open-source marine instrumentation project, and contributions are welcome.

## Guidelines

### Before You Start

1. **Check existing issues** — avoid duplicates
2. **Fork the repo** on GitHub
3. **Create a feature branch** — use a descriptive name
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Code Standards

- **Never commit credentials** — use `.env.example` as a template
- Follow **PEP 8** for Python code
- Add **docstrings** to functions
- Test your changes locally before pushing
- Write clear **commit messages**

### JSON File Modifications — Python Only

⚠️ **ABSOLUTE RULE: Never use `sed`, `awk`, `grep`, or text manipulation for JSON files.**

Always use **Python** with `scripts/json_utils.py` or equivalent validation. Why?
- Python validates JSON structure before and after modification
- Prevents silent corruption from special characters or encoding issues
- Script fails loudly rather than corrupting files
- Automatic backups protect against mistakes

**Usage:**
```bash
# Validate JSON syntax
python3 scripts/json_utils.py validate grafana-dashboards/cockpit.json

# Get a value (dot notation)
python3 scripts/json_utils.py get grafana-dashboards/cockpit.json title

# Set a value
python3 scripts/json_utils.py set grafana-dashboards/cockpit.json title "NEW TITLE"

# Delete a key
python3 scripts/json_utils.py delete config.json temp_key

# Count items in array
python3 scripts/json_utils.py count grafana-dashboards/cockpit.json panels

# Pretty-print (format)
python3 scripts/json_utils.py pretty grafana-dashboards/cockpit.json

# Apply patch file
python3 scripts/json_utils.py patch config.json patch.json

# Show file info
python3 scripts/json_utils.py info grafana-dashboards/cockpit.json
```

**For custom Python scripts:**
```python
import json

# ❌ WRONG: Never use sed/shell commands
os.system("sed -i 's/old/new/g' file.json")  # DANGER!

# ✅ CORRECT: Load, modify, validate, save
with open("file.json") as f:
    data = json.load(f)  # Validates JSON on load

data["key"] = "new_value"

with open("file.json", "w") as f:
    json.dump(data, f, indent=2)  # Validates format on write
```

See `scripts/json_utils.py` for complete utility with automatic backups.

### Security and Dashboard Integrity

Grafana dashboards and other JSON configs are fragile. **Corrupted JSON = broken dashboards = race day failures.**

**Before modifying any JSON:**
1. **Always validate first**: `python3 scripts/json_utils.py validate file.json`
2. **Use Python**: Never shell commands on JSON
3. **Test locally**: Verify dashboards load correctly in Grafana
4. **Commit separately**: Don't mix JSON changes with code changes

### Security

- **No hardcoded tokens, passwords, or API keys** in code or config files
- Use `.env.local` (which is gitignored) for local credentials
- **Never use text tools (sed/awk) on JSON** — they corrupt the files
- If you discover a security issue, please report it privately to the maintainers

### Testing

Before submitting a PR:
1. Test your changes locally
2. Run `pytest` if tests exist
3. Verify no errors in logs

### Pull Request Process

1. Update documentation if you change functionality
2. Reference any related issues (`Fixes #123`)
3. Provide a clear description of changes
4. Submit PR against `main` branch

### Documentation

- Update relevant markdown files in `docs/`
- Keep `README.md` in sync with major changes
- Document hardware connections and configuration steps

## Questions?

Open an issue on GitHub and describe your question. We're here to help!

---

**Thank you for helping make Midnight Rider better!** ⛵
