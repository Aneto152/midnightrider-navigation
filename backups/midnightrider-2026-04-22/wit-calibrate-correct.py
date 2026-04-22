#!/usr/bin/env python3
"""
WIT Calibration - CORRECT
Offset doit être tel que: brut - offset = 1 g (gravité)
"""

import serial
import time
import sys
import json
import os

CALIBRATION_FILE = '/home/aneto/.signalk/wit-calibration.json'
USB_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
CALIBRATION_SAMPLES = 300

print("╔════════════════════════════════════════════════════════════╗")
print("║  WIT IMU Calibration - CORRECT                            ║")
print("║  Offset doit donner: brut - offset = 1g (pas 9.81g!)      ║")
print("║  Starting in 3 seconds...                                  ║")
print("╚════════════════════════════════════════════════════════════╝")
print()

time.sleep(3)

accel_samples = [[], [], []]
gyro_samples = [[], [], []]
angle_samples = [[], [], []]

def decode_wit(data):
    if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
        return None

    def read16(off):
        v = (data[off+1] << 8) | data[off]
        return v - 0x10000 if v & 0x8000 else v

    accel_x = (read16(2) / 32768) * 16
    accel_y = (read16(4) / 32768) * 16
    accel_z = (read16(6) / 32768) * 16

    gyro_x = (read16(8) / 32768) * 2000
    gyro_y = (read16(10) / 32768) * 2000
    gyro_z = (read16(12) / 32768) * 2000

    roll = (read16(14) / 32768) * 180
    pitch = (read16(16) / 32768) * 180
    yaw = (read16(18) / 32768) * 180

    return {
        'accel': [accel_x, accel_y, accel_z],
        'gyro': [gyro_x, gyro_y, gyro_z],
        'angle': [roll, pitch, yaw]
    }

try:
    print(f"Collecting {CALIBRATION_SAMPLES} samples ({CALIBRATION_SAMPLES/30:.1f}s)...\n")
    
    port = serial.Serial(USB_PORT, BAUD_RATE, timeout=1)
    buffer = b''
    sample_count = 0

    while sample_count < CALIBRATION_SAMPLES:
        chunk = port.read(512)
        if not chunk:
            continue

        buffer += chunk

        while len(buffer) >= 20:
            if buffer[0] == 0x55 and buffer[1] == 0x61:
                packet = buffer[:20]
                buffer = buffer[20:]

                decoded = decode_wit(packet)
                if decoded:
                    for i in range(3):
                        accel_samples[i].append(decoded['accel'][i])
                        gyro_samples[i].append(decoded['gyro'][i])
                        angle_samples[i].append(decoded['angle'][i])

                    sample_count += 1
                    if sample_count % 50 == 0:
                        print(f"  [{sample_count:3d}/{CALIBRATION_SAMPLES}]")
            else:
                buffer = buffer[1:]

    port.close()

    print("\nCalculating offsets...\n")
    print("LOGIQUE CORRECTE:")
    print("  Offset = Brut - Résultat_attendu")
    print("  Si IMU horizontal: résultat attendu = 1g (ou 0, 0, 1 pour XYZ)")
    print()

    calibration = {
        'accel_offset': [0, 0, 0],
        'gyro_offset': [0, 0, 0],
        'angle_offset': [0, 0, 0],
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'samples': CALIBRATION_SAMPLES,
        'constraints': {
            'roll': 0,
            'pitch': 0,
            'yaw': 0,
            'accel_x': 0,
            'accel_y': 0,
            'accel_z': 1
        }
    }

    for i in range(3):
        accel_avg = sum(accel_samples[i]) / len(accel_samples[i])
        gyro_avg = sum(gyro_samples[i]) / len(gyro_samples[i])
        angle_avg = sum(angle_samples[i]) / len(angle_samples[i])

        axis_name = ['X', 'Y', 'Z'][i]

        # Offset = Brut - Attendu
        # Pour X,Y: attendu = 0
        # Pour Z: attendu = 1 (gravité)
        if i == 2:  # Z axis
            accel_expected = 1.0
        else:
            accel_expected = 0.0

        accel_offset = accel_avg - accel_expected

        calibration['accel_offset'][i] = accel_offset
        calibration['gyro_offset'][i] = gyro_avg
        calibration['angle_offset'][i] = angle_avg

        print(f"Axis {axis_name}:")
        print(f"  Accel brut:    {accel_avg:.4f}g")
        print(f"  Attendu:       {accel_expected:.4f}g")
        print(f"  → Offset:      {accel_offset:.4f}g")
        print()

    # Save
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(calibration, f, indent=2)

    print(f"✅ Calibration saved to {CALIBRATION_FILE}")
    print()
    print("Vérification:")
    print("  Après calibration:")
    print(f"    X: {accel_samples[0][0]:.4f}g - {calibration['accel_offset'][0]:.4f} = {accel_samples[0][0] - calibration['accel_offset'][0]:.4f}g (attendu 0)")
    print(f"    Y: {accel_samples[1][0]:.4f}g - {calibration['accel_offset'][1]:.4f} = {accel_samples[1][0] - calibration['accel_offset'][1]:.4f}g (attendu 0)")
    print(f"    Z: {accel_samples[2][0]:.4f}g - {calibration['accel_offset'][2]:.4f} = {accel_samples[2][0] - calibration['accel_offset'][2]:.4f}g (attendu 1)")
    print()
    print("Ensuite:")
    print("  sudo systemctl restart wit-usb-reader")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
