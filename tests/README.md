# Test Suite — `tests/`

Mirror structure — tests/ mirrors root module layout.

## Structure

```
tests/
├── conftest.py              ← Shared fixtures + PYTHONPATH
├── pytest.ini               ← pytest config
├── run_all.sh               ← Run all tests
├── README.md                ← This file
├── ais/                     ← mirrors ais/
│   ├── test_lib.py          (34 tests)
│   ├── test_html.py         (35 tests)
│   ├── test_competitors_db.py (23 tests)
│   └── test_server_handlers.py (18 tests)
├── mcp/                     ← mirrors mcp/
│   ├── test_mcp.py          (18 tests)
│   └── js/                  (JS protocol tests)
├── plugins/                 ← mirrors plugins/
│   └── plugins.test.js      (27 Jest tests)
└── portal/                  ← mirrors portal/
    └── test_portal.py       (33 tests)
```

## Running Tests

```bash
# All tests
bash tests/run_all.sh

# Python only
python3 -m pytest tests/ -v

# By module
python3 -m pytest tests/ais/
python3 -m pytest tests/portal/
python3 -m pytest tests/mcp/
```

## Test Counts

| Directory | Tests | Framework |
|-----------|-------|-----------|
| tests/ais/ | 110 | pytest |
| tests/portal/ | 33 | pytest |
| tests/mcp/ | 18 | pytest |
| tests/plugins/ | 27 | Jest |
| **Total** | **188** | — |

*Midnight Rider — J/30 — Larchmont Yacht Club*
