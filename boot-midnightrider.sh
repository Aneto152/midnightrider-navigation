#!/bin/bash
#
# MidnightRider Boot Sequence
# Ensures proper startup order: Kplex → Docker → Signal K Provider Plugins
#
# 2026-04-22
#

set -e

LOG="/var/log/midnightrider-boot.log"
exec 1>>"$LOG" 2>&1

echo "═══════════════════════════════════════════════════════════════"
echo "MidnightRider Boot Sequence - $(date)"
echo "═══════════════════════════════════════════════════════════════"

# Phase 1: Start Kplex (takes USB exclusively)
echo ""
echo "Phase 1️⃣  Starting Kplex (NMEA router)..."
if systemctl start kplex; then
    echo "✅ Kplex started"
    sleep 2
    
    # Verify port 10110 listening
    if netstat -tlnp 2>/dev/null | grep -q ":10110 "; then
        echo "✅ Kplex listening on port 10110"
    else
        echo "⚠️  Kplex not listening yet, waiting..."
        sleep 3
    fi
else
    echo "❌ Failed to start Kplex"
    exit 1
fi

# Phase 2: Start Docker services (includes Signal K)
echo ""
echo "Phase 2️⃣  Starting Docker services..."
cd /home/aneto/docker/signalk

if docker-compose up -d; then
    echo "✅ Docker services started"
    sleep 5
else
    echo "❌ Failed to start Docker services"
    exit 1
fi

# Phase 3: Wait for Signal K to be ready
echo ""
echo "Phase 3️⃣  Waiting for Signal K API..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:3000/skServer/plugins > /dev/null 2>&1; then
        echo "✅ Signal K API ready"
        break
    fi
    echo "⏳ Waiting for Signal K ($WAITED/$MAX_WAIT sec)..."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "⚠️  Signal K took too long, continuing anyway"
fi

# Phase 4: Verify data flow
echo ""
echo "Phase 4️⃣  Verifying data flow..."
sleep 2

# Check Kplex
if lsof /dev/ttyUSB0 2>/dev/null | grep -q kplex; then
    echo "✅ Kplex holding /dev/ttyUSB0"
else
    echo "⚠️  Kplex not found on USB"
fi

# Check Signal K
if curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude > /dev/null 2>&1; then
    echo "✅ Signal K API responding"
else
    echo "⚠️  Signal K API not responding yet"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ MidnightRider Boot Complete - $(date)"
echo "═══════════════════════════════════════════════════════════════"

exit 0
