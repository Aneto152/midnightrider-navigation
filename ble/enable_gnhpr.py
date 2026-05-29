#!/usr/bin/env python3
"""
Activer GNHPR (Heading/Pitch/Roll) sur UM982
"""

import serial
import time

PORT = '/dev/ttyUSB0'
BAUD = 115200

def send_cmd(ser, cmd):
    """Envoyer une commande et attendre la réponse"""
    full_cmd = cmd.strip() + '\r\n'
    ser.write(full_cmd.encode())
    time.sleep(0.5)
    response = ser.read(ser.in_waiting or 256).decode(errors='ignore')
    print(f"  → {cmd}")
    if response.strip():
        print(f"    ✅ {response.strip()[:80]}")
    return response

print("═══════════════════════════════════════════════════════════")
print("ACTIVATION GNHPR SUR UM982")
print("═══════════════════════════════════════════════════════════\n")

try:
    with serial.Serial(PORT, BAUD, timeout=2) as ser:
        time.sleep(1)
        
        print("1️⃣ ARRÊTER TOUTES LES SORTIES:")
        send_cmd(ser, 'unlog')
        time.sleep(1)
        
        print("\n2️⃣ VÉRIFIER CONFIGURATION ACTUELLE:")
        send_cmd(ser, 'config')
        time.sleep(1)
        
        print("\n3️⃣ ACTIVER LES PHRASES NÉCESSAIRES:")
        send_cmd(ser, 'gngga 1')      # Position GPS, 1 Hz
        time.sleep(0.5)
        send_cmd(ser, 'gnrmc 1')      # Position + vitesse, 1 Hz
        time.sleep(0.5)
        send_cmd(ser, 'gnvtg 1')      # Vitesse et cap, 1 Hz
        time.sleep(0.5)
        send_cmd(ser, 'gnzda 1')      # Date/heure UTC, 1 Hz
        time.sleep(0.5)
        send_cmd(ser, 'gnhpr 1')      # ⭐ HEADING + PITCH + ROLL, 1 Hz
        time.sleep(0.5)
        send_cmd(ser, 'bestnava 1')   # Meilleure position, 1 Hz
        time.sleep(1)
        
        print("\n4️⃣ VÉRIFIER QUE GNHPR SORT BIEN:")
        gnhpr_found = False
        start = time.time()
        print("  Écoutant pendant 15 secondes...")
        while time.time() - start < 15:
            line = ser.readline().decode(errors='ignore').strip()
            if 'GNHPR' in line:
                print(f"    ✅ GNHPR REÇU: {line}")
                gnhpr_found = True
                break
            elif line.startswith('$'):
                print(f"       {line[:60]}")
        
        if not gnhpr_found:
            print("    ⚠️ GNHPR non reçu après 15s")
        
        print("\n5️⃣ SAUVEGARDER EN FLASH (survit au reboot):")
        send_cmd(ser, 'saveconfig')
        time.sleep(2)
        
        print("\n═══════════════════════════════════════════════════════════")
        print("✅ CONFIGURATION COMPLÉTÉE")
        print("═══════════════════════════════════════════════════════════\n")

except Exception as e:
    print(f"❌ ERREUR: {e}")
    exit(1)
