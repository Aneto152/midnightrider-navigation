#!/usr/bin/env python3
"""Refuse a commit that carries a credential.

Installed by H3b (incident SEC-2026-09-14-01), where an InfluxDB token was
published in this public repository by the 15-minute log auto-commit.
Hardened by H3f (2026-09-16) after the v1 scanner walked straight past a
published Grafana password and a published WiFi passphrase: its keyword list
was English-only and it only looked at assigned values of 20 characters or
more, while a human password is short and its label is often French.

Usage
-----
    python3 scripts/check-staged-secrets.py              # scan the git index
    python3 scripts/check-staged-secrets.py --files a b  # scan given files
    python3 scripts/check-staged-secrets.py --audit     # scan the whole tracked tree
    python3 scripts/check-staged-secrets.py --self-test  # prove it still works

Exit code 0 = clean, 1 = a credential was found (or the self-test failed).

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
# before "TOKEN", which is the single most likely shape of a leak here.
ASSIGN = re.compile(
    r'(?i)(token|secret|password|passwd|api[_-]?key|apikey|credential|authorization)'
    r'["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-+/]{20,})')

# A long opaque run of characters: the shape of an InfluxDB token.
LONG = re.compile(r'[A-Za-z0-9_\-]{60,}={0,2}')

PEM = re.compile(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----')

# Un identifiant passe en ARGUMENT de ligne de commande. La version 2
# exigeait ':' '=' ou '|' apres l'etiquette et laissait donc passer
#   wifi-sec.psk "..."
# qui est exactement la forme sous laquelle la passphrase WiFi est restee
# publiee apres H3f (defaut 28). Seules les valeurs entre guillemets sont
# examinees, et le discriminant habituel s'applique ensuite.
CLI_CREDENTIAL = re.compile(
    r'(?i)(wifi-sec\.psk|wifi\.psk|wireless-security\.psk|--password|'
    r'--passwd|--api-key|--apikey|--token|--secret|--psk)'
    r'\s+(["\'])([^"\']{4,80})\2')


# A short human credential behind a label, in any of the shapes this
# repository actually uses: a markdown table row, a "key: value" line, a
# French label. This is what v1 was missing.
LABEL = (r'(?:mots?\s*de\s*passe|motdepasse|passphrase|password|passwd|login|'
         r'identifiant|credential|secret|token|api[_-]?key|apikey|mdp|pwd|psk|'
         r'wpa[_-]?key|admin\s*pass)')
LABEL_VALUE = re.compile(r'(?i)' + LABEL + r'\s*[:=|]\s*(`[^`]{3,80}`|[^\s|,;]{3,80})')

# Lines that legitimately talk ABOUT credentials without carrying one.
EXEMPT_LINE = re.compile(
    r'(?i)(REDACTED|\[MASKED|MASKED_|sha256\[:16\]|fingerprint|empreinte|\$\{|%\(|'
    r'noscan|placeholder|example|changeme|your[-_]|<[a-z_-]+>|xxx)')

# Values that are not credentials even behind a credential label.
EXEMPT_VALUE = re.compile(
    r'(?i)\A(none|null|n/?a|aucun|voir|see|\.env|env|true|false|yes|no|oui|non|'
    r'https?://.*|/.*|-+|—|\*+|\.\.\.|'
    # a reference to a variable is not a value: this is what well-behaved code
    # looks like, and flagging it would train everybody to ignore the barrier
    r'(process\.env.*|os\.environ.*|os\.getenv.*|getenv.*|config\..*|self\..*|'
    r'this\..*|\$.*|%.*|\{\{.*|<.*>|'
    # a version number is not a credential (| jsonwebtoken | 9.0.3 |)
    r'v?\d+(\.\d+)+.*|'
    # a code expression is not a literal: token = auths[0].get("token")
    r'.*[\(\[].*))\Z')

# Obvious teaching placeholders found in this repository's own documentation.
EXEMPT_PLACEHOLDER = re.compile(
    r'(?i)(super[-_]secret|my[-_]token|token[-_]here|votre[-_]|ton[-_]token|dummy|'
    r'sample|test[-_]token|replace[-_]with|abc123|abcdef|abcxyz|mytoken|foo|bar|baz|'
    r'1234|password123|secret123|s3cr3t|tok123|fake)')

# Paths whose content is fake by convention, or machine-generated. Skipped by
# --audit so that a repository-wide report stays readable; the barrier itself
# only ever sees the paths the log timer stages.
AUDIT_SKIP = re.compile(r'(?i)(package-lock\.json|[^/]*\.lock|\Atests?/|/tests?/|'
                        r'\Anode_modules/|/node_modules/|\.min\.(js|css)\Z)')

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
        # 32/40/64 hex = md5 / git sha / sha256: public identifiers.
        return len(s) not in (32, 40, 64)
    has_lower = any(c.islower() for c in s)
    has_upper = any(c.isupper() for c in s)
    has_digit = any(c.isdigit() for c in s)
    if not (has_lower and has_upper and has_digit):
        return False
    return entropy(s) >= 3.6


def looks_like_password(word):
    """True for a short human credential behind a credential label.

    The discriminator, tuned against the 408 files of this repository: a
    credential carries a digit, or an uppercase letter INSIDE the word
    (CamelCaseWord), which ordinary prose does not (Empreinte, Identifiant).
    A leading capital alone is just a sentence starting.
    """
    word = word.strip().strip('`"\'')
    if len(word) < 4 or len(word) > 80:
        return False
    if EXEMPT_VALUE.match(word) or EXEMPT_PLACEHOLDER.search(word):
        return False
    if re.match(r'(?i)\A(admin|root|user|pi|aneto|grafana|influx|signalk|bearer)\Z', word):
        return False          # a user name alone is not a credential
    if HEXONLY.match(word) and len(word) in (8, 16, 32, 40, 64):
        return False          # an identifier, not a secret
    has_digit = any(c.isdigit() for c in word)
    internal_upper = any(c.isupper() for c in word[1:]) and any(c.islower() for c in word)
    return has_digit or internal_upper


def mask(s):
    if len(s) <= 8:
        return '%s%s (%d chars)' % (s[:1], '*' * (len(s) - 1), len(s))
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
        cm = CLI_CREDENTIAL.search(line)
        if cm and looks_like_password(cm.group(3)):
            findings.append((path, lineno, 'CLI_CREDENTIAL', mask(cm.group(3))))
            continue
        m = ASSIGN.search(line)
        if m and EXEMPT_PLACEHOLDER.search(m.group(2)):
            m = None
        if m:
            findings.append((path, lineno, 'ASSIGNED_CREDENTIAL',
                             '%s = %s' % (m.group(1), mask(m.group(2)))))
            continue
        hit = None
        for lv in LABEL_VALUE.finditer(line):
            value = lv.group(1)
            parts = re.split(r'[/,\s]+', value.strip('`')) if value.startswith('`') else [value]
            for part in parts:
                if looks_like_password(part):
                    hit = (path, lineno, 'LABELLED_CREDENTIAL', mask(part.strip('`"\'')))
                    break
            if hit:
                break
        if hit:
            findings.append(hit)
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


def tracked_files():
    """Every file git tracks: what a repository-wide audit must actually read."""
    out = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
    return [p for p in out.stdout.split('\n') if p.strip()]


def staged_files():
    out = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True, text=True)
    return [p for p in out.stdout.split('\n') if p.strip()]


def self_test():
    """Prove the two things that matter: it catches, and it does not cry wolf."""
    fake_token = ('Ab3' + 'xY7qZ2mK9pL4wD8s') * 5                      # noscan
    must_flag = [                                                      # noscan
        ('influx token in a log line', 'level=info token=%s' % fake_token),  # noscan
        ('assignment', 'INFLUX_TOKEN=%s' % ('Qw3rTy' * 5)),            # noscan
        ('password assignment', 'password: %s' % ('a1B2c3D4' * 4)),    # noscan
        ('private key', '-----BEGIN ' + 'RSA PRIVATE KEY-----'),       # noscan
        # The two real leaks that walked past the v1 scanner, in the exact
        # shape they had in docs/guides/RESTORE.md.
        # Valeurs volontairement absurdes : un echantillon d autotest ne doit
        # JAMAIS ressembler a un vrai identifiant du systeme. Defaut 27 : la
        # premiere version de cet autotest contenait la vraie passphrase WiFi,
        # ce qui l aurait republiee dans le depot. Le garde-fou de H3f l a
        # attrapee en repetition.
        ('login table row', '| Grafana login | `admin / Qx7ZzWpbTrap` |'),          # noscan
        ('passphrase, French label', '| WiFi AP | SSID: `Boat` / MDP: `Zz9KmqTrap` |'),  # noscan
        ('short password, key: value', 'GF_SECURITY_ADMIN_PASSWORD: Vv8RhtTrap'),    # noscan
        # La forme restee publiee apres H3f. Valeur volontairement absurde :
        # un echantillon d autotest ne doit jamais ressembler a un vrai
        # identifiant du systeme (defaut 27).
        ('nmcli psk argument',
         'wifi-sec.key-mgmt wpa-psk wifi-sec.psk "Kk4TrapZz" \\'),           # noscan

    ]
    must_pass = [
        ('fingerprint', 'sha256[:16]=e80a47801529a25c'),
        ('git sha', 'commit 860120398157b59551fd49191c62bcd5bba0d61c landed'),
        ('prose', 'the token was deactivated, not deleted, and that is fine'),
        ('prose about passwords', 'the admin password must be changed at some point'),
        ('env reference', 'token: ${INFLUX_TOKEN}'),
        ('masked', 'Authorization: Token [MASKED]'),
        ('redacted', '[REDACTED - credential reference: influx-exposed-token]'),
        ('redacted table row', '| Grafana login | `admin / [REDACTED - see .env]` |'),
        ('already masked token row', '| InfluxDB local token | `[MASKED_INFLUX_TOKEN]` |'),
        ('url row', '| Grafana Cloud | https://example.grafana.net |'),
        ('login url', 'the login page is at http://boat.local:3001'),
        ('flux query', 'from(bucket: "midnight_rider") |> range(start: -3h)'),
        ('user name only', '| Grafana login | `admin` |'),
        ('env var reference row', '| password | ${GF_SECURITY_ADMIN_PASSWORD} |'),
        ('nmcli psk via variable',
         'wifi-sec.psk "$WIFI_AP_PASSPHRASE" \\'),
        ('nmcli key management only', 'wifi-sec.key-mgmt wpa-psk \\'),

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
    audit = '--audit' in argv
    if '--files' in argv:
        paths = argv[argv.index('--files') + 1:]
    elif audit:
        # DEFAUT 33 : --audit sans --files n examinait que l index, donc un
        # audit du depot entier ne regardait rien. Un audit porte desormais
        # sur tous les fichiers suivis par git.
        paths = tracked_files()
    else:
        paths = staged_files()
    if audit:
        skipped = [p for p in paths if AUDIT_SKIP.search(p)]
        paths = [p for p in paths if not AUDIT_SKIP.search(p)]
        print('  audit mode: %d path(s) skipped as generated or test fixtures'
              % len(skipped))
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
