# Navico Race Timer — N2K Protocol Research
## Date: 2026-06-14

## PGNs Identified
| PGN | Hex | Rate | Role |
|-----|-----|------|------|
| 65280 | 0xFF00 | 1 Hz | Timer heartbeat (SA=11, Vulcan 1) |
| 65312 | 0xFF20 | 1 Hz | Timer auxiliary (SA=10) |

## PGN 65280 Payload
Raw: 13 99 04 05 00 00 02 00
Pos: 0  1  2  3  4  5  6  7

- Bytes 0-1: 0x13 0x99 = Navico company 275 + Industry Marine (fixed)
- Byte 2: 0x04 = command = race timer
- Byte 3: 0x05 = sub-command (state/sync)
- Bytes 4-5: 0x00 0x00 = countdown uint16 LE (0 = stopped)
  - HYPOTHESIS: countdown in seconds (300 sec = 5 min = 0x2C 0x01 LE)
  - TO VERIFY on field test
- Byte 6: 0x02 = status (0=stopped? 1=running? 2=synced?)
- Byte 7: 0x00 = reserved

## PGN 65312 Payload
Raw: 13 99 00 00 7F FF FF FF

- Bytes 0-1: 0x13 0x99 = Navico header
- Bytes 2-3: 0x00 0x00 = possibly countdown MSB or mode
- Bytes 4-7: 0x7F 0xFF 0xFF 0xFF = N2K "not available"

## Network Configuration
- Gateway: YDNU-02 (Yacht Devices) on /dev/ttyACM0 @ 115200 baud
- Devices: Both Vulcan 7 FS on same N2K backbone
  - Vulcan 1: SA=11 (primary timer source)
  - Vulcan 2: SA=10 (mirror/backup)

## Integration Plan
**Plugin: signalk-racing-timer-n2k** (Phase 5)
```
Portal → /api/timer (start time) → SK racing.startTime
                                 ↓
                        Plugin reads racing.startTime
                                 ↓
                        Computes countdown = (startTime - now) / 1000
                                 ↓
                        Formats PGN 65280: 13 99 04 05 <LO> <HI> 02 00
                                 ↓
                        sk-to-nmea2000 transmits @ 1 Hz
                                 ↓
                        Vulcan displays countdown
```

## Capture Results (2026-06-13, 64-minute session)
- **PGN 65280:** 256 frames, payload constant (likely awaiting active countdown)
- **PGN 65312:** 64 frames, payload constant
- **Rate:** Both ~1 Hz
- **Transmission:** Continuous, bidirectional (R/T alternating)

## Field Test Checklist
- [ ] Set timer to 5 minutes on Vulcan 1
- [ ] Observe PGN 65280 byte 4-5 values during countdown
- [ ] If decrements: confirm unit (seconds vs. 10x seconds vs. milliseconds)
- [ ] If constant: check byte 6 (status), byte 3 (sub-command)
- [ ] Test timer reset: observe payload change
- [ ] Test timer pause: observe payload freeze
- [ ] Build bidirectional: Portal → SK → N2K timer update

## References
- Navico Proprietary Range: PGN 65280-65535
- Company ID 275: Navico (Garmin, Navionics)
- N2K Fast Packet: multi-frame if > 8 bytes
- Industry: Marine (not available in bytes 4-7 = 0x7F 0xFF...)
