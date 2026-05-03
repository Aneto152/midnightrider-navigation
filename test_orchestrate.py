#!/usr/bin/env python3
from orchestrate import route_telegram

tests = [
    ('TASK ajouter lien GPS', 'init'),
    ('STATUS', 'status'),
    ('GO', 'go'),
    ('STOP', 'stop'),
    ('bonjour OC', 'passthrough'),
]

results = []
for msg, expected in tests:
    result = route_telegram(msg)
    ok = (result is None) == (expected == 'passthrough')
    status = '✅' if ok else '❌'
    results.append(ok)
    print(f'{status} [{expected}] "{msg[:30]}" → {"passthrough" if result is None else "response"}')

print(f"\nTests route_telegram(): {sum(results)}/5 ✅")
