#!/bin/bash

################################################################################
#
#  🚀 MIDNIGHT RIDER — SYSTEM HEALTH CHECK
#
#  Diagnostic complet du système navigation J/30 avant la mise à la mer.
#  Teste tous les composants: services, capteurs, données, BDD.
#
#  Usage: ./check-system.sh [--quick | --full | --watch]
#
#  Version: 1.0
#  Date: 2026-04-25
#
################################################################################

set -e

# ====== CONFIGURATION ======

SK_URL="http://localhost:3000"
INFLUX_URL="http://localhost:8086"
GRAFANA_URL="http://localhost:3001"
TIMEOUT=5
SPINNER_CHARS="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
WARNING_CHECKS=0
FAILED_CHECKS=0

# ====== COLORS & FORMATTING ======

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ====== HELPER FUNCTIONS ======

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_check() {
    local name="$1"
    local status="$2"
    local detail="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    case "$status" in
        PASS)
            echo -e "${GREEN}✅${NC} $name"
            [ -n "$detail" ] && echo "   → $detail"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            ;;
        WARN)
            echo -e "${YELLOW}⚠️${NC}  $name"
            [ -n "$detail" ] && echo "   → $detail"
            WARNING_CHECKS=$((WARNING_CHECKS + 1))
            ;;
        FAIL)
            echo -e "${RED}❌${NC} $name"
            [ -n "$detail" ] && echo "   → $detail"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            ;;
    esac
}

spinner() {
    local pid=$1
    local i=0
    while kill -0 $pid 2>/dev/null; do
        printf "\r${SPINNER_CHARS:$((i % 10)):1} "
        i=$((i + 1))
        sleep 0.1
    done
    printf "\r"
}

# ====== CATEGORY 1: BASE SERVICES ======

check_base_services() {
    print_header "CATÉGORIE 1 — SERVICES DE BASE"
    
    # Signal K
    if systemctl is-active --quiet signalk; then
        print_check "Signal K (systemctl)" "PASS" "Active (running)"
    else
        print_check "Signal K (systemctl)" "FAIL" "Not running — run: systemctl start signalk"
    fi
    
    # Signal K API
    local sk_code=$(curl -s -o /dev/null -w "%{http_code}" "$SK_URL/signalk" 2>/dev/null || echo "000")
    if [ "$sk_code" = "200" ] || [ "$sk_code" = "404" ]; then
        print_check "Signal K API (port 3000)" "PASS" "Responding (HTTP $sk_code)"
    else
        print_check "Signal K API (port 3000)" "FAIL" "Not responding (HTTP $sk_code)"
    fi
    
    # InfluxDB
    local influx_code=$(curl -s -o /dev/null -w "%{http_code}" "$INFLUX_URL/api/v2/health" 2>/dev/null || echo "000")
    if [ "$influx_code" = "200" ]; then
        print_check "InfluxDB (port 8086)" "PASS" "Healthy (HTTP $influx_code)"
    elif [ "$influx_code" = "503" ]; then
        print_check "InfluxDB (port 8086)" "WARN" "Initializing (HTTP $influx_code)"
    else
        print_check "InfluxDB (port 8086)" "FAIL" "Not responding (HTTP $influx_code)"
    fi
    
    # Grafana
    local grafana_code=$(curl -s -o /dev/null -w "%{http_code}" "$GRAFANA_URL/api/health" 2>/dev/null || echo "000")
    if [ "$grafana_code" = "200" ]; then
        print_check "Grafana (port 3001)" "PASS" "Responsive (HTTP $grafana_code)"
    else
        print_check "Grafana (port 3001)" "FAIL" "Not responding (HTTP $grafana_code)"
    fi
    
    echo ""
}

# ====== CATEGORY 2: SENSORS ======

check_sensors() {
    print_header "CATÉGORIE 2 — CAPTEURS CONNECTÉS"
    
    # UM982 GPS
    if [ -c "/dev/ttyUSB0" ] || [ -L "/dev/gnss0" ]; then
        # Try to read a sentence
        local gps_read=$(timeout 2 cat /dev/ttyUSB0 2>/dev/null | head -1 || echo "")
        if echo "$gps_read" | grep -q "$"; then
            print_check "UM982 GPS (/dev/ttyUSB0)" "PASS" "Device accessible, sentence detected"
        else
            print_check "UM982 GPS (/dev/ttyUSB0)" "WARN" "Device accessible, awaiting data (cold start?)"
        fi
    else
        print_check "UM982 GPS (/dev/ttyUSB0)" "FAIL" "Device not found"
    fi
    
    # WIT IMU BLE
    if hciconfig hci0 2>/dev/null | grep -q "UP RUNNING"; then
        if pgrep -f "bleak_wit|signalk-wit" > /dev/null 2>&1; then
            print_check "WIT IMU BLE (hci0)" "PASS" "Adapter up, driver running"
        else
            print_check "WIT IMU BLE (hci0)" "WARN" "Adapter up, driver not active (start manually?)"
        fi
    else
        print_check "WIT IMU BLE (hci0)" "FAIL" "BLE adapter not up"
    fi
    
    # YDNU-02 Gateway
    if lsusb 2>/dev/null | grep -qi "yacht\|ydnu\|cp210\|ftdi"; then
        print_check "YDNU-02 Gateway (USB)" "PASS" "Device detected in lsusb"
    else
        print_check "YDNU-02 Gateway (USB)" "WARN" "Not in lsusb (may be disconnected or not enumerated)"
    fi
    
    echo ""
}

# ====== CATEGORY 3: SIGNAL K DATA ======

check_signalk_data() {
    print_header "CATÉGORIE 3 — DONNÉES SIGNAL K"
    
    local sk_data=$(curl -s "$SK_URL/signalk/v1/api/vessels/self" 2>/dev/null || echo "{}")
    
    # Position
    local pos=$(echo "$sk_data" | grep -o '"latitude"' 2>/dev/null || echo "")
    if [ -n "$pos" ]; then
        print_check "Position GPS" "PASS" "Data in Signal K"
    else
        print_check "Position GPS" "WARN" "Not yet in Signal K (cold start or no GPS lock)"
    fi
    
    # Heading
    local heading=$(echo "$sk_data" | grep -o '"headingTrue"' 2>/dev/null || echo "")
    if [ -n "$heading" ]; then
        print_check "Heading True (UM982)" "PASS" "Data in Signal K"
    else
        print_check "Heading True (UM982)" "WARN" "Not yet in Signal K"
    fi
    
    # Attitude
    local attitude=$(echo "$sk_data" | grep -o '"roll"' 2>/dev/null || echo "")
    if [ -n "$attitude" ]; then
        print_check "Attitude (roll/pitch/yaw)" "PASS" "Data in Signal K"
    else
        print_check "Attitude (roll/pitch/yaw)" "WARN" "Not yet in Signal K (WIT not connected?)"
    fi
    
    # Waves
    local waves=$(echo "$sk_data" | grep -o '"significantWaveHeight"' 2>/dev/null || echo "")
    if [ -n "$waves" ]; then
        print_check "Wave Height (Analyzer v1.1)" "PASS" "Data in Signal K"
    else
        print_check "Wave Height (Analyzer v1.1)" "WARN" "Not yet (needs 5+ min data collection)"
    fi
    
    echo ""
}

# ====== CATEGORY 4: INFLUXDB ======

check_influxdb() {
    print_header "CATÉGORIE 4 — INFLUXDB (ENREGISTREMENT)"
    
    # Check bucket
    local bucket_check=$(curl -s -H "Authorization: Bearer $(cat ~/.influxdb_token 2>/dev/null || echo '')" \
        "$INFLUX_URL/api/v2/buckets" 2>/dev/null | grep -q "midnight_rider" && echo "FOUND" || echo "NOT_FOUND")
    
    if [ "$bucket_check" = "FOUND" ]; then
        print_check "Bucket 'midnight_rider'" "PASS" "Exists and accessible"
    else
        print_check "Bucket 'midnight_rider'" "WARN" "Cannot verify (auth issue?)"
    fi
    
    # Check recent data
    local recent_log=$(journalctl -u signalk --since "5 min ago" 2>/dev/null | tail -5)
    if echo "$recent_log" | grep -qi "influx"; then
        print_check "InfluxDB writes (last 5 min)" "PASS" "Activity in logs"
    else
        print_check "InfluxDB writes (last 5 min)" "WARN" "No recent activity logged"
    fi
    
    echo ""
}

# ====== CATEGORY 5: DOCKER (OPTIONAL) ======

check_docker() {
    print_header "CATÉGORIE 5 — DOCKER SERVICES (OPTIONNEL)"
    
    if command -v docker &> /dev/null; then
        # Docker compose
        if docker compose ps 2>/dev/null | grep -q "influxdb"; then
            print_check "Docker Compose (influxdb)" "PASS" "Container running"
        else
            print_check "Docker Compose (influxdb)" "WARN" "Container not found or stopped"
        fi
        
        if docker compose ps 2>/dev/null | grep -q "grafana"; then
            print_check "Docker Compose (grafana)" "PASS" "Container running"
        else
            print_check "Docker Compose (grafana)" "WARN" "Container not found or stopped"
        fi
    else
        print_check "Docker installed" "WARN" "Docker not found (optional)"
    fi
    
    echo ""
}

# ====== SUMMARY ======

print_summary() {
    print_header "RÉSUMÉ"
    
    echo "Total checks:     $TOTAL_CHECKS"
    echo -e "${GREEN}✅ Passed:       $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}⚠️  Warnings:    $WARNING_CHECKS${NC}"
    echo -e "${RED}❌ Failed:       $FAILED_CHECKS${NC}"
    echo ""
    
    # GO / NO-GO Decision
    if [ $FAILED_CHECKS -eq 0 ] && [ $WARNING_CHECKS -le 2 ]; then
        echo -e "${GREEN}${BOLD}✅ GO FOR DEPLOYMENT${NC}"
        echo "System is ready for field testing or race deployment."
        echo ""
        return 0
    elif [ $FAILED_CHECKS -eq 0 ] && [ $WARNING_CHECKS -gt 2 ]; then
        echo -e "${YELLOW}${BOLD}⚠️  CAUTION PROCEED${NC}"
        echo "System mostly ready, but check warnings above."
        echo ""
        return 1
    else
        echo -e "${RED}${BOLD}❌ NO-GO${NC}"
        echo "Critical issues detected. Fix failures before deployment."
        echo ""
        return 2
    fi
}

# ====== MAIN ======

main() {
    local mode="${1:---full}"
    
    echo -e "${BOLD}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║        🚀 MIDNIGHT RIDER — SYSTEM HEALTH CHECK v1.0           ║"
    echo "║                                                                ║"
    echo "║        J/30 Navigation System Diagnostic                       ║"
    echo "║        Date: $(date '+%Y-%m-%d %H:%M:%S')                           ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    case "$mode" in
        --quick)
            check_base_services
            ;;
        --full)
            check_base_services
            check_sensors
            check_signalk_data
            check_influxdb
            check_docker
            ;;
        --watch)
            while true; do
                clear
                check_base_services
                check_sensors
                check_signalk_data
                echo "(Refreshing every 10 sec... Press Ctrl+C to exit)"
                sleep 10
            done
            ;;
        *)
            echo "Usage: ./check-system.sh [--quick | --full | --watch]"
            echo ""
            echo "  --quick   Test only base services (fast)"
            echo "  --full    Complete diagnostic (recommended)"
            echo "  --watch   Continuous monitoring every 10 sec"
            exit 1
            ;;
    esac
    
    print_summary
    local exit_code=$?
    
    echo "📝 Full logs: journalctl -u signalk -f"
    echo "📊 Dashboard: http://localhost:3001"
    echo "📡 Signal K API: http://localhost:3000/signalk"
    echo ""
    
    exit $exit_code
}

# Run
main "$@"
