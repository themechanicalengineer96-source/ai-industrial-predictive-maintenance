"""Synthetic, machine-specific sensor generator. All outputs are SIMULATION."""
import math
import random
from datetime import datetime, timezone

FAULTS = {
    "Normal": "Normal operation", "Normal operation": "Normal operation",
    "Bearing wear simulation": "Bearing wear simulation", "Machine imbalance": "Machine imbalance",
    "Shaft misalignment": "Shaft misalignment", "Overheating": "Overheating",
    "Excessive vibration": "Excessive vibration", "High vibration / imbalance": "Machine imbalance",
    "Abnormal RPM": "Abnormal RPM", "Low RPM": "Abnormal RPM", "Combined fault": "Shaft misalignment",
}

def generate_sensor_reading(machine_id, machine=None, fault_mode="Normal operation", seed=None, degradation_pct=0.0):
    machine = machine or {}
    rng = random.Random(seed)
    mtype = machine.get("machine_type", "Electric Motor")
    temp_limit = float(machine.get("temperature_limit", 75))
    vib_limit = float(machine.get("vibration_limit", 4.5))
    rated_rpm = int(machine.get("rpm", 1500))
    profiles = {
        "Electric Motor": (52, 7, 1.5, .55, .018), "Centrifugal Pump": (58, 8, 2.0, .65, .025),
        "Air Compressor": (64, 9, 2.2, .75, .020), "CNC Machine": (43, 6, 1.0, .35, .012),
        "Industrial Fan": (49, 7, 1.3, .5, .022), "Gearbox": (57, 8, 2.1, .65, .015),
        "Conveyor Belt": (46, 6, 1.4, .5, .018),
    }
    base_t, spread_t, base_v, spread_v, rpm_jitter = profiles.get(mtype, (54, 7, 1.6, .6, .02))
    degradation = max(0.0, min(100.0, float(degradation_pct)))
    temp = max(20, rng.gauss(base_t, spread_t) + degradation * .10)
    vibration = max(.1, rng.gauss(base_v, spread_v) + degradation * .025)
    rpm = max(0, int(rated_rpm * (1 + rng.uniform(-rpm_jitter, rpm_jitter) - degradation * .0007)))
    fault = FAULTS.get(fault_mode, fault_mode)
    if fault == "Bearing wear simulation":
        vibration += vib_limit * rng.uniform(.45, .9); temp += rng.uniform(4, 10)
    elif fault == "Machine imbalance":
        vibration += vib_limit * rng.uniform(.65, 1.25)
    elif fault == "Shaft misalignment":
        vibration += vib_limit * rng.uniform(.7, 1.35); temp += rng.uniform(5, 12); rpm = int(rpm * rng.uniform(.94, .99))
    elif fault == "Overheating":
        temp = temp_limit + rng.uniform(4, 18)
    elif fault == "Excessive vibration":
        vibration = vib_limit * rng.uniform(1.55, 2.2)
    elif fault == "Abnormal RPM":
        rpm = int(rated_rpm * rng.uniform(.55, .78))
    status = "CRITICAL" if temp >= temp_limit * 1.15 or vibration >= vib_limit * 1.5 else (
        "WARNING" if temp >= temp_limit or vibration >= vib_limit or rpm < rated_rpm*.85 else "RUNNING")
    load = max(5.0, min(100.0, rng.gauss(68, 12) + (12 if fault != "Normal operation" else 0)))
    voltage = max(180.0, rng.gauss(400.0, 7.0))
    current = max(.1, (load / 100.0) * (2.5 + rated_rpm / 1800.0) * rng.uniform(.92, 1.08))
    operating_hours = float(machine.get("operating_hours", rng.uniform(100, 5000)))
    return {"machine_id": machine_id, "temperature": round(temp, 2), "vibration": round(vibration, 2),
            "rpm": rpm, "operating_hours": round(operating_hours, 1), "machine_load": round(load, 1),
            "current_amp": round(current, 2), "voltage": round(voltage, 1),
            "degradation_pct": round(degradation, 2), "status": status,
            "data_mode": "SIMULATION", "fault_mode": fault, "timestamp": datetime.now(timezone.utc).isoformat()}

def generate_vibration_waveform(samples=500, frequency=25, amplitude=1.4, noise=.12, fault_mode=False, seed=None):
    rng = random.Random(seed)
    time_values = [i / samples for i in range(samples)]
    signal = [amplitude * math.sin(2 * math.pi * frequency * t)
              + (0.8 * math.sin(2 * math.pi * 75 * t) if fault_mode else 0)
              + rng.gauss(0, noise) for t in time_values]
    return time_values, signal
