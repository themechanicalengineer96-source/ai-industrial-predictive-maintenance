"""Temperature evaluation and explicitly synthetic trend generation."""
import math
import random


def generate_temperature_reading(base_temperature=55, variation=5):
    return round(base_temperature + random.uniform(-variation, variation), 2)


def evaluate_temperature(temperature, warning_limit=75, critical_limit=90):
    if critical_limit <= warning_limit:
        raise ValueError("Critical limit must exceed warning limit.")
    value = float(temperature)
    if value >= critical_limit:
        status, severity, action = "CRITICAL", "RED", "Over-temperature: verify the measurement and inspect cooling/load conditions."
    elif value >= warning_limit:
        status, severity, action = "WARNING", "YELLOW", "Temperature elevated: review ventilation, cooling and operating load."
    else:
        status, severity, action = "NORMAL", "GREEN", "Temperature is within the configured limit."
    return {"temperature": round(value, 2), "status": status, "severity": severity,
            "warning_limit": warning_limit, "critical_limit": critical_limit,
            "recommended_action": action}


def generate_temperature_history(samples=60, base_temperature=55, seed=42):
    rng = random.Random(seed)
    return [round(base_temperature + 4 * math.sin(i / 8) + rng.uniform(-1.5, 1.5), 2) for i in range(samples)]
