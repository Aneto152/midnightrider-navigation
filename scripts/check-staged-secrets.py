#!/usr/bin/env python3
"""Refuse a commit that carries a credential.

Installed by H3b (incident SEC-2026-09-14-01), where an InfluxDB token was
published in this public repository by the 15-minute log auto-commit.

Usage
-----
    python3 scripts/check-staged-secrets.py              # scan the git index
    python3 scripts/check-staged-secrets.py --files a b  # scan given files
    python3 scripts/check-staged-secrets.py --self-test  # prove it still works

Exit code 0 = clean, 1 = a credential was found (or the self-test failed).

Design notes
------------
No secret value is ever printed: findings are reported as a rule name, a
position and a masked excerpt. A line carrying the pragma ``# noscan`` is
skipped, which is how this file describes its own test material without
tripping over itself.
"""

import math
import os
import re
import subprocess
import sys

MAX_BYTES = 4 * 1024 * 1024

# A credential assigned to an obviously credential-shaped name.
# No \b before the keyword on purpose: INFLUX_TOKEN= has a word character
# (the underscore) before "TOKEN", so \b would miss the single most likely
# shape of a leak in this repository. Caught during rehearsal.
ASSIGN = re.compile(
    r'(?i)(token|secret|password|passwd|api[_-]?key|apikey|credential|authorization)'
    r'["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-+/]{20,})')

# A long opaque run of characters: the shape of an InfluxDB token.
LONG = re.compile(r'[A-Za-z0-9_\-]{60,}={0,2}')

PEM = re.compile(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----')

# Lines that legitimately talk ABOUT secrets without carrying one.
EXEMPT_LINE = re.compile(
    r'(?i)(REDACTED|\[MASKED\]|sha256\[:16\]|fingerprint|\$\{|%\(|noscan|placeholder|example)')

HEXONLY = re.compile(r'(?i)\A[0-9a-f]+\Z')


def entropy(s):
    """Shannon entropy in bits per character."""
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = float(len(s))
    return -sum((c / n) * math.log(c / n, 2) for c in counts.values())


def looks_opaque(s):
    """True when a long run looks like a key rather than like text."""
    if HEXONLY.match(s):
        # 40 = git sha, 64 = sha256: those are public identifiers, not secrets.
        return len(s) not in (32, 40, 64)
    has_lower = any(c.islower() for c in s)
    has_upper = any(c.isupper() for c in s)
    has_digit = any(c.isdigit() for c in s)
    if not (has_lower and has_upper and has_digit):
        return False
    return entropy(s) >= 3.6


def mask(s):
    if len(s) <= 8:
        return '*' * len(s)
    return '%s...%s (%d chars)' % (s[:3], s[-2:], len(s))


def scan_text(path, body):
    findings = []
    for lineno, line in enumerate(body.split('\n'), 1):
        if len(line) > 20000:
            line = line[:20000]
        if EXEMPT_LINE.search(line):
            continue
        if PEM.search(line):
            findings.append((path, lineno, 'PRIVATE_KEY', '-----BEGIN ... PRIVATE KEY-----'))
            continue
        m = ASSIGN.search(line)
        if m:
            findings.append((path, lineno, 'ASSIGNED_CREDENTIAL',
                             '%s = %s' % (m.group(1), mask(m.group(2)))))
            continue
        for run in LONG.findall(line):
            run = run.rstrip('=')
            if looks_opaque(run):
                findings.append((path, lineno, 'OPAQUE_LONG_STRING', mask(run)))
                break
    return findings


def scan_files(paths):
    findings, scanned = [], 0
    for path in paths:
        if not path or not os.path.isfile(path):
            continue
        try:
            if os.path.getsize(path) > MAX_BYTES:
                print('  skipped (too large): %s' % path)
                continue
            with open(path, 'rb') as fh:
                blob = fh.read()
            if b'\0' in blob[:4096]:
                print('  skipped (binary): %s' % path)
                continue
            body = blob.decode('utf-8', 'replace')
        except Exception as exc:                        # pragma: no cover
            print('  unreadable, treated as suspect: %s (%s)' % (path, exc))
            findings.append((path, 0, 'UNREADABLE', str(exc)[:60]))
            continue
        scanned += 1
        findings.extend(scan_text(path, body))
    return findings, scanned


def staged_files():
    out = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True, text=True)
    return [p for p in out.stdout.split('\n') if p.strip()]


def self_test():
    """Prove the two things that matter: it catches, and it does not cry wolf."""
    # Built by concatenation so that this file contains no literal long key.
    fake_token = ('Ab3' + 'xY7qZ2mK9pL4wD8s') * 5                      # noscan
    must_flag = [                                                      # noscan
        ('influx token in a log line', 'level=info token=%s' % fake_token),  # noscan
        ('assignment', 'INFLUX_TOKEN=%s' % ('Qw3rTy' * 5)),            # noscan
        ('password', 'password: %s' % ('a1B2c3D4' * 4)),               # noscan
        ('private key', '-----BEGIN ' + 'RSA PRIVATE KEY-----'),       # noscan
    ]
    must_pass = [
        ('fingerprint', 'sha256[:16]=e80a47801529a25c'),
        ('git sha', 'commit 860120398157b59551fd49191c62bcd5bba0d61c landed'),
        ('prose', 'the token was deactivated, not deleted, and that is fine'),
        ('env reference', 'token: ${INFLUX_TOKEN}'),
        ('masked', 'Authorization: Token [MASKED]'),
        ('redacted', '[REDACTED - credential reference: influx-exposed-token]'),
        ('flux query', 'from(bucket: "midnight_rider") |> range(start: -3h)'),
    ]
    ok = True
    for label, sample in must_flag:
        if not scan_text('<self-test>', sample):
            print('  SELF-TEST FAIL: missed %s' % label)
            ok = False
    for label, sample in must_pass:
        found = scan_text('<self-test>', sample)
        if found:
            print('  SELF-TEST FAIL: false positive on %s -> %s' % (label, found[0][2]))
            ok = False
    print('  self-test: %s (%d must-flag, %d must-pass)'
          % ('PASS' if ok else 'FAIL', len(must_flag), len(must_pass)))
    return 0 if ok else 1


def main(argv):
    if '--self-test' in argv:
        return self_test()
    if '--files' in argv:
        paths = argv[argv.index('--files') + 1:]
    else:
        paths = staged_files()
    findings, scanned = scan_files(paths)
    if not findings:
        print('  secret barrier: CLEAN (%d file(s) scanned)' % scanned)
        return 0
    print('  secret barrier: BLOCKED (%d finding(s) in %d file(s) scanned)'
          % (len(findings), scanned))
    for path, lineno, rule, excerpt in findings[:40]:
        print('    %s:%s  [%s]  %s' % (path, lineno, rule, excerpt))
    print('  Nothing was committed. Remove or redact the value, then retry.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
