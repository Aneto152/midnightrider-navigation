#!/usr/bin/env python3
"""
MidnightRider — Wave Analyzer v1.0
Estimates significant wave height (Hs) and dominant period (Tp)
from WIT WT901BLECL IMU Z-axis accelerometer data via InfluxDB.

Algorithm:
 1. Read vertical acceleration az (m/s²) from InfluxDB (last N seconds)
 2. Detrend (remove gravity + slow bias)
 3. Bandpass filter for wave frequencies (0.05–1.0 Hz = 1–20s period)
 4. Double-integrate to get vertical displacement
 5. Hs = 4 × std(displacement) [significant wave height definition]
 6. Tp = 1 / peak_frequency [dominant period from FFT]
 7. Write results to InfluxDB → midnight_rider bucket

Signal K paths written:
 environment.water.waves.significantWaveHeight (meters)
 environment.water.waves.dominantPeriod (seconds)

Usage:
 python3 scripts/wave-analyzer.py # runs once
 python3 scripts/wave-analyzer.py --loop 60 # runs every 60 seconds
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

try:
    import numpy as np
    from scipy import signal as sp_signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("⚠️ scipy not installed — using simplified std method (less accurate)", file=sys.stderr)

# Configuration
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")

IMU_MEASUREMENT = "navigation"
IMU_PATH_AZ = "navigation.imu.accelerationZ"

IMU_PATH_CANDIDATES = [
    "navigation.imu.accelerationZ",
    "navigation.acceleration.z",
    "navigation.attitude.accelerationZ",
    "sensors.imu.accelerationZ",
]

WINDOW_SECONDS = 120
GRAVITY = 9.80665
WAVE_FREQ_LOW = 0.05  # Hz (20s period)
WAVE_FREQ_HIGH = 1.0  # Hz (1s period)


def query_influx(flux_query: str) -> list:
    """Execute Flux query, return list of values."""
    req = urllib.request.Request(
        f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
        data=flux_query.encode(),
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "application/vnd.flux",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            lines = r.read().decode().split("\n")
        rows = []
        for line in lines:
            if line.startswith("#") or not line.strip() or "," not in line:
                continue
            parts = line.split(",")
            if len(parts) >= 7:
                try:
                    rows.append(float(parts[6]))
                except (ValueError, IndexError):
                    pass
        return rows
    except Exception as e:
        print(f"Query error: {e}", file=sys.stderr)
        return []


def write_influx(measurement: str, path: str, value: float) -> bool:
    """Write a single value to InfluxDB line protocol."""
    ts = int(time.time() * 1e9)
    line = f'{measurement},source=wave-analyzer value={value:.4f},path="{path}" {ts}'
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    req = urllib.request.Request(
        url,
        data=line.encode(),
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "text/plain",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status in (200, 204)
    except Exception as e:
        print(f"Write error: {e}", file=sys.stderr)
        return False


def find_imu_path() -> str:
    """Auto-detect the correct IMU acceleration path."""
    for candidate in IMU_PATH_CANDIDATES:
        measurement = candidate.split(".")[0]
        flux = f"""from(bucket: "{INFLUX_BUCKET}")
 |> range(start: -10m)
 |> filter(fn: (r) => r["_measurement"] == "{measurement}")
 |> filter(fn: (r) => r["_field"] == "value")
 |> filter(fn: (r) => r["path"] == "{candidate}")
 |> limit(n: 1)"""
        rows = query_influx(flux)
        if rows:
            print(f" Found IMU path: {candidate}")
            return candidate
    return IMU_PATH_AZ


def get_acceleration_data(path: str, window_sec: int) -> tuple:
    """Query vertical acceleration. Returns (az_array, sample_rate_hz) or (None, None)."""
    measurement = path.split(".")[0]
    flux = f"""from(bucket: "{INFLUX_BUCKET}")
 |> range(start: -{window_sec}s)
 |> filter(fn: (r) => r["_measurement"] == "{measurement}")
 |> filter(fn: (r) => r["_field"] == "value")
 |> filter(fn: (r) => r["path"] == "{path}")
 |> sort(columns: ["_time"])"""

    values = query_influx(flux)
    if len(values) < 20:
        print(f" ⚠️ Insufficient data: {len(values)} samples (need ≥20)")
        return None, None

    n = len(values)
    sample_rate = n / max(window_sec, 1)  # rough estimate
    return values, sample_rate


def analyze_waves(az: list, sample_rate: float) -> dict:
    """Compute significant wave height and dominant period."""
    n = len(az)
    if n < 20:
        return {"Hs": None, "Tp": None, "n_samples": n}

    if HAS_SCIPY:
        az = np.asarray(az, dtype=float)
        az_detrended = sp_signal.detrend(az - np.mean(az))

        # Bandpass filter
        nyq = sample_rate / 2.0
        low = WAVE_FREQ_LOW / nyq
        high = min(WAVE_FREQ_HIGH / nyq, 0.99)
        if low < high:
            b, a = sp_signal.butter(4, [low, high], btype='band')
            az_filtered = sp_signal.filtfilt(b, a, az_detrended)
        else:
            az_filtered = az_detrended

        # Double integrate
        dt = 1.0 / sample_rate
        velocity = sp_signal.cumtrapz(az_filtered, dx=dt, initial=0)
        velocity -= np.mean(velocity)
        displacement = sp_signal.cumtrapz(velocity, dx=dt, initial=0)
        displacement -= np.mean(displacement)

        # Significant wave height
        Hs = 4.0 * float(np.std(displacement))

        # Dominant period from FFT
        freqs = np.fft.rfftfreq(len(displacement), d=dt)
        fft_mag = np.abs(np.fft.rfft(displacement))
        wave_mask = (freqs >= WAVE_FREQ_LOW) & (freqs <= WAVE_FREQ_HIGH)
        if np.any(wave_mask) and np.sum(fft_mag[wave_mask]) > 0:
            peak_freq = float(freqs[wave_mask][np.argmax(fft_mag[wave_mask])])
            Tp = 1.0 / peak_freq if peak_freq > 0 else 0.0
        else:
            Tp = 0.0
    else:
        # Simplified: no scipy
        mean_az = sum(az) / len(az)
        variance = sum((x - mean_az) ** 2 for x in az) / len(az)
        std_az = math.sqrt(variance)
        Hs = std_az * 0.1  # rough empirical factor
        Tp = 5.0

    return {
        "Hs": round(max(0.0, Hs), 3),
        "Tp": round(max(0.0, Tp), 1),
        "n_samples": n,
        "sample_rate_hz": round(sample_rate, 2),
    }


def run_once(window_sec: int = WINDOW_SECONDS):
    """Execute one analysis cycle."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Wave analysis starting...")

    imu_path = find_imu_path()
    print(f" IMU path: {imu_path}")

    az, sample_rate = get_acceleration_data(imu_path, window_sec)
    if az is None:
        print(" No IMU data available — skipping this cycle")
        return False

    print(f" Samples: {len(az)} @ {sample_rate:.1f} Hz")

    result = analyze_waves(az, sample_rate)
    Hs = result["Hs"]
    Tp = result["Tp"]

    if Hs is None:
        print(" Analysis failed — insufficient data")
        return False

    print(f" Hs = {Hs:.3f} m | Tp = {Tp:.1f} s")

    # Sanity check (LIS waves: 0.1–3m typical)
    if Hs > 10.0:
        print(f" ⚠️ Hs={Hs:.1f}m exceeds 10m — possible sensor error, not writing")
        return False

    # Write to InfluxDB
    measurement = "environment"
    ok1 = write_influx(measurement, "environment.water.waves.significantWaveHeight", Hs)
    ok2 = write_influx(measurement, "environment.water.waves.dominantPeriod", Tp)

    if ok1 and ok2:
        print(f" ✅ Written: Hs={Hs:.3f}m Tp={Tp:.1f}s → InfluxDB midnight_rider")
        return True
    else:
        print(" ❌ Write failed")
        return False


def main():
    parser = argparse.ArgumentParser(description="MidnightRider Wave Analyzer")
    parser.add_argument("--loop", type=int, default=0,
                       help="Run every N seconds (0 = run once)")
    parser.add_argument("--window", type=int, default=WINDOW_SECONDS,
                       help=f"Analysis window in seconds (default: {WINDOW_SECONDS})")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Wave analyzer running every {args.loop}s (Ctrl+C to stop)")
        try:
            while True:
                run_once(args.window)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_once(args.window)


if __name__ == "__main__":
    main()
