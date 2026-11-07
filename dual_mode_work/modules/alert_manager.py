"""Rule and model alert evaluation. Persistence is handled by database.py."""


def evaluate_alerts(reading, ai_result=None, temperature_limit=75, vibration_limit=4.5, rated_rpm=None):
    mode = reading.get("data_mode")
    if mode not in ("SIMULATION", "REAL"):
        raise ValueError("Unknown sensor data mode.")
    temperature = float(reading["temperature"])
    vibration = float(reading["vibration"])
    health = float(reading.get("health_percentage", 100))
    alerts = []
    def add(severity, problem, action):
        alerts.append({"severity": severity, "problem": problem, "recommended_action": action})
    if temperature >= temperature_limit * 1.15:
        add("CRITICAL", f"Critical temperature: {temperature:.1f} °C", "Verify the sensor and inspect cooling/load conditions promptly.")
    elif temperature >= temperature_limit:
        add("WARNING", f"Temperature above configured limit: {temperature:.1f} °C", "Review cooling, ventilation and load.")
    if vibration >= vibration_limit * 1.5:
        add("CRITICAL", f"Critical vibration: {vibration:.2f} mm/s", "Verify the measurement; inspect bearings, alignment and mounting.")
    elif vibration >= vibration_limit:
        add("WARNING", f"Vibration above configured limit: {vibration:.2f} mm/s", "Review vibration trend and inspect bearings/alignment.")
    if rated_rpm:
        rpm = float(reading.get("rpm", 0))
        if rpm < float(rated_rpm) * .75 or rpm > float(rated_rpm) * 1.15:
            add("WARNING", f"Abnormal RPM: {rpm:.0f} against rated {float(rated_rpm):.0f} RPM",
                "Check drive load, supply, speed controller and tachometer reading.")
    fault = reading.get("fault_mode", "Normal operation")
    fault_guidance = {
        "Bearing wear simulation": ("Bearing-wear scenario active", "Inspect bearing condition, lubrication and vibration trend."),
        "Machine imbalance": ("Imbalance scenario active", "Inspect rotor balance, deposits and mounting."),
        "Shaft misalignment": ("Shaft-misalignment scenario active", "Check coupling alignment, soft foot and shaft runout."),
        "Overheating": ("Overheating scenario active", "Inspect cooling path, ventilation and operating load."),
        "Excessive vibration": ("Excessive-vibration scenario active", "Inspect bearings, mounting, looseness and resonance."),
        "Abnormal RPM": ("Abnormal-RPM scenario active", "Check drive, load, controller and speed sensor."),
    }
    if fault in fault_guidance:
        title, action = fault_guidance[fault]
        add("WARNING", title, action)
    if health < 50:
        add("CRITICAL", f"Illustrative machine health score is low: {health:.1f}%", "Arrange a qualified inspection; this score is not a failure probability.")
    elif health < 75:
        add("WARNING", f"Illustrative machine health score declining: {health:.1f}%", "Review trends and plan preventive maintenance.")
    if ai_result and ai_result.get("anomaly_detected"):
        add("WARNING", "AI model flagged an unusual sensor pattern.", ai_result.get("recommended_action", "Verify sensor readings."))
    return alerts


def save_alerts(machine_id, alerts, data_mode="SIMULATION"):
    from modules.database import save_alerts as persist
    return persist(machine_id, alerts, data_mode)


def process_machine_alerts(reading, ai_result=None):
    alerts = evaluate_alerts(reading, ai_result)
    saved = save_alerts(reading["machine_id"], alerts, reading["data_mode"])
    return {"machine_id": reading["machine_id"], "alert_count": saved,
            "alerts": alerts, "data_mode": reading["data_mode"]}
