#!/bin/bash
#
# Update WIT IMU Configuration
# Change calibration, filter, or update rate without restarting the service
#
# Usage:
#   ./update-wit-config.sh --calibZ 0.035 --filterAlpha 0.08 --restart
#   ./update-wit-config.sh --show
#

CALIB_FILE="/home/aneto/.signalk/wit-calibration.json"
PLUGIN_CONFIG="/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-reader.json"
RESTART=false

# Show current config
if [[ "$1" == "--show" ]] || [[ $# -eq 0 ]]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  WIT IMU Configuration                                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Calibration offsets (g):"
    cat "$CALIB_FILE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
calib = d.get('accel_offset', [0,0,0])
gyro = d.get('gyro_offset', [0,0,0])
angle = d.get('angle_offset', [0,0,0])
print(f'  Accel: X={calib[0]:.6f}  Y={calib[1]:.6f}  Z={calib[2]:.6f}')
print(f'  Gyro:  X={gyro[0]:.2f}°/s  Y={gyro[1]:.2f}°/s  Z={gyro[2]:.2f}°/s')
print(f'  Angle: Roll={angle[0]:.4f}°  Pitch={angle[1]:.4f}°  Yaw={angle[2]:.4f}°')
"
    echo ""
    echo "Plugin configuration:"
    cat "$PLUGIN_CONFIG" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  USB Port: {d.get(\"usbPort\")}')
print(f'  Baud Rate: {d.get(\"baudRate\")}')
print(f'  Filter Alpha: {d.get(\"filterAlpha\")}')
print(f'  Update Rate: {d.get(\"updateRate\")} Hz')
"
    echo ""
    exit 0
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --calibX)
            python3 << PYTHON
import json
with open('$CALIB_FILE', 'r') as f:
    d = json.load(f)
d['accel_offset'][0] = float('$2')
with open('$CALIB_FILE', 'w') as f:
    json.dump(d, f, indent=2)
print(f"✅ Accel X offset updated to {d['accel_offset'][0]}")
PYTHON
            shift 2
            RESTART=true
            ;;
        --calibY)
            python3 << PYTHON
import json
with open('$CALIB_FILE', 'r') as f:
    d = json.load(f)
d['accel_offset'][1] = float('$2')
with open('$CALIB_FILE', 'w') as f:
    json.dump(d, f, indent=2)
print(f"✅ Accel Y offset updated to {d['accel_offset'][1]}")
PYTHON
            shift 2
            RESTART=true
            ;;
        --calibZ)
            python3 << PYTHON
import json
with open('$CALIB_FILE', 'r') as f:
    d = json.load(f)
d['accel_offset'][2] = float('$2')
with open('$CALIB_FILE', 'w') as f:
    json.dump(d, f, indent=2)
print(f"✅ Accel Z offset updated to {d['accel_offset'][2]}")
PYTHON
            shift 2
            RESTART=true
            ;;
        --filterAlpha)
            python3 << PYTHON
import json
with open('$PLUGIN_CONFIG', 'r') as f:
    d = json.load(f)
d['filterAlpha'] = float('$2')
with open('$PLUGIN_CONFIG', 'w') as f:
    json.dump(d, f, indent=2)
print(f"✅ Filter alpha updated to {d['filterAlpha']}")
PYTHON
            shift 2
            RESTART=true
            ;;
        --updateRate)
            python3 << PYTHON
import json
with open('$PLUGIN_CONFIG', 'r') as f:
    d = json.load(f)
d['updateRate'] = float('$2')
with open('$PLUGIN_CONFIG', 'w') as f:
    json.dump(d, f, indent=2)
print(f"✅ Update rate changed to {d['updateRate']} Hz")
PYTHON
            shift 2
            RESTART=true
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--calibX VAL] [--calibY VAL] [--calibZ VAL] [--filterAlpha VAL] [--updateRate VAL] [--restart] [--show]"
            exit 1
            ;;
    esac
done

# Restart service if requested
if [[ "$RESTART" == true ]]; then
    echo ""
    echo "Restarting WIT IMU service..."
    sudo systemctl restart wit-usb-reader
    sleep 5
    echo "✅ Service restarted"
    echo ""
    echo "IMU Data:"
    curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude 2>/dev/null | python3 -c "
import sys, json, math
try:
    d = json.load(sys.stdin)
    r = d['roll']['value'] * 180 / math.pi
    p = d['pitch']['value'] * 180 / math.pi
    y = d['yaw']['value'] * 180 / math.pi
    print(f'  Roll:  {r:7.2f}°')
    print(f'  Pitch: {p:7.2f}°')
    print(f'  Yaw:   {y:7.2f}°')
except:
    print('  (IMU data not available yet)')
"
fi
