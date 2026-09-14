#!/usr/bin/env python3
"""Repository-wide static guards.

Rationale (2026-09-14). Six production defects shipped in a single day on the
Fleet page and none of them was visible to the existing test suite:

1. regatta/server.py committed with an IndentationError -> production HTTP 502.
2. tests/portal/test_portal.py and tests/mcp/test_mcp.py committed with a
   SyntaxError in d6a3107, silently breaking pytest collection repo-wide.
3. ais/fleet_db.html and ais/fleet_stars.js both declared a global
   `const STORAGE_KEY` -> SyntaxError annulling an entire script block.
4. fleet_db.html called saveStarred(), a function defined nowhere - and a test
   actively asserted the presence of that call.
5. showModal() never called populateRaceHistory(), leaving the race history
   section permanently hidden since de8d682.

Every guard below is static, runs in about a second, and would have caught one
of these. They are deliberately strict: a legitimate exception must be argued
in review, not silently tolerated.
"""
import ast
import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', '.pytest_cache'}

FLEET_HTML = REPO_ROOT / 'ais' / 'fleet_db.html'
FLEET_JS = REPO_ROOT / 'ais' / 'fleet_stars.js'

GLOBAL_DECL_RE = re.compile(r'^(?:const|let|var)\s+([A-Za-z_$][\w$]*)', re.MULTILINE)
FUNCTION_DECL_RE = re.compile(r'^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)', re.MULTILINE)
INLINE_HANDLER_RE = re.compile(
    r'on(?:click|dblclick|change|input|submit|keyup)="\s*([A-Za-z_$][\w$]*)\s*\('
)


def iter_python_files():
    """Yield every tracked-looking Python source file in the repository."""
    for path in sorted(REPO_ROOT.rglob('*.py')):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue
        yield path


class TestRepositoryPythonSyntax(unittest.TestCase):
    """Guard 1 - every Python file in the repository must compile."""

    def test_every_python_file_parses(self):
        scanned = 0
        failures = []
        for path in iter_python_files():
            scanned += 1
            source = path.read_text(encoding='utf-8', errors='replace')
            try:
                ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                failures.append(
                    '{}:{} -> {}'.format(path.relative_to(REPO_ROOT), exc.lineno, exc.msg)
                )
        self.assertGreater(scanned, 50, 'sanity check: the whole repository should be scanned')
        self.assertEqual(
            failures, [],
            'Python files that do not compile:\n' + '\n'.join(failures)
        )


class TestFleetFrontendStaticGuards(unittest.TestCase):
    """Guards 2 to 4 - the Fleet frontend spans an HTML page and an external
    script that share one global scope. Collisions there are fatal at parse
    time and invisible to string-matching tests."""

    @classmethod
    def setUpClass(cls):
        cls.html = FLEET_HTML.read_text(encoding='utf-8')
        cls.js = FLEET_JS.read_text(encoding='utf-8')
        cls.html_globals = set(GLOBAL_DECL_RE.findall(cls.html))
        cls.js_globals = set(GLOBAL_DECL_RE.findall(cls.js))
        cls.html_functions = set(FUNCTION_DECL_RE.findall(cls.html))
        cls.js_functions = set(FUNCTION_DECL_RE.findall(cls.js))

    def test_no_duplicate_global_declaration(self):
        """A `const` declared in both files throws SyntaxError and kills a whole
        script block. This is exactly what STORAGE_KEY did."""
        clash = sorted(self.html_globals & self.js_globals)
        self.assertEqual(
            clash, [],
            'Global identifiers declared in BOTH fleet_db.html and '
            'fleet_stars.js (fatal at parse time): {}'.format(clash)
        )

    def test_no_function_declared_in_both_files(self):
        """Two definitions of the same function: the last parsed wins, silently,
        even with incompatible signatures. This is what toggleFleetStar did."""
        clash = sorted(self.html_functions & self.js_functions)
        self.assertEqual(
            clash, [],
            'Functions defined in both files: {}'.format(clash)
        )

    def test_inline_event_handlers_are_defined(self):
        """Every onclick/ondblclick target must exist somewhere."""
        handlers = set(INLINE_HANDLER_RE.findall(self.html))
        defined = self.html_functions | self.js_functions
        missing = sorted(handlers - defined)
        self.assertEqual(
            missing, [],
            'Inline handlers referencing undefined functions: {}'.format(missing)
        )

    def test_no_unreferenced_function(self):
        """A function that is never called is either dead code or a wiring bug.
        populateRaceHistory() was the second case and hid a whole feature."""
        combined = self.html + self.js
        dead = []
        for name in sorted(self.html_functions | self.js_functions):
            calls = len(re.findall(r'\b' + re.escape(name) + r'\s*\(', combined))
            as_callback = len(re.findall(r'[(,]\s*' + re.escape(name) + r'\s*[),]', combined))
            if calls <= 1 and as_callback == 0:
                dead.append(name)
        self.assertEqual(
            dead, [],
            'Functions defined but never referenced (dead code or missing '
            'wiring): {}'.format(dead)
        )


if __name__ == '__main__':
    unittest.main()
