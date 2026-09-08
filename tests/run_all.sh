#!/bin/bash
set -e
BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

PASS=0; FAIL=0
echo "================================================="
echo " Midnight Rider — Full Test Suite"
echo "================================================="
echo ""

echo "[ Python — pytest ]"
if python3 -m pytest tests/ -v --tb=short -q 2>&1 | tail -50; then
    echo "✅ Python tests PASSED"
    ((PASS++))
else
    echo "❌ Python tests FAILED"
    ((FAIL++))
fi
echo ""

echo "================================================="
echo " Results: $PASS passed | $FAIL failed"
echo "================================================="
[ $FAIL -eq 0 ] && exit 0 || exit 1
