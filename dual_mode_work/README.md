# AI-Based Industrial Predictive Maintenance Software — Dual Operating Mode

This is an in-place upgrade of the supplied Streamlit project. The existing 12 workspaces, machine registry, animated factory digital twin, vibration/temperature/RPM views, Isolation Forest diagnostics, alerts, maintenance history and reporting are retained.

> **SIMULATION MODE — NOT CONNECTED TO REAL HARDWARE**

## Operating modes

### 1. Simulation Mode (available now)
- Runs without physical sensors, PLCs or gateways.
- Generates machine-specific temperature, vibration, RPM, load, current, voltage and operating-hours values.
- Supports Start, Pause, Reset, simulation speed, per-machine fault scenarios and gradual synthetic degradation.
- Synthetic readings are saved in the existing `sensor_readings` table with `data_mode='SIMULATION'`.
- Simulation data is clearly labelled on the dashboard and in reports.

### 2. Real Hardware Mode (prepared, intentionally disabled)
- Can be selected from **Settings → Operating mode** or the sidebar mode selector.
- This build has no configured or verified sensor adapter, so it displays **HARDWARE DISCONNECTED** and deliberately shows no synthetic readings in this mode.
- The `modules/sensor_adapters.py` module defines a safe adapter contract for future temperature, accelerometer/vibration, RPM, current/voltage, PLC and industrial IoT integrations (e.g. Modbus TCP, MQTT and OPC UA).
- A separate `real_sensor_readings` SQLite table is reserved for validated real telemetry. It is not populated by this build.
- A future adapter must verify endpoint identity, connectivity, units, timestamps, calibration and data quality before any reading can be stored as REAL.
- No motor control, emergency stop, machine trip or other safety output is implemented.

## AI diagnostics and limitations

Isolation Forest is an unsupervised anomaly-detection model trained on a synthetic multi-machine baseline using temperature, vibration, RPM, machine load, current and voltage. It flags unusual combinations relative to that baseline; it does **not** guarantee a fault, provide a failure probability, predict an exact failure date or estimate remaining useful life. Sensor contribution values are standardized deviations, not causal explanations. Health scores and limits are illustrative, not certified operating or safety thresholds.

## Database safety

- Existing `data/maintenance.db` is included in the project archive.
- Schema changes are additive only; no existing tables are dropped and no data reset is performed.
- New simulation telemetry columns are added only when missing.
- `real_sensor_readings` is a separate table to prevent simulation/real measurement mixing.
- Back up your working `data/maintenance.db` before running an upgrade against your own production or demonstration data.

## Windows VS Code installation

Open the extracted project folder in VS Code, then use **Terminal → New Terminal** (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks virtual-environment activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Open the URL printed by Streamlit, normally `http://localhost:8501`. Keep the terminal open while using the dashboard; press `Ctrl+C` to stop it.

## Recommended demonstration

1. Keep **Simulation Mode** selected.
2. Click **Generate sensor cycle** or press **Start** for timed cycles.
3. Choose a machine and fault scenario, then click **SIMULATE FAULT**.
4. Review AI Diagnostics, Vibration Analysis, Temperature Monitoring, RPM & Speed Monitoring and Maintenance Alerts.
5. Click **Reset to Normal** or **Reset simulation** to clear active scenarios/degradation counters. Existing history is retained.
6. Select **Real Hardware Mode** to demonstrate the safe disconnected state. No synthetic values are shown as real measurements.

## Validation performed in this delivery

- Python source AST/syntax parsing: passed.
- Simulator generation including load/current/voltage/degradation fields: passed.
- Additive SQLite migration on a disposable copy of the supplied database: passed.
- Simulation telemetry insert and mode-filtered read: passed.
- REAL telemetry table exists separately and remains empty: passed.
- Hardware adapter remains disconnected and refuses reads: passed.
- ZIP integrity: checked before delivery.
- Live Streamlit browser test: not performed in this environment; please run locally using the commands above.

## Known limitations

- All currently available readings and faults are synthetic.
- Real sensor protocol drivers, authentication, calibration workflows, role-based access, industrial cybersecurity and site acceptance testing are not included.
- Simulation speed scales the synthetic degradation and operating-hours increments; it is a demonstration control, not a physical-time model.
- Isolation Forest has not been trained or validated on plant-specific labelled failure history.
