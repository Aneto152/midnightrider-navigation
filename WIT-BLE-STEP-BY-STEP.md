╔════════════════════════════════════════════════════════════════════════════╗
║                 CONNEXION BLUETOOTH WIT - DIAGRAMME COMPLET               ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────┐                    ┌──────────────┐
│   WIT IMU    │                    │   RPi BLE    │
│  (Device)    │                    │  (Receiver)  │
└──────────────┘                    └──────────────┘
       │                                    │
       │  ÉTAPE 1: Bluetooth Activation     │
       │                                    ├─ systemctl status bluetooth
       │                                    │  → Active: running ✅
       │                                    │
       ├─ Broadcast "Je suis WT901BLE68"   │
       │                                    │
       │  ÉTAPE 2: Scan                     │
       │                                    ├─ bluetoothctl devices
       │  Found: E9:10:DB:8B:CE:C7         │  → Device E9:10:DB:8B:CE:C7
       │         WT901BLE68                 │
       │                                    │
       │  ÉTAPE 3: Connection Request       │
       │  ◄────────────────────────────────├─ bluetoothctl connect
       │  Connection allowed (no PIN)       │
       │  Connection successful ✅          │
       │                                    │
       │  ÉTAPE 4: Verify Connected         │
       │                                    ├─ bluetoothctl info
       │                                    │  → Connected: yes ✅
       │                                    │
       │  ÉTAPE 5: Discover GATT            │
       │  Service 0000ffe5 (Vendor)         │
       │    ├─ Char 0x000e (Data Read)     │
       │    ├─ Descriptor 0x0010 (CCCD)    │
       │    └─ Char 0x000c (Write)         │
       │                                    ├─ bluetoothctl gatt.list
       │                                    │  → Handles found ✅
       │                                    │
       │  ÉTAPE 6A: Read Once               │
       │  [0x55][0x61][18 bytes] ◄─────────├─ gatttool --char-read
       │                          (one-time) │
       │                                    │
       │  ÉTAPE 6B: Continuous Notifications
       │  Enable CCCD (Handle 0x0010)       │
       │  ◄─ Write 0x0100                  ├─ gatttool --char-write
       │                                    │
       │  [0x55][0x61][18 bytes]            │
       │  [0x55][0x61][18 bytes] ◄─────────├─ Listen continuously
       │  [0x55][0x61][18 bytes]            │  (100x per second)
       │  ...                               │

┌──────────────────────────────────────────────────────────────────────────┐
│ PACKET STRUCTURE: [Header][Roll][Pitch][Yaw][Accel X/Y/Z][Gyro X/Y/Z]  │
│ Example: 55 61 18 00 b6 ff 44 08 00 00 00 00 00 00 94 fe 87 ff bd 31   │
└──────────────────────────────────────────────────────────────────────────┘

COMMANDS SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Check Bluetooth Service
   $ systemctl status bluetooth

2. Find WIT in Bluetooth Range
   $ sudo bluetoothctl devices

3. Connect to WIT
   $ sudo bluetoothctl connect E9:10:DB:8B:CE:C7

4. Verify Connected
   $ sudo bluetoothctl info E9:10:DB:8B:CE:C7

5. List GATT Services
   $ sudo bluetoothctl gatt.list-attributes E9:10:DB:8B:CE:C7

6. Read Once
   $ sudo gatttool -b E9:10:DB:8B:CE:C7 --char-read -a 0x000e

7. Enable Notifications (for continuous data)
   $ sudo gatttool -b E9:10:DB:8B:CE:C7 --char-write-req -a 0x0010 -n 0100

PROBLEM FOUND:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ All Bluetooth infrastructure works perfectly!
✅ Connection established successfully
✅ GATT discovery complete
✅ Data format identified (0x55 0x61 packets)

❌ BUT: Signal K plugin won't load the BLE data
   (This is a Signal K v2.25 integration issue, not a WIT/BLE issue)

SOLUTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use USB mode for sailing (data flows immediately via /dev/ttyUSB0)
BLE infrastructure is proven working - debug Signal K plugin later

