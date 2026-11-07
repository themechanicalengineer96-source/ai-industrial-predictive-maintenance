"""Industrial predictive maintenance dashboard.

Default source is SIMULATION. REAL mode is intentionally not enabled until a
verified sensor adapter is configured; this application never fabricates REAL data.
"""
from datetime import date, datetime, timezone
import io
import time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from modules.machine_manager import MACHINE_TYPES, create_initial_machines, add_machine
from modules.simulator import generate_sensor_reading
from modules.database import (
    initialize_database, save_machine, get_machines, save_sensor_reading,
    get_latest_readings, get_recent_readings, save_alerts, get_alert_history,
    update_alert, add_maintenance_record, get_maintenance_history,
)
from modules.health_engine import evaluate_machine
from modules.vibration import generate_vibration_signal, analyze_vibration
from modules.temperature import evaluate_temperature
from modules.anomaly_detection import PredictiveMaintenanceAI
from modules.alert_manager import evaluate_alerts
from modules.sensor_adapters import get_hardware_status, SUPPORTED_INTEGRATIONS
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="Industrial Predictive Maintenance", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

# --------------------------- Industrial responsive theme ---------------------------
st.markdown("""
<style>
:root{--bg:#08111e;--panel:#101d2d;--panel2:#14243a;--line:#263b54;--muted:#91a6bf;--cyan:#35c8e8;--green:#31c48d;--amber:#f6b84a;--red:#f36b72}
.stApp{background:radial-gradient(ellipse at 15% 0%,#14283d 0%,#08111e 48%);color:#e8f1fb;font-family:Inter,'Segoe UI',sans-serif}
[data-testid="stHeader"]{background:rgba(8,17,30,.86)}
.main .block-container{max-width:1600px;padding:1.5rem clamp(1rem,3vw,3rem) 3rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#102137,#091421);border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:#dce9f7}
h1,h2,h3{letter-spacing:-.025em;color:#f1f7ff!important}
h1{font-weight:800!important}
p, label, [data-testid="stCaptionContainer"]{color:#a6b9ce}
div[data-testid="stMetric"]{background:linear-gradient(145deg,#172a40,#101d2d);border:1px solid #29445f;border-radius:15px;padding:15px 17px;box-shadow:0 8px 24px #0002}
div[data-testid="stMetricLabel"]{color:#9db2c9} div[data-testid="stMetricValue"]{color:var(--cyan);font-weight:800}
.stButton>button{border-radius:10px;border:1px solid #267e9b;background:linear-gradient(100deg,#087da5,#1768b5);color:white;font-weight:700;min-height:42px}
.stButton>button:hover{border-color:#61ddf3;background:#1689ad}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:#2a405a!important;border-radius:16px;background:linear-gradient(145deg,#122238,#0d1928)}
[data-testid="stPlotlyChart"]{border:1px solid #263d57;border-radius:14px;background:#0d1a2a;padding:5px}
[data-testid="stAlert"]{border-radius:12px}
.status-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;animation:pulse 1.8s infinite}
.dot-green{background:#31c48d;box-shadow:0 0 12px #31c48d}.dot-amber{background:#f6b84a;box-shadow:0 0 12px #f6b84a}.dot-red{background:#f36b72;box-shadow:0 0 12px #f36b72}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
/* Animated industrial UI */
.main .block-container{animation:pageIn .4s ease-out both}@keyframes pageIn{from{opacity:.7;transform:translateY(6px)}to{opacity:1;transform:none}}
.twin-panel{border:1px solid #29445f;border-radius:18px;padding:18px;background:linear-gradient(145deg,#12243a,#091522);overflow:hidden;box-shadow:0 12px 35px #0003}
.twin-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:8px}.twin-label{font-size:.72rem;letter-spacing:.14em;color:#82a1bd;font-weight:800}.twin-svg{width:100%;height:auto;max-height:260px}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 3s linear infinite}.spin-slow{transform-box:fill-box;transform-origin:center;animation:spin 7s linear infinite}.shaft{stroke-dasharray:9 7;animation:shaftFlow 1s linear infinite}.flow{stroke-dasharray:5 12;animation:shaftFlow 1.2s linear infinite}.sensor-pulse{animation:pulse 1.4s ease-in-out infinite}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes shaftFlow{to{stroke-dashoffset:-32}}
.wave-live{height:88px;width:100%;border-radius:12px;background:linear-gradient(90deg,#0b1c2d,#102a3e);border:1px solid #29445f;padding:8px;margin:8px 0 14px}.wave-live svg{width:100%;height:100%}.wave-path{fill:none;stroke:#35c8e8;stroke-width:2.4;stroke-dasharray:8 7;animation:waveMove 1s linear infinite;filter:drop-shadow(0 0 5px #35c8e899)}@keyframes waveMove{to{stroke-dashoffset:-60}}
.temp-track{height:10px;background:#20364c;border-radius:20px;overflow:hidden;margin:10px 0}.temp-fill{height:100%;border-radius:20px;animation:gaugeIn 1.1s ease-out both;box-shadow:0 0 12px currentColor}@keyframes gaugeIn{from{width:0!important}}

.machine-stage{position:relative;border:1px solid #244761;border-radius:14px;background:radial-gradient(ellipse at 48% 55%,#123b5a 0%,#091a2a 58%,#071321 100%);padding:8px 10px 2px;overflow:hidden}
.machine-stage:before{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 15%,#36cfff0b 48%,transparent 72%);pointer-events:none}
.machine-svg{display:block;width:100%;max-height:370px;position:relative;z-index:1}
.shaft-highlight{animation:shaftTravel .8s linear infinite}.fan-spin,.pump-spin,.gear-large,.gear-small{transform-box:fill-box;transform-origin:center;animation:spin 2.4s linear infinite}.pump-spin{animation-duration:3.2s}.gear-small{animation:spinReverse 3.1s linear infinite}.spin-reverse{transform-box:fill-box;transform-origin:center}
.data-flow{animation:shaftTravel 1.1s linear infinite}.delay-1{animation-delay:.35s}.delay-2{animation-delay:.7s}.delay-3{animation-delay:1.05s}
.twin-stats{display:flex;gap:12px 22px;align-items:center;flex-wrap:wrap;padding:12px 4px 2px;color:#91abc3;font-size:.75rem}.twin-stats b{color:#36d6a0}.twin-stats strong{color:#d8efff;margin-left:5px}.sim-note{color:#f6c66e;font-weight:800;letter-spacing:.05em}
@keyframes shaftTravel{to{stroke-dashoffset:-62}}@keyframes spinReverse{to{transform:rotate(-360deg)}}

@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important}}

.machine-title{font-size:1.15rem;font-weight:800;color:#eff7ff}.eyebrow{font-size:.72rem;letter-spacing:.13em;color:#6f8ba8;font-weight:800;text-transform:uppercase}
.machine-meta{font-size:.82rem;color:#8fa8c2}.source-pill{display:inline-block;padding:4px 9px;border:1px solid #986d2c;border-radius:20px;color:#ffd17c;background:#5c411b33;font-size:.7rem;font-weight:800;letter-spacing:.06em}
div[data-testid="stTabs"] button{font-weight:700}
@media(max-width:760px){.main .block-container{padding:.8rem .75rem 2rem}h1{font-size:1.65rem!important}div[data-testid="stMetric"]{padding:10px}}
</style>
""", unsafe_allow_html=True)

initialize_database()

# Restore persisted machines (including records created by the earlier version).
if "machines" not in st.session_state:
    stored = get_machines()
    if stored:
        st.session_state.machines = [{
            "machine_id": m["machine_id"], "machine_type": m.get("machine_type") or "Electric Motor",
            "active": bool(m.get("active", 1)), "data_mode": m.get("data_mode") or "SIMULATION",
            "rpm": m.get("rated_rpm") or 1500,
            "temperature_limit": m.get("temperature_limit") or 75,
            "vibration_limit": m.get("vibration_limit") or 4.5,
        } for m in stored]
    else:
        st.session_state.machines = create_initial_machines(3)
        for machine in st.session_state.machines:
            save_machine(machine)
if "ai_model" not in st.session_state:
    st.session_state.ai_model = PredictiveMaintenanceAI()
    st.session_state.ai_model.train_demo_model()
if "last_cycle" not in st.session_state:
    st.session_state.last_cycle = 0.0
if "operating_mode" not in st.session_state:
    st.session_state.operating_mode = "Simulation Mode"
if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False
if "simulation_speed" not in st.session_state:
    st.session_state.simulation_speed = 1
if "degradation" not in st.session_state:
    st.session_state.degradation = {m["machine_id"]: 0.0 for m in st.session_state.machines}
if "operating_hours" not in st.session_state:
    st.session_state.operating_hours = {m["machine_id"]: 500.0 for m in st.session_state.machines}

# --------------------------- Sidebar / controls ---------------------------
st.sidebar.markdown("# ⚙️ INDUSTRIAL AI")
st.sidebar.caption("PREDICTIVE MAINTENANCE CONTROL CENTER")
page = st.sidebar.radio("WORKSPACE", [
    "Overview Dashboard", "Machine Health Monitoring", "Vibration Analysis",
    "Temperature Monitoring", "RPM & Speed Monitoring", "AI Diagnostics",
    "Maintenance Alerts", "Maintenance History", "Analytics & Reports",
    "Animated Factory Digital Twin", "About Project", "Settings"
])
# Backward-compatible labels used by existing page render logic.
page_alias = {
    "Overview Dashboard": "Overview", "Machine Health Monitoring": "Machine Health",
    "RPM & Speed Monitoring": "RPM Monitoring", "Animated Factory Digital Twin": "Digital Twin"
}
page = page_alias.get(page, page)
if "settings_mode" not in st.session_state:
    st.session_state.settings_mode = st.session_state.operating_mode

def sync_settings_mode():
    st.session_state.operating_mode = st.session_state.settings_mode

st.sidebar.divider()
st.sidebar.markdown("#### MACHINE REGISTRY")
new_type = st.sidebar.selectbox("Equipment type", list(MACHINE_TYPES))
if st.sidebar.button("＋ Register machine", use_container_width=True):
    st.session_state.machines = add_machine(st.session_state.machines, new_type)
    save_machine(st.session_state.machines[-1])
    st.success(f"{st.session_state.machines[-1]['machine_id']} registered.")
    st.rerun()
st.sidebar.metric("REGISTERED MACHINES", len(st.session_state.machines))
st.sidebar.divider()
st.sidebar.markdown("#### OPERATING MODE")
if page == "Settings":
    mode_choice = st.session_state.operating_mode
    st.sidebar.caption(f"Selected: {mode_choice}")
else:
    mode_choice = st.sidebar.selectbox("Data source", ["Simulation Mode", "Real Hardware Mode"], key="operating_mode")
hardware_status = get_hardware_status()
if mode_choice == "Simulation Mode":
    st.sidebar.success("● SIMULATION ACTIVE")
    st.sidebar.markdown('<span class="source-pill">SIMULATION MODE — NOT CONNECTED TO REAL HARDWARE</span>', unsafe_allow_html=True)
    st.sidebar.caption("Every displayed reading is synthetic and stored in the simulation data store.")
else:
    st.sidebar.error("● HARDWARE DISCONNECTED")
    st.sidebar.caption(hardware_status.message)
    st.sidebar.caption("Real telemetry is blocked until a verified adapter is installed and validated.")
st.sidebar.divider()
st.sidebar.markdown("#### DATA ACQUISITION")
if mode_choice == "Simulation Mode":
    run_col, pause_col = st.sidebar.columns(2)
    if run_col.button("▶ Start", use_container_width=True):
        st.session_state.simulation_running = True
        st.rerun()
    if pause_col.button("Ⅱ Pause", use_container_width=True):
        st.session_state.simulation_running = False
        st.rerun()
    if st.sidebar.button("↺ Reset simulation", use_container_width=True):
        st.session_state.simulation_running = False
        st.session_state.active_faults = {}
        st.session_state.degradation = {m["machine_id"]: 0.0 for m in st.session_state.machines}
        st.session_state.operating_hours = {m["machine_id"]: 500.0 for m in st.session_state.machines}
        st.success("Simulation controls and degradation counters reset. Existing history is retained.")
    st.session_state.simulation_speed = st.sidebar.select_slider("Simulation speed", options=[1, 2, 5, 10], value=st.session_state.simulation_speed, format_func=lambda x: f"{x}×")
else:
    st.sidebar.info("Simulation generation is paused while Real Hardware Mode is selected.")
st.sidebar.caption("Simulation and real telemetry are kept in separate SQLite tables.")
st.sidebar.caption("Active scenarios: " + (", ".join(f"{k}: {v}" for k,v in st.session_state.get("active_faults", {}).items()) or "All normal"))
if "active_faults" not in st.session_state:
    st.session_state.active_faults = {}
fault_target = st.sidebar.selectbox("Fault target machine", [m["machine_id"] for m in st.session_state.machines], key="fault_target")
fault_mode = st.sidebar.selectbox("Fault scenario", [
    "Normal operation", "Bearing wear simulation", "Machine imbalance",
    "Shaft misalignment", "Overheating", "Excessive vibration", "Abnormal RPM"
], key="fault_selector")
fc1, fc2 = st.sidebar.columns(2)
if fc1.button("⚠ SIMULATE FAULT", use_container_width=True, disabled=(mode_choice != "Simulation Mode")):
    st.session_state.active_faults[fault_target] = fault_mode
    st.sidebar.warning(f"{fault_mode} enabled for {fault_target}. Generate a sensor cycle.")
if fc2.button("↺ Reset to Normal", use_container_width=True, disabled=(mode_choice != "Simulation Mode")):
    st.session_state.active_faults[fault_target] = "Normal operation"
    st.sidebar.success(f"{fault_target} reset. Generate a sensor cycle.")
refresh_seconds = st.sidebar.selectbox("Auto-cycle interval", ["Manual", "10 seconds", "30 seconds", "60 seconds"], index=1)
manual_cycle = st.sidebar.button("↻ Generate sensor cycle", use_container_width=True, disabled=(mode_choice != "Simulation Mode"))
auto_interval = None if refresh_seconds == "Manual" else max(1, int(int(refresh_seconds.split()[0]) / st.session_state.simulation_speed))
if mode_choice == "Simulation Mode" and st.session_state.simulation_running and auto_interval is not None:
    st_autorefresh(
    interval=auto_interval * 1000,
    key="simulation_refresh_main"
)
now_mono = time.monotonic()
should_cycle = mode_choice == "Simulation Mode" and (manual_cycle or (st.session_state.simulation_running and auto_interval is not None and now_mono - st.session_state.last_cycle >= auto_interval))
if should_cycle:
    for machine in st.session_state.machines:
        mid = machine["machine_id"]
        machine_fault = st.session_state.active_faults.get(mid, "Normal operation")
        st.session_state.degradation[mid] = min(100.0, st.session_state.degradation.get(mid, 0.0) + (0.08 * st.session_state.simulation_speed if machine_fault != "Normal operation" else 0.01 * st.session_state.simulation_speed))
        st.session_state.operating_hours[mid] = st.session_state.operating_hours.get(mid, 500.0) + (1.0 * st.session_state.simulation_speed)
        machine["operating_hours"] = st.session_state.operating_hours[mid]
        reading = generate_sensor_reading(mid, machine, fault_mode=machine_fault, degradation_pct=st.session_state.degradation[mid])
        health = evaluate_machine(reading["temperature"], reading["vibration"], machine["temperature_limit"], machine["vibration_limit"])
        reading["health_percentage"] = health["health_percentage"]
        reading["status"] = health["status"]
        ai = st.session_state.ai_model.predict(reading["temperature"], reading["vibration"], reading["rpm"], reading.get("machine_load", 68), reading.get("current_amp", 3.8), reading.get("voltage", 400))
        reading["anomaly_score"] = ai["anomaly_score"]
        reading["risk_level"] = ai["risk_level"]
        save_sensor_reading(reading)
        alerts = evaluate_alerts(reading, ai, machine["temperature_limit"], machine["vibration_limit"], rated_rpm=machine["rpm"])
        save_alerts(mid, alerts, "SIMULATION")
    st.session_state.last_cycle = now_mono
    if manual_cycle:
        st.sidebar.success("Simulation sensor cycle stored.")
    if st.session_state.simulation_running and auto_interval is not None:
        st_autorefresh(
    interval=auto_interval * 1000,
    key="simulation_refresh_secondary"
)
        st.rerun()

# Never display synthetic values while hardware mode is selected.
latest = {r["machine_id"]: r for r in get_latest_readings(data_mode="SIMULATION")} if mode_choice == "Simulation Mode" else {}

def plot_layout(fig, height=330):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(8,17,30,.35)",
                      font_color="#dbe9f7", height=height, margin=dict(l=15,r=15,t=45,b=15),
                      legend=dict(orientation="h", y=1.12))
    fig.update_xaxes(gridcolor="#23384f", zerolinecolor="#23384f")
    fig.update_yaxes(gridcolor="#23384f", zerolinecolor="#23384f")
    return fig

def build_pdf_report(frame):
    """Build a compact PDF snapshot from saved simulation history."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title="Predictive Maintenance Simulation Report")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Industrial Predictive Maintenance — Simulation Report", styles["Title"]),
        Paragraph("SIMULATION MODE — NOT CONNECTED TO REAL HARDWARE", styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
        Spacer(1, 12),
    ]
    cols = [c for c in ["timestamp","machine_id","temperature","vibration","rpm","health_percentage","anomaly_score","risk_level","status","fault_mode"] if c in frame.columns]
    view = frame[cols].tail(35).fillna("—")
    data = [cols] + view.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173653")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#9aabba")),
        ("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#edf3f8")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("This report summarizes synthetic demonstration data. Anomaly flags are not verified faults, failure probabilities or remaining-useful-life estimates.", styles["Italic"]))
    doc.build(story)
    return buffer.getvalue()

def render_factory_twin():
    """Animated equipment digital twin; telemetry labels use stored SIMULATION samples."""
    samples = list(latest.values())
    avg_rpm = int(np.mean([r.get("rpm", 0) for r in samples])) if samples else 0
    avg_temp = float(np.mean([r.get("temperature", 0) for r in samples])) if samples else 0.0
    machine_count = len(st.session_state.machines)
    status_text = f"{machine_count} ASSETS · {len(samples)} WITH DATA"
    html = f"""<section class='twin-panel'>
    <div class='twin-head'><div><div class='twin-label'>ANIMATED EQUIPMENT DIGITAL TWIN</div>
    <div style='font-size:1.08rem;font-weight:800;color:#edf6ff'>Rotating machinery line</div></div>
    <span class='source-pill'>SIMULATION VISUALIZATION</span></div>
    <div class='machine-stage'>
    <svg class='twin-svg machine-svg' viewBox='0 0 1100 360' role='img' aria-label='Animated 3D-style electric motor connected by rotating shaft to fan, pump and transparent gearbox'>
      <defs>
        <linearGradient id='steel' x2='0' y2='1'><stop stop-color='#a9c8dc'/><stop offset='.22' stop-color='#456d8d'/><stop offset='.55' stop-color='#183a59'/><stop offset='1' stop-color='#071a2c'/></linearGradient>
        <linearGradient id='blueMetal' x2='.15' y2='1'><stop stop-color='#68d9ff'/><stop offset='.18' stop-color='#167fc5'/><stop offset='.58' stop-color='#07508e'/><stop offset='1' stop-color='#062b50'/></linearGradient>
        <linearGradient id='darkMetal' x2='0' y2='1'><stop stop-color='#52738c'/><stop offset='.45' stop-color='#203c54'/><stop offset='1' stop-color='#0a1b2b'/></linearGradient>
        <linearGradient id='glass' x2='1' y2='1'><stop stop-color='#b5eaff' stop-opacity='.45'/><stop offset='.5' stop-color='#1d6e9d' stop-opacity='.12'/><stop offset='1' stop-color='#72dfff' stop-opacity='.3'/></linearGradient>
        <radialGradient id='glow'><stop stop-color='#42dfff' stop-opacity='.65'/><stop offset='1' stop-color='#0b83c9' stop-opacity='0'/></radialGradient>
        <filter id='softGlow' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='5' result='b'/><feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge></filter>
      </defs>
      <ellipse cx='540' cy='303' rx='485' ry='31' fill='#020b15' opacity='.8'/>
      <path d='M55 300H1050' stroke='#2c668b' stroke-width='3'/><path d='M70 309H1030' stroke='#1b3c59' stroke-width='8'/>
      <!-- motor base and feet -->
      <g><path d='M85 260L360 260L382 294L65 294Z' fill='url(#darkMetal)' stroke='#5a86a5' stroke-width='2'/>
      <path d='M105 284L135 284L125 310L95 310Z M315 284L345 284L355 310L325 310Z' fill='#274b68' stroke='#6c9ab8'/>
      <!-- motor body -->
      <path d='M95 115Q95 91 124 82L310 82Q344 92 355 123L355 229Q345 259 315 268L125 268Q95 256 95 229Z' fill='url(#blueMetal)' stroke='#79dfff' stroke-width='3'/>
      <path d='M112 117Q112 101 135 96H302Q330 104 337 128V224Q328 247 302 252H135Q112 244 112 222Z' fill='#0a3b68' stroke='#2ba9e8' stroke-width='2'/>
      <g stroke='#77c9f3' stroke-width='5' opacity='.65'><path d='M142 102V247M158 99V250M174 98V251M190 97V252M206 97V252M222 97V252M238 97V252M254 97V252M270 98V251M286 99V250'/></g>
      <path d='M150 72L168 49H274L294 72Z' fill='url(#steel)' stroke='#7eb4d3' stroke-width='2'/><rect x='176' y='35' width='94' height='26' rx='7' fill='url(#darkMetal)' stroke='#8dbbd5'/>
      <path d='M355 137Q382 145 382 177V201Q379 230 355 238Z' fill='url(#steel)' stroke='#8ddcff' stroke-width='3'/>
      <ellipse cx='365' cy='187' rx='14' ry='50' fill='#061c30' stroke='#65c9f5' stroke-width='4'/>
      <text x='225' y='337' fill='#cceaff' font-size='17' font-weight='700' text-anchor='middle'>ELECTRIC MOTOR</text>
      <text x='225' y='355' fill='#6fcfff' font-size='12' text-anchor='middle'>{avg_rpm:,} RPM AVG</text></g>
      <!-- shaft with rotating highlight -->
      <g><rect x='365' y='178' width='590' height='18' rx='8' fill='url(#steel)' stroke='#a7d9f5' stroke-width='1.5'/>
      <path class='shaft-highlight' d='M370 183H950' stroke='#8eeaff' stroke-width='3' stroke-dasharray='18 24' filter='url(#softGlow)'/></g>
      <!-- fan housing and rotor -->
      <g transform='translate(470 187)'><ellipse rx='57' ry='75' fill='url(#darkMetal)' stroke='#75bce2' stroke-width='4'/><ellipse rx='44' ry='61' fill='#09263e' stroke='#2f8ab9' stroke-width='3'/>
      <g class='spin fan-spin'><path d='M0 -8C-13 -60 14 -65 22 -38L9 -4Z' fill='#65d9ff' stroke='#b3efff'/><path d='M8 0C60 -13 65 14 38 22L4 9Z' fill='#65d9ff' stroke='#b3efff'/><path d='M0 8C13 60 -14 65 -22 38L-9 4Z' fill='#65d9ff' stroke='#b3efff'/><path d='M-8 0C-60 13 -65 -14 -38 -22L-4 -9Z' fill='#65d9ff' stroke='#b3efff'/></g><circle r='12' fill='#d5f6ff' stroke='#3aa9dc' stroke-width='5'/><text y='105' fill='#cceaff' font-size='16' font-weight='700' text-anchor='middle'>COOLING FAN</text></g>
      <!-- pump casing + impeller -->
      <g transform='translate(700 187)'><path d='M-72 -50Q-52 -78 0 -70Q66 -65 76 -8L73 42Q48 74 -12 69Q-67 63 -78 12Z' fill='url(#blueMetal)' stroke='#8ddcff' stroke-width='3'/><path d='M-18 -70V-104H23V-70M-18 -104H23' fill='url(#steel)' stroke='#8ddcff' stroke-width='3'/><path d='M-74 0H-99V34H-72' fill='url(#steel)' stroke='#8ddcff' stroke-width='3'/><circle r='42' fill='#08253d' stroke='#6cccf2' stroke-width='4'/><g class='spin pump-spin'><path d='M0 -6C-10 -40 12 -45 20 -20L6 -3Z M6 0C40 -10 45 12 20 20L3 6Z M0 6C10 40 -12 45 -20 20L-6 3Z M-6 0C-40 10 -45 -12 -20 -20L-3 -6Z' fill='#8ce8ff'/></g><circle r='10' fill='#dff8ff'/><text y='105' fill='#cceaff' font-size='16' font-weight='700' text-anchor='middle'>PROCESS PUMP</text></g>
      <!-- see-through gearbox -->
      <g transform='translate(935 187)'><path d='M-83 -80L62 -80L88 -52V63L62 84H-83L-100 62V-58Z' fill='url(#glass)' stroke='#8ddcff' stroke-width='4'/><path d='M-72 -65H53L72 -46V48L53 67H-72Z' fill='#0b2941' fill-opacity='.65' stroke='#4d9fc9' stroke-width='2'/>
      <g class='spin gear-large'><circle r='43' fill='none' stroke='#e1a94e' stroke-width='12' stroke-dasharray='8 5'/><circle r='24' fill='#244b66' stroke='#ffcf78' stroke-width='3'/><path d='M0 -36V-20M0 20V36M-36 0H-20M20 0H36M-25 -25L-14 -14M14 14L25 25M25 -25L14 -14M-14 14L-25 25' stroke='#ffd68c' stroke-width='5'/></g>
      <g class='spin-reverse gear-small'><circle cx='48' cy='-37' r='24' fill='none' stroke='#79dfff' stroke-width='9' stroke-dasharray='6 4'/><circle cx='48' cy='-37' r='9' fill='#bceeff'/></g>
      <text y='116' fill='#cceaff' font-size='16' font-weight='700' text-anchor='middle'>GEARBOX</text></g>
      <!-- sensor/data stream -->
      <path class='data-flow' d='M105 25H1020' stroke='#2bc9f4' stroke-width='2' fill='none' stroke-dasharray='7 13'/>
      <g fill='#5de2ff' filter='url(#softGlow)'><circle class='sensor-pulse' cx='225' cy='25' r='6'/><circle class='sensor-pulse delay-1' cx='470' cy='25' r='6'/><circle class='sensor-pulse delay-2' cx='700' cy='25' r='6'/><circle class='sensor-pulse delay-3' cx='935' cy='25' r='6'/></g>
      <g fill='#a9d5ef' font-size='12' text-anchor='middle'><text x='225' y='15'>TEMP / RPM</text><text x='470' y='15'>AIRFLOW</text><text x='700' y='15'>PRESSURE</text><text x='935' y='15'>TORQUE / VIBRATION</text></g>
    </svg></div>
    <div class='twin-stats'><span><b>●</b> {status_text}</span><span>AVG SPEED <strong>{avg_rpm:,} RPM</strong></span><span>AVG TEMP <strong>{avg_temp:.1f} °C</strong></span><span class='sim-note'>SIMULATED TELEMETRY · NOT CONNECTED TO HARDWARE</span></div>
    </section>"""
    st.markdown(html, unsafe_allow_html=True)

def render_live_waveform():
    st.markdown("<div class='wave-live'><svg viewBox='0 0 800 70' preserveAspectRatio='none'><path d='M0 35H800' stroke='#28465f'/><path class='wave-path' d='M0 35 L15 35 25 10 35 60 45 35 65 35 80 18 92 52 104 35 130 35 145 5 157 64 170 35 195 35 210 21 222 49 235 35 260 35 275 12 287 58 300 35 325 35 340 18 352 51 365 35 390 35 405 7 417 63 430 35 455 35 470 20 482 50 495 35 520 35 535 11 547 59 560 35 585 35 600 17 612 53 625 35 650 35 665 8 677 62 690 35 715 35 730 18 742 52 755 35 780 35 800 35'/></svg></div>", unsafe_allow_html=True)

def render_temperature_bar(value, warning, critical):
    pct=max(0,min(100,value/max(critical,1)*100)); color='#31c48d' if value<warning else '#f6b84a' if value<critical else '#f36b72'; label='NORMAL' if value<warning else 'WARNING' if value<critical else 'CRITICAL'
    st.markdown(f"<div style='display:flex;justify-content:space-between;color:#9db4ca;font-size:.78rem'><span>THERMAL LOAD · {label}</span><span>{value:.1f} °C</span></div><div class='temp-track'><div class='temp-fill' style='width:{pct:.1f}%;background:{color};color:{color}'></div></div>",unsafe_allow_html=True)

def health_for(machine, reading):
    return evaluate_machine(reading["temperature"], reading["vibration"], machine["temperature_limit"], machine["vibration_limit"])

def selected_machine_data():
    available = [m for m in st.session_state.machines if m["machine_id"] in latest]
    if not available:
        return None, None
    chosen = st.selectbox("Select equipment", [m["machine_id"] for m in available], key=f"machine_select_{page}")
    machine = next(m for m in available if m["machine_id"] == chosen)
    return machine, latest[chosen]

def render_machine_cards():
    cols = st.columns(2)
    for idx, machine in enumerate(st.session_state.machines):
        reading = latest.get(machine["machine_id"])
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f'<div class="eyebrow">{machine["machine_type"]} · {machine["machine_id"]}</div>', unsafe_allow_html=True)
                if not reading:
                    st.info("Hardware is disconnected; no real telemetry is available." if mode_choice == "Real Hardware Mode" else "No simulation sample yet. Generate a sensor cycle from the sidebar.")
                    continue
                h = health_for(machine, reading)
                status = h["status"]
                dot = "dot-green" if status == "RUNNING" else "dot-amber" if status == "WARNING" else "dot-red"
                st.markdown(f'<div class="machine-title"><span class="status-dot {dot}"></span>{status} <span style="float:right;color:#35c8e8">{h["health_percentage"]:.0f}% HEALTH</span></div>', unsafe_allow_html=True)
                st.progress(h["health_percentage"] / 100)
                a,b,c = st.columns(3)
                a.metric("TEMPERATURE", f"{reading['temperature']:.1f} °C")
                b.metric("VIBRATION", f"{reading['vibration']:.2f} mm/s")
                c.metric("SPEED", f"{reading['rpm']:,} RPM")
                st.caption(f"Source: {reading.get('data_mode','UNKNOWN')} · Sample: {reading.get('timestamp','—')[:19].replace('T',' ')} UTC")

# --------------------------- Header ---------------------------
st.markdown('<div class="eyebrow">ASSET RELIABILITY / CONDITION MONITORING</div>', unsafe_allow_html=True)
st.title("Industrial Predictive Maintenance")
if mode_choice == "Simulation Mode":
    st.markdown("<span class='source-pill'>SIMULATION MODE — NOT CONNECTED TO REAL HARDWARE</span>", unsafe_allow_html=True)
    st.warning("SIMULATION MODE — NOT CONNECTED TO REAL HARDWARE", icon="⚠️")
else:
    st.error("REAL HARDWARE MODE REQUESTED — HARDWARE DISCONNECTED · NO REAL READINGS AVAILABLE", icon="🔌")
st.caption(f"Workspace: {page}  ·  Operating mode: {mode_choice}  ·  Last UI update: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}")

if page in ("Overview", "Machine Health"):
    readings = [(m, latest.get(m["machine_id"])) for m in st.session_state.machines]
    readings = [(m,r) for m,r in readings if r]
    statuses = [health_for(m,r)["status"] for m,r in readings]
    avg_health = np.mean([health_for(m,r)["health_percentage"] for m,r in readings]) if readings else 0
    active_alerts = get_alert_history(1000, unresolved_only=True, data_mode="SIMULATION")
    critical_count = sum(a["severity"] == "CRITICAL" for a in active_alerts)
    warning_count = sum(a["severity"] == "WARNING" for a in active_alerts)
    k = st.columns(5)
    k[0].metric("ASSETS", len(st.session_state.machines))
    k[1].metric("RUNNING", statuses.count("RUNNING"))
    k[2].metric("WARNING", statuses.count("WARNING"))
    k[3].metric("CRITICAL", statuses.count("CRITICAL"))
    k[4].metric("AVG HEALTH", f"{avg_health:.1f}%")
    st.divider()
    st.subheader("Equipment fleet")
    render_factory_twin()
    if not latest:
        if mode_choice == "Simulation Mode":
            st.info("No stored sensor readings yet. Use **Generate sensor cycle** in the sidebar to create the first clearly labelled simulation sample.")
        else:
            st.error("Hardware disconnected. No real readings are available; simulated readings are intentionally hidden in this mode.")
    render_machine_cards()
    if readings:
        st.divider()
        st.subheader("Fleet condition profile")
        fleet = pd.DataFrame([{"Machine":m["machine_id"],"Health":health_for(m,r)["health_percentage"],"Temperature":r["temperature"],"Vibration":r["vibration"]} for m,r in readings])
        f1,f2 = st.columns(2)
        with f1:
            fig = px.bar(fleet, x="Machine", y="Health", color="Health", range_y=[0,100], title="Machine health index (%)", color_continuous_scale=["#e45d66","#e7ad45","#2bc58b"])
            st.plotly_chart(plot_layout(fig,300), use_container_width=True)
        with f2:
            fig = px.scatter(fleet, x="Temperature", y="Vibration", color="Machine", size="Health", title="Temperature vs vibration condition map")
            st.plotly_chart(plot_layout(fig,300), use_container_width=True)

elif page == "Vibration Analysis":
    st.subheader("Vibration diagnostics")
    machine, reading = selected_machine_data()
    if machine:
        fault = reading["vibration"] >= machine["vibration_limit"]
        t, sig = generate_vibration_signal(fault_mode=fault, seed=17)
        # Scale synthetic waveform to the machine's latest synthetic sensor amplitude.
        sig = sig - np.mean(sig)
        current_rms = float(np.sqrt(np.mean(sig**2))) or 1
        sig = sig * (float(reading["vibration"]) / current_rms)
        result = analyze_vibration(sig, sampling_rate=2000, warning_rms=machine["vibration_limit"], critical_rms=machine["vibration_limit"]*1.5)
        st.caption(f"{machine['machine_id']} · {reading['data_mode']} waveform generated for demonstration; not a measured accelerometer trace.")
        render_live_waveform()
        q = st.columns(4)
        q[0].metric("RMS", f"{result['rms']:.2f} mm/s")
        q[1].metric("PEAK", f"{result['peak']:.2f} mm/s")
        q[2].metric("CREST FACTOR", f"{result['crest_factor']:.2f}")
        q[3].metric("DOMINANT", f"{result['dominant_frequency']:.1f} Hz")
        left,right = st.columns(2)
        with left:
            fig = px.line(x=t, y=sig, labels={"x":"Time (s)","y":"Velocity (mm/s)"}, title="Synthetic vibration waveform")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        with right:
            fig = px.line(x=result["frequencies"], y=result["spectrum"], labels={"x":"Frequency (Hz)","y":"Amplitude (mm/s)"}, title="FFT frequency spectrum")
            fig.update_xaxes(range=[0,300])
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        st.info(f"Signal condition: **{result['status']}** · Frequency peaks: {', '.join(map(str,result['significant_frequencies'][:8])) or 'None detected'}")
        st.caption("RMS thresholds are illustrative configuration values. Industrial acceptance limits depend on machine class, mounting, speed and applicable standards.")
    else:
        st.info("Hardware disconnected; no real vibration data is available." if mode_choice == "Real Hardware Mode" else "Generate a sensor cycle to begin vibration analysis.")

elif page == "Temperature Monitoring":
    st.subheader("Thermal condition monitoring")
    machine, reading = selected_machine_data()
    if machine:
        limit = float(machine["temperature_limit"])
        critical = limit * 1.2
        result = evaluate_temperature(reading["temperature"], limit, critical)
        a,b = st.columns([1,2])
        with a:
            render_temperature_bar(float(reading["temperature"]), limit, critical)
            fig = go.Figure(go.Indicator(mode="gauge+number", value=reading["temperature"], number={"suffix":" °C"}, title={"text":"Latest simulated temperature"}, gauge={"axis":{"range":[0,max(120,critical+10)]},"bar":{"color":"#f6b84a"},"steps":[{"range":[0,limit],"color":"#174c43"},{"range":[limit,critical],"color":"#72521f"},{"range":[critical,max(120,critical+10)],"color":"#702d38"}],"threshold":{"line":{"color":"#ff6672","width":4},"value":critical}}))
            st.plotly_chart(plot_layout(fig,340), use_container_width=True)
            st.metric("Configured warning limit", f"{limit:.1f} °C")
            st.metric("Thermal state", result["status"])
        with b:
            hist = get_recent_readings(machine["machine_id"], 150, data_mode=reading.get("data_mode"))
            df = pd.DataFrame(hist)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                fig = px.line(df, x="timestamp", y="temperature", title="Stored temperature trend", markers=True)
                fig.add_hline(y=limit, line_dash="dash", line_color="#f6b84a", annotation_text="Warning limit")
                fig.add_hline(y=critical, line_dash="dot", line_color="#f36b72", annotation_text="Critical guide")
                st.plotly_chart(plot_layout(fig,340), use_container_width=True)
            st.info(result["recommended_action"])
            st.caption("Only saved samples are plotted. No synthetic history is silently backfilled.")
    else:
        st.info("Hardware disconnected; no real temperature data is available." if mode_choice == "Real Hardware Mode" else "Generate a sensor cycle to begin temperature monitoring.")

elif page == "AI Diagnostics":
    st.subheader("AI anomaly detection")
    st.warning("Demonstration AI only: Isolation Forest is trained on synthetic baseline data by default. It is not validated for industrial failure prediction, remaining useful life (RUL), or safety decisions.")
    machine, reading = selected_machine_data()
    if machine:
        ai = st.session_state.ai_model.predict(reading["temperature"], reading["vibration"], reading["rpm"], reading.get("machine_load", 68), reading.get("current_amp", 3.8), reading.get("voltage", 400))
        a,b,c = st.columns(3)
        a.metric("Risk classification", ai["risk_level"])
        b.metric("Anomaly flagged", "YES" if ai["anomaly_detected"] else "NO")
        c.metric("Decision score", f"{ai['anomaly_score']:.4f}")
        st.info(ai["recommended_action"])
        st.markdown("**Sensor contribution guide** · distance from synthetic baseline (not causal attribution)")
        contrib = pd.DataFrame(ai.get("sensor_contributions", []))
        if not contrib.empty:
            st.dataframe(contrib.rename(columns={"feature":"Sensor","standardized_deviation":"Baseline deviation (σ)"}), use_container_width=True, hide_index=True)
        st.write("**Model:**", ai["model_type"], "  ·  **Training source:**", ai["training_source"])
        st.caption("A negative decision score is more anomalous relative to this model's fitted baseline. It is not a probability of failure.")
        if st.button("Retrain demo baseline"):
            st.session_state.ai_model = PredictiveMaintenanceAI()
            st.session_state.ai_model.train_demo_model()
            st.success("Synthetic demonstration baseline retrained.")

elif page == "Maintenance Alerts":
    st.subheader("Alarm and event management")
    alerts = get_alert_history(500, data_mode="SIMULATION" if mode_choice == "Simulation Mode" else "REAL")
    if not alerts:
        st.success("No alert records. Alerts are created when a sensor cycle is generated.")
    else:
        for alert in alerts:
            severity = alert["severity"]
            with st.container(border=True):
                x,y = st.columns([4,1])
                with x:
                    st.markdown(f"**{alert['machine_id']} · {severity}** — {alert['problem']}")
                    st.caption(f"{alert['timestamp']} · Source: {alert.get('data_mode') or 'LEGACY/UNKNOWN'} · " + ("Resolved" if alert.get("resolved_at") else "Acknowledged" if alert.get("acknowledged_at") else "Active"))
                    st.write(alert["recommended_action"])
                with y:
                    if not alert.get("resolved_at"):
                        if not alert.get("acknowledged_at") and st.button("Acknowledge", key=f"ack_{alert['id']}"):
                            update_alert(alert["id"], "acknowledge")
                            st.rerun()
                        if st.button("Resolve", key=f"resolve_{alert['id']}"):
                            update_alert(alert["id"], "resolve")
                            st.rerun()

elif page == "Maintenance History":
    st.subheader("Maintenance work orders and service history")
    machines = [m["machine_id"] for m in st.session_state.machines]
    with st.form("maintenance_form", clear_on_submit=True):
        c1,c2 = st.columns(2)
        machine_id = c1.selectbox("Machine", machines)
        maintenance_type = c2.selectbox("Maintenance type", ["Inspection", "Preventive maintenance", "Corrective repair", "Lubrication", "Bearing replacement", "Calibration", "Other"])
        description = st.text_area("Work performed / observations", placeholder="Describe findings, parts replaced and work completed...")
        c3,c4,c5 = st.columns(3)
        performed_date = c3.date_input("Maintenance date", value=date.today())
        performed_by = c4.text_input("Technician / team")
        cost = c5.number_input("Cost (optional)", min_value=0.0, value=0.0, step=100.0)
        next_due = st.date_input("Next due date (optional)", value=None)
        submitted = st.form_submit_button("＋ Save maintenance record")
        if submitted:
            if not description.strip():
                st.error("Add a short description before saving.")
            else:
                add_maintenance_record(machine_id, maintenance_type, description.strip(), performed_date.isoformat(), performed_by.strip(), cost if cost else None, next_due.isoformat() if next_due else None)
                st.success("Maintenance record saved.")
                st.rerun()
    history = get_maintenance_history()
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No maintenance records have been entered yet. Existing maintenance table was preserved.")

elif page == "Analytics & Reports":
    st.subheader("Condition analytics and export")
    machine_ids = [m["machine_id"] for m in st.session_state.machines]
    chosen = st.multiselect("Machines", machine_ids, default=machine_ids)
    rows = []
    for mid in chosen:
        rows.extend(get_recent_readings(mid, 1000, data_mode="SIMULATION" if mode_choice == "Simulation Mode" else "REAL"))
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
        f1,f2 = st.columns(2)
        with f1:
            fig = px.line(df, x="timestamp", y="temperature", color="machine_id", title="Temperature history (°C)")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        with f2:
            fig = px.line(df, x="timestamp", y="vibration", color="machine_id", title="Vibration history (mm/s)")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        if "rpm" in df.columns:
            fig = px.line(df, x="timestamp", y="rpm", color="machine_id", title="RPM / speed history")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        if "health_percentage" in df.columns and df["health_percentage"].notna().any():
            fig = px.line(df, x="timestamp", y="health_percentage", color="machine_id", title="Illustrative machine health trend (%)")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        if "anomaly_score" in df.columns and df["anomaly_score"].notna().any():
            fig = px.scatter(df, x="timestamp", y="anomaly_score", color="risk_level", title="Isolation Forest decision score (not failure probability)")
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        st.download_button("Download sensor history CSV", df.to_csv(index=False).encode("utf-8"), "sensor_history.csv", "text/csv")
        st.download_button("Download PDF report", build_pdf_report(df), "predictive_maintenance_report.pdf", "application/pdf")
        st.dataframe(df.tail(30), use_container_width=True, hide_index=True)
        maintenance_df = pd.DataFrame(get_maintenance_history())
        if not maintenance_df.empty and "cost" in maintenance_df.columns:
            st.metric("Recorded maintenance cost (manual entries)", f"₹{pd.to_numeric(maintenance_df['cost'], errors='coerce').fillna(0).sum():,.0f}")
        else:
            st.caption("Maintenance cost overview: no manual maintenance costs recorded yet.")
    else:
        st.info("No saved sensor history for the selected assets. Generate sensor cycles to populate analytics.")

elif page == "RPM Monitoring":
    st.subheader("RPM & speed monitoring")
    machine, reading = selected_machine_data()
    if machine:
        rated = float(machine["rpm"])
        rpm = float(reading["rpm"])
        low, high = rated * 0.85, rated * 1.10
        status = "NORMAL" if low <= rpm <= high else "WARNING"
        gauge = go.Figure(go.Indicator(mode="gauge+number", value=rpm, number={"suffix":" RPM"},
            title={"text":f"{machine['machine_type']} · simulated speed"},
            gauge={"axis":{"range":[0,max(rated*1.25, rpm*1.15, 100)]},
                   "bar":{"color":"#35c8e8"},
                   "steps":[{"range":[0,low],"color":"#5a2b35"},{"range":[low,high],"color":"#174c43"},{"range":[high,max(rated*1.25,rpm*1.15,100)],"color":"#72521f"}]}))
        a,b,c=st.columns(3)
        a.metric("CURRENT SPEED",f"{rpm:,.0f} RPM")
        b.metric("RATED SPEED",f"{rated:,.0f} RPM")
        c.metric("SPEED STATE",status)
        st.plotly_chart(plot_layout(gauge,330),use_container_width=True)
        hist=pd.DataFrame(get_recent_readings(machine["machine_id"],150,data_mode=reading.get("data_mode")))
        if not hist.empty:
            hist["timestamp"]=pd.to_datetime(hist["timestamp"],errors="coerce")
            fig=px.line(hist,x="timestamp",y="rpm",title="Stored RPM trend",markers=True)
            fig.add_hline(y=low,line_dash="dash",line_color="#f6b84a",annotation_text="Low guide")
            fig.add_hline(y=high,line_dash="dash",line_color="#31c48d",annotation_text="High guide")
            st.plotly_chart(plot_layout(fig),use_container_width=True)
        st.caption("RPM limits are illustrative guides based on configured rated speed, not certified operating limits.")
    else:
        st.info("Hardware disconnected; no real RPM data is available." if mode_choice == "Real Hardware Mode" else "Generate a sensor cycle to begin RPM monitoring.")

elif page == "Digital Twin":
    st.subheader("Animated factory digital twin")
    render_factory_twin()
    st.caption("Rotating SVG equipment and data-flow paths are illustrative simulation visuals; they do not represent connected machinery.")
    render_machine_cards()

elif page == "About Project":
    st.subheader("AI-Based Industrial Predictive Maintenance Software")
    st.markdown("""
This software is a simulation-based industrial condition-monitoring prototype designed to track machine health and flag unusual operating behaviour for earlier inspection planning.

**Example:** If one motor in a factory fleet begins showing unusual vibration or temperature readings, the system highlights the abnormal pattern and creates a maintenance alert so a technician can investigate before a potential breakdown.

**Applications:** automobile manufacturing, CNC machining, textile plants, power generation, oil and gas, food processing, packaging, pumps, motors, compressors, fans and general manufacturing.

**Benefits:** earlier visibility of abnormal trends, reduced unplanned downtime risk, more informed maintenance planning and fleet monitoring from one workspace.

**Future scope:** validated sensor integration through industrial gateways and protocols such as Modbus TCP, MQTT or OPC UA, after calibration, cybersecurity and site testing.
""")
    st.info("Simulation-only prototype. Anomaly flags are not confirmed faults, failure probabilities or remaining-useful-life estimates.")

elif page == "Settings":
    st.subheader("System configuration")
    st.markdown("#### Equipment thresholds")
    for machine in st.session_state.machines:
        with st.expander(f"{machine['machine_id']} · {machine['machine_type']}"):
            with st.form(f"limits_{machine['machine_id']}"):
                tlim = st.number_input("Temperature warning limit (°C)", min_value=10.0, max_value=200.0, value=float(machine["temperature_limit"]), key=f"t_{machine['machine_id']}")
                vlim = st.number_input("Vibration warning limit (mm/s)", min_value=.1, max_value=50.0, value=float(machine["vibration_limit"]), key=f"v_{machine['machine_id']}")
                if st.form_submit_button("Save equipment limits"):
                    machine["temperature_limit"] = tlim
                    machine["vibration_limit"] = vlim
                    save_machine(machine)
                    st.success("Equipment limits updated.")
    st.divider()
    st.markdown("#### Operating mode and sensor integration")
    st.selectbox("Operating mode", ["Simulation Mode", "Real Hardware Mode"], key="settings_mode", on_change=sync_settings_mode)
    st.write("Selected mode:", st.session_state.operating_mode)
    if st.session_state.operating_mode == "Simulation Mode":
        st.success("SIMULATION ACTIVE — all displayed readings are synthetic and stored separately.")
    else:
        st.error("HARDWARE DISCONNECTED — Real mode is safely locked because no verified adapter is configured.")
    st.write("Connection status:", hardware_status.status)
    st.write("Supported future integration targets:", ", ".join(SUPPORTED_INTEGRATIONS))
    st.info("Hardware mode cannot ingest or display data until a real adapter verifies endpoint identity, connection, units, timestamps, calibration and data quality. No motor control, emergency stop or machine trip outputs are implemented.")
    st.write("Simulation running:", st.session_state.simulation_running)
    st.write("Simulation speed:", f"{st.session_state.simulation_speed}×")
    st.write("Database file:", "`data/maintenance.db`")
    st.write("Registered assets:", len(st.session_state.machines))
    st.write("AI baseline:", st.session_state.ai_model.training_source)
    st.caption("REAL sensor readings, when a verified adapter is implemented, will be stored in the separate real_sensor_readings table. No simulated value is copied into that table.")

st.divider()
st.caption("INDUSTRIAL PREDICTIVE MAINTENANCE · DEMONSTRATION BUILD · SIMULATED SENSOR DATA · NOT FOR SAFETY-CRITICAL CONTROL")
