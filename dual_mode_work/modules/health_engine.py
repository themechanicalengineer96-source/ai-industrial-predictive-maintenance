"""Transparent rule-based health scoring; not a certified failure probability."""


def calculate_machine_health(temperature, vibration, temperature_limit=75, vibration_limit=4.5):
    temp_ratio = max(0.0, float(temperature) / max(float(temperature_limit), 1e-6) - 0.85)
    vib_ratio = max(0.0, float(vibration) / max(float(vibration_limit), 1e-6) - 0.75)
    penalty = min(50, temp_ratio * 100) * 0.45 + min(50, vib_ratio * 100) * 0.55
    return round(max(0.0, min(100.0, 100.0 - penalty)), 1)


def evaluate_machine(temperature, vibration, temperature_limit=75, vibration_limit=4.5):
    health = calculate_machine_health(temperature, vibration, temperature_limit, vibration_limit)
    if temperature >= temperature_limit * 1.15 or vibration >= vibration_limit * 1.5:
        status, severity, action = "CRITICAL", "RED", "Inspect the machine promptly; verify sensor readings and follow site safety procedures."
    elif temperature >= temperature_limit or vibration >= vibration_limit or health < 75:
        status, severity, action = "WARNING", "YELLOW", "Review operating conditions and schedule an inspection if the trend persists."
    else:
        status, severity, action = "RUNNING", "GREEN", "Readings are within the configured demonstration limits; continue monitoring."
    return {"health_percentage": health, "status": status, "severity": severity, "recommended_action": action}
