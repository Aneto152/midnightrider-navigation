#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║ MIDNIGHT RIDER — DATA SIMULATOR (DEV ONLY)                          ║
║ Branch: dev/simulator — DO NOT MERGE TO MAIN                        ║
║                                                                      ║
║ Injects synthetic data into Signal K + InfluxDB for testing.        ║
║ Safe by design: requires SIMULATOR_ENABLED=true to run.            ║
║ Writes to midnight_rider_sim bucket by default (not midnight_rider)║
║                                                                      ║
║ REMOVAL: delete scripts/dev/ entirely. Zero production impact.      ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
  SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --list
  SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind
  SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --scenario upwind --live
  SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --verify-fields
"""

import os, sys, json, time, math, random, argparse, signal
from datetime import datetime
from pathlib import Path

# ─── Safety gate ──────────────────────────────────────────────────────────────

if os.environ.get("SIMULATOR_ENABLED", "").lower() != "true":
    print("❌ SIMULATOR_ENABLED=true required. This is a dev-only tool.")
    print(" Run: SIMULATOR_ENABLED=true python3 scripts/dev/simulator.py --help")
    sys.exit(1)

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("❌ influxdb-client not installed: pip3 install influxdb-client")
    sys.exit(1)

import urllib.request
import urllib.error

# ─── Configuration ────────────────────────────────────────────────────────────

INFLUX_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "midnight_rider")
SIGNALK_URL = os.environ.get("SIGNALK_URL", "http://localhost:3000")

SIM_BUCKET = "midnight_rider_sim"
LIVE_BUCKET = "midnight_rider"
INTERVAL_SEC = 5
MAX_RUNTIME = 7200

# ─── Signal K path map ────────────────────────────────────────────────────────
# Maps InfluxDB field names → Signal K paths + SI unit converters

SK_PATH_MAP = {
    "sog_kts": ("navigation.speedOverGround", lambda v: v * 0.514444),
    "stw_kts": ("navigation.speedThroughWater", lambda v: v * 0.514444),
    "cog_deg": ("navigation.courseOverGroundTrue", lambda v: math.radians(v)),
    "heading_mag_deg": ("navigation.headingMagnetic", lambda v: math.radians(v)),
    "heel_deg": ("navigation.attitude.roll", lambda v: math.radians(v)),
    "pitch_deg": ("navigation.attitude.pitch", lambda v: math.radians(v)),
    "depth_m": ("environment.depth.belowKeel", lambda v: v),
    "tws_kts": ("environment.wind.speedTrue", lambda v: v * 0.514444),
    "aws_kts": ("environment.wind.speedApparent", lambda v: v * 0.514444),
    "twa_deg": ("environment.wind.angleTrueWater", lambda v: math.radians(v)),
    "awa_deg": ("environment.wind.angleApparent", lambda v: math.radians(v)),
    "twd_deg": ("environment.wind.directionTrue", lambda v: math.radians(v)),
    "pressure_hpa": ("environment.outside.pressure", lambda v: v * 100.0),
    "air_temp_c": ("environment.outside.temperature", lambda v: v + 273.15),
    "water_temp_c": ("environment.water.temperature", lambda v: v + 273.15),
    "vmg_kts": ("performance.velocityMadeGood", lambda v: v * 0.514444),
    "target_speed_kts": ("performance.targetSpeed", lambda v: v * 0.514444),
    "current_drift_kts": ("environment.current.drift", lambda v: v * 0.514444),
    "current_set_deg": ("environment.current.setTrue", lambda v: math.radians(v)),
}

def inject_signalk(scenario_data, verbose=False):
    """Inject values into Signal K via HTTP PUT.
    Only injects fields present in SK_PATH_MAP.
    HTTP 405 = path read-only in SK → silently skipped.
    """
    headers = {"Content-Type": "application/json"}
    injected = 0
    skipped = 0
    failed = 0

    for measurement, fields in scenario_data.items():
        for field, value in fields.items():
            if field not in SK_PATH_MAP:
                skipped += 1
                continue
            sk_path, converter = SK_PATH_MAP[field]
            try:
                sk_value = converter(float(value))
            except Exception:
                skipped += 1
                continue

            path_url = sk_path.replace(".", "/")
            url = f"{SIGNALK_URL}/signalk/v1/api/vessels/self/{path_url}"
            payload = json.dumps({"value": sk_value}).encode()

            try:
                req = urllib.request.Request(
                    url, data=payload, headers=headers, method="PUT")
                with urllib.request.urlopen(req, timeout=3):
                    injected += 1
            except urllib.error.HTTPError as e:
                if e.code == 405:
                    skipped += 1  # read-only path, normal
                else:
                    failed += 1
                    if verbose:
                        print(f" ⚠️ SK PUT {sk_path} → HTTP {e.code}")
            except Exception as e:
                failed += 1
                if verbose:
                    print(f" ⚠️ SK {sk_path} → {type(e).__name__}")

    if verbose or injected > 0:
        status = f"✅ Signal K : {injected} injected"
        if skipped:
            status += f", {skipped} skipped"
        if failed:
            status += f", {failed} failed"
        print(f" {status}")
    return injected

# ─── Scenarios ────────────────────────────────────────────────────────────────

SCENARIOS = {
    "calibrate": {
        "description": "Known exact values — use to verify all field names",
        "data": {
            "navigation": {
                "sog_kts": 5.0, "stw_kts": 4.8, "cog_deg": 270.0,
                "heading_mag_deg": 268.0, "heel_deg": 10.0, "pitch_deg": 2.0,
                "depth_m": 15.0
            },
            "environment": {
                "tws_kts": 10.0, "twa_deg": 45.0, "aws_kts": 13.0,
                "pressure_hpa": 1013.0, "air_temp_c": 15.0, "water_temp_c": 12.0
            },
            "performance": {
                "vmg_kts": 3.5, "target_speed_kts": 5.8, "polar_ratio": 0.86
            },
        }
    },

    "upwind": {
        "description": "Upwind beat — TWS 12kt, TWA 45°, heel 18°",
        "variance": 0.05,
        "data": {
            "navigation": {
                "sog_kts": 6.2, "stw_kts": 6.0, "cog_deg": 285.0,
                "heading_mag_deg": 282.0, "heel_deg": 18.5, "pitch_deg": 3.0,
                "depth_m": 25.0
            },
            "environment": {
                "tws_kts": 12.0, "twa_deg": 45.0, "aws_kts": 16.5,
                "pressure_hpa": 1016.0, "air_temp_c": 14.0, "water_temp_c": 11.5
            },
            "performance": {
                "vmg_kts": 4.8, "target_speed_kts": 6.1, "polar_ratio": 0.92,
            }
        }
    },

    "downwind": {
        "description": "Downwind run — TWS 15kt, spinnaker",
        "variance": 0.06,
        "data": {
            "navigation": {
                "sog_kts": 7.8, "stw_kts": 7.5, "cog_deg": 95.0,
                "heading_mag_deg": 93.0, "heel_deg": -12.0, "pitch_deg": -2.0,
                "depth_m": 30.0
            },
            "environment": {
                "tws_kts": 15.0, "twa_deg": 155.0, "aws_kts": 10.0,
                "pressure_hpa": 1014.0, "air_temp_c": 16.0, "water_temp_c": 12.0
            },
            "performance": {
                "vmg_kts": 7.2, "target_speed_kts": 8.1, "polar_ratio": 0.89,
            }
        }
    },

    "storm-alert": {
        "description": "⚠️ DECLENCHE LES ALERTES — heel >25°, TWS 28kt",
        "variance": 0.03,
        "data": {
            "navigation": {
                "sog_kts": 8.1, "stw_kts": 7.9, "cog_deg": 310.0,
                "heading_mag_deg": 308.0, "heel_deg": 28.0, "pitch_deg": 8.0,
                "depth_m": 20.0
            },
            "environment": {
                "tws_kts": 28.0, "twa_deg": 42.0, "aws_kts": 33.0,
                "pressure_hpa": 998.0, "air_temp_c": 10.0, "water_temp_c": 10.5
            },
            "performance": {
                "vmg_kts": 5.1, "target_speed_kts": 7.2, "polar_ratio": 0.71
            }
        }
    },

    "the-race": {
        "description": "Passage de The Race — courant 4.5kt E, J/30 lutte contre le courant",
        "variance": 0.08,
        "data": {
            "navigation": {
                "sog_kts": 2.1, "stw_kts": 6.3, "cog_deg": 185.0,
                "heading_mag_deg": 180.0, "heel_deg": 22.0, "pitch_deg": 4.0,
                "depth_m": 45.0
            },
            "environment": {
                "tws_kts": 14.0, "twa_deg": 40.0, "aws_kts": 18.5,
                "pressure_hpa": 1011.0, "air_temp_c": 13.0, "water_temp_c": 11.0
            },
            "performance": {
                "vmg_kts": 1.8, "target_speed_kts": 6.1, "polar_ratio": 0.88
            },
            "environment_current": {
                "current_drift_kts": 4.5, "current_set_deg": 90.0
            }
        }
    },

    "race-start": {
        "description": "Ligne de départ Stamford — timer 4m30, layline, boat speed max",
        "variance": 0.04,
        "data": {
            "navigation": {
                "sog_kts": 5.8, "stw_kts": 5.7, "cog_deg": 295.0,
                "heading_mag_deg": 292.0, "heel_deg": 16.0, "pitch_deg": 2.5,
                "depth_m": 18.0
            },
            "environment": {
                "tws_kts": 10.0, "twa_deg": 48.0, "aws_kts": 13.5,
                "pressure_hpa": 1017.0, "air_temp_c": 18.0, "water_temp_c": 13.0
            },
            "performance": {
                "vmg_kts": 4.2, "target_speed_kts": 5.9, "polar_ratio": 0.95
            },
            "racing": {
                "start_timer_min": 4.5
            }
        }
    },

    "anchor": {
        "description": "Au mouillage — toutes mesures a zero",
        "data": {
            "navigation": {
                "sog_kts": 0.0, "stw_kts": 0.0, "cog_deg": 0.0,
                "heading_mag_deg": 180.0, "heel_deg": 0.5, "pitch_deg": 0.2,
                "depth_m": 4.0
            },
            "environment": {
                "tws_kts": 3.0, "twa_deg": 90.0, "aws_kts": 3.0,
                "pressure_hpa": 1015.0, "air_temp_c": 20.0, "water_temp_c": 14.0
            },
            "performance": {
                "vmg_kts": 0.0, "target_speed_kts": 0.0, "polar_ratio": 0.0
            }
        }
    }
}

# ─── InfluxDB writers ─────────────────────────────────────────────────────────

def write_influxdb(scenario_data, bucket, verbose=False):
    """Write all fields directly to InfluxDB."""
    if not INFLUX_TOKEN:
        print("❌ INFLUX_TOKEN not set")
        return False

    try:
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            points = []

            for measurement, fields in scenario_data.items():
                meas_name = measurement.split(".")[0] if "." in measurement else measurement
                for field, value in fields.items():
                    if isinstance(value, (int, float)):
                        p = Point(meas_name).field(field, float(value))
                        points.append(p)

            write_api.write(bucket=bucket, record=points)
            if verbose:
                total = sum(len(f) for f in scenario_data.values())
                print(f" ✅ InfluxDB → {bucket} : {total} fields")
            return True
    except Exception as e:
        print(f" ❌ InfluxDB error: {e}")
        return False

def ensure_sim_bucket():
    """Create midnight_rider_sim bucket if it doesn't exist."""
    if not INFLUX_TOKEN:
        return False
    try:
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            buckets_api = client.buckets_api()
            existing = [b.name for b in buckets_api.find_buckets().buckets]
            if SIM_BUCKET not in existing:
                buckets_api.create_bucket(bucket_name=SIM_BUCKET, org=INFLUX_ORG)
                print(f"✅ Bucket cree: {SIM_BUCKET}")
            else:
                print(f"✅ Bucket existant: {SIM_BUCKET}")
            return True
    except Exception as e:
        print(f"❌ Bucket error: {e}")
        return False

def apply_variance(data, variance):
    """Apply small random variation to simulate realistic sensor noise."""
    result = {}
    for measurement, fields in data.items():
        result[measurement] = {}
        for field, value in fields.items():
            if isinstance(value, float) and value != 0.0 and variance > 0:
                noise = value * variance * (random.random() * 2 - 1)
                result[measurement][field] = round(value + noise, 4)
            else:
                result[measurement][field] = value
    return result

def verify_fields(bucket):
    """Inject calibrate scenario and show field map."""
    print("\n=== VERIFY FIELDS — Calibrate scenario ===\n")
    scenario = SCENARIOS["calibrate"]
    write_influxdb(scenario["data"], bucket, verbose=True)
    time.sleep(2)
    print(f"\nChamps injectes dans {bucket}:")
    print(f"{'MEASUREMENT':<15} {'FIELD':<25} {'VALUE'}")
    print("-" * 55)
    for meas, fields in scenario["data"].items():
        for field, value in fields.items():
            print(f" {meas:<15} {field:<25} {value}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="⚠️ DEV ONLY — Midnight Rider Data Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--scenario", help="Scenario name (see --list)")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--continuous", action="store_true", help=f"Loop every {INTERVAL_SEC}s")
    parser.add_argument("--live", action="store_true",
                       help=f"⚠️ Write to REAL bucket '{LIVE_BUCKET}'")
    parser.add_argument("--verify-fields", action="store_true", help="Inject calibrate + show fields")
    parser.add_argument("--no-signalk", action="store_true",
                       help="Skip Signal K injection (InfluxDB only)")
    parser.add_argument("--interval", type=int, default=INTERVAL_SEC)
    args = parser.parse_args()

    print("=" * 60)
    print("⚠️  MIDNIGHT RIDER — SIMULATOR (DEV ONLY)")
    print("=" * 60)

    bucket = LIVE_BUCKET if args.live else SIM_BUCKET
    if args.live:
        print(f"🔴 LIVE MODE — writing to REAL bucket: {LIVE_BUCKET}")
        confirm = input(" Confirm? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)
    else:
        print(f"🟢 SAFE MODE — writing to sim bucket: {SIM_BUCKET}")
        ensure_sim_bucket()

    if args.list:
        print("\nScenarios disponibles:\n")
        for name, s in SCENARIOS.items():
            print(f" {name:<15} {s['description']}")
        return

    if args.verify_fields:
        verify_fields(bucket)
        return

    if not args.scenario:
        parser.print_help()
        return

    if args.scenario not in SCENARIOS:
        print(f"❌ Scenario '{args.scenario}' inconnu. Use --list")
        sys.exit(1)

    scenario = SCENARIOS[args.scenario]
    variance = scenario.get("variance", 0.0) if args.continuous else 0.0

    print(f"\n📊 Scenario: {args.scenario}")
    print(f" {scenario['description']}")
    print(f" Bucket: {bucket}")
    print(f" Mode: {'continuous (Ctrl+C to stop)' if args.continuous else 'single shot'}\n")

    start_time = time.time()
    def on_signal(sig, frame):
        print(f"\n✅ Simulator stopped after {int(time.time()-start_time)}s")
        sys.exit(0)
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    cycle = 0
    while True:
        cycle += 1
        data = apply_variance(scenario["data"], variance)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle {cycle}", end=" ")
        write_influxdb(data, bucket, verbose=(cycle == 1))
        if not args.no_signalk:
            inject_signalk(data, verbose=(cycle == 1))

        if cycle == 1 and not args.continuous:
            print(f"\n✅ Single shot done — bucket: {bucket}")
            break

        elapsed = time.time() - start_time
        if elapsed > MAX_RUNTIME:
            print(f"\n⏱️ Max runtime {MAX_RUNTIME}s reached — stopping")
            break

        print(f"→ next in {args.interval}s")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
