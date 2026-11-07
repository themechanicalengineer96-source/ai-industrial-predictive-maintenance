"""SQLite persistence with additive migrations; existing records are retained."""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_ROOT / "data"
DB_PATH = DATA_FOLDER / "maintenance.db"


def get_connection():
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def _add_column(conn, table, definition):
    name = definition.split()[0]

    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})")
    }

    if name in existing:
        return

    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error).lower():
            raise


def initialize_database():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS machines (
            machine_id TEXT PRIMARY KEY, created_at TEXT, active INTEGER DEFAULT 1,
            data_mode TEXT DEFAULT 'SIMULATION')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
            temperature REAL, vibration REAL, rpm INTEGER, operating_hours REAL,
            status TEXT, data_mode TEXT, timestamp TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT, severity TEXT,
            problem TEXT, recommended_action TEXT, timestamp TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS maintenance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT,
            maintenance_type TEXT, description TEXT, maintenance_date TEXT)""")
        # Additive schema evolution: never drop or recreate the user's tables.
        for definition in (
            "machine_type TEXT DEFAULT 'Electric Motor'",
            "rated_rpm INTEGER DEFAULT 1500",
            "temperature_limit REAL DEFAULT 75",
            "vibration_limit REAL DEFAULT 4.5",
        ):
            _add_column(conn, "machines", definition)
        for definition in ("acknowledged_at TEXT", "resolved_at TEXT", "dedupe_key TEXT", "data_mode TEXT DEFAULT 'LEGACY/UNKNOWN'"):
            _add_column(conn, "alerts", definition)
        for definition in ("anomaly_score REAL", "risk_level TEXT", "fault_mode TEXT", "health_percentage REAL"):
            _add_column(conn, "sensor_readings", definition)
        for definition in ("performed_by TEXT", "cost REAL", "next_due_date TEXT", "data_mode TEXT DEFAULT 'LEGACY/UNKNOWN'"):
            _add_column(conn, "maintenance_history", definition)
        # Keep REAL telemetry physically separate from SIMULATION telemetry.
        conn.execute("""CREATE TABLE IF NOT EXISTS real_sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
            temperature REAL, vibration REAL, rpm INTEGER, operating_hours REAL,
            status TEXT, timestamp TEXT NOT NULL, source_id TEXT NOT NULL,
            current_amp REAL, voltage REAL, machine_load REAL, quality_status TEXT DEFAULT 'UNVERIFIED'
        )""")
        # Additive fields for richer simulation telemetry; existing rows remain untouched.
        for definition in ("machine_load REAL", "current_amp REAL", "voltage REAL", "degradation_pct REAL"):
            _add_column(conn, "sensor_readings", definition)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_real_readings_machine_time ON real_sensor_readings(machine_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_machine_time ON sensor_readings(machine_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_machine_state ON alerts(machine_id, resolved_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_machine_date ON maintenance_history(machine_id, maintenance_date)")


def save_machine(machine):
    with get_connection() as conn:
        conn.execute("""INSERT INTO machines
            (machine_id, created_at, active, data_mode, machine_type, rated_rpm, temperature_limit, vibration_limit)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            ON CONFLICT(machine_id) DO UPDATE SET active=excluded.active,
            machine_type=excluded.machine_type, rated_rpm=excluded.rated_rpm,
            temperature_limit=excluded.temperature_limit, vibration_limit=excluded.vibration_limit""",
            (machine["machine_id"], int(machine.get("active", True)), machine.get("data_mode", "SIMULATION"),
             machine.get("machine_type", "Electric Motor"), machine.get("rpm", 1500),
             machine.get("temperature_limit", 75), machine.get("vibration_limit", 4.5)))


def get_machines(active_only=True):
    query = "SELECT * FROM machines" + (" WHERE active=1" if active_only else "") + " ORDER BY machine_id"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def save_sensor_reading(reading):
    required = ("machine_id", "temperature", "vibration", "rpm", "operating_hours", "status", "data_mode", "timestamp")
    if any(k not in reading for k in required):
        raise ValueError("Sensor reading is missing required fields")
    if reading["data_mode"] != "SIMULATION":
        raise ValueError("save_sensor_reading accepts SIMULATION data only; use the verified real-adapter persistence path for REAL telemetry.")
    with get_connection() as conn:
        cur = conn.execute("""INSERT INTO sensor_readings
            (machine_id, temperature, vibration, rpm, operating_hours, status, data_mode, timestamp,
             anomaly_score, risk_level, fault_mode, health_percentage, machine_load, current_amp, voltage, degradation_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(reading[k] for k in required) + tuple(reading.get(k) for k in ("anomaly_score", "risk_level", "fault_mode", "health_percentage", "machine_load", "current_amp", "voltage", "degradation_pct")))
        return cur.lastrowid


def save_real_sensor_reading(reading, adapter_status):
    """Persist REAL telemetry only after a verified adapter reports connected."""
    required = ("machine_id", "timestamp", "source_id")
    if not getattr(adapter_status, "connected", False) or getattr(adapter_status, "status", "") != "HARDWARE CONNECTED":
        raise PermissionError("Real telemetry rejected: adapter connection is not verified.")
    if any(not reading.get(key) for key in required):
        raise ValueError("Real telemetry requires machine_id, timestamp and source_id.")
    with get_connection() as conn:
        cur = conn.execute("""INSERT INTO real_sensor_readings
            (machine_id, temperature, vibration, rpm, operating_hours, status, timestamp,
             source_id, current_amp, voltage, machine_load, quality_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED')""",
            (reading["machine_id"], reading.get("temperature"), reading.get("vibration"),
             reading.get("rpm"), reading.get("operating_hours"), reading.get("status"),
             reading["timestamp"], reading["source_id"], reading.get("current_amp"),
             reading.get("voltage"), reading.get("machine_load")))
        return cur.lastrowid


def get_recent_readings(machine_id, limit=100, data_mode=None):
    limit = max(1, min(int(limit), 5000))
    sql = "SELECT * FROM sensor_readings WHERE machine_id=?"
    params = [machine_id]
    if data_mode:
        sql += " AND data_mode=?"
        params.append(data_mode)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_latest_readings(data_mode=None):
    # This query intentionally reads only the simulation table. REAL telemetry
    # has its own table and can only be populated through a verified adapter.
    sql = "SELECT s.* FROM sensor_readings s JOIN (SELECT machine_id, MAX(id) max_id FROM sensor_readings"
    params = []
    if data_mode:
        sql += " WHERE data_mode=?"
        params.append(data_mode)
    sql += " GROUP BY machine_id) latest ON s.id=latest.max_id ORDER BY s.machine_id"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def save_alerts(machine_id, alerts, data_mode="SIMULATION"):
    """Persist only one unresolved copy of a given alert per machine."""
    from hashlib import sha256
    saved = 0
    with get_connection() as conn:
        for alert in alerts:
            problem = alert["problem"]
            category = problem.split(":", 1)[0].strip().lower()
            key = sha256(f"{machine_id}|{alert['severity']}|{category}".encode()).hexdigest()
            exists = conn.execute("SELECT id FROM alerts WHERE dedupe_key=? AND resolved_at IS NULL", (key,)).fetchone()
            if exists:
                continue
            conn.execute("""INSERT INTO alerts
                (machine_id,severity,problem,recommended_action,timestamp,dedupe_key,data_mode)
                VALUES (?,?,?,?,datetime('now'),?,?)""",
                (machine_id, alert["severity"], alert["problem"], alert["recommended_action"], key, data_mode))
            saved += 1
    return saved


def get_alert_history(limit=300, unresolved_only=False, data_mode=None):
    sql = "SELECT * FROM alerts"
    clauses = []
    params = []
    if unresolved_only:
        clauses.append("resolved_at IS NULL")
    if data_mode:
        clauses.append("data_mode=?")
        params.append(data_mode)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 2000)))
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def update_alert(alert_id, action):
    if action == "acknowledge":
        sql = "UPDATE alerts SET acknowledged_at=COALESCE(acknowledged_at, datetime('now')) WHERE id=? AND resolved_at IS NULL"
    elif action == "resolve":
        sql = "UPDATE alerts SET resolved_at=datetime('now'), acknowledged_at=COALESCE(acknowledged_at, datetime('now')) WHERE id=?"
    else:
        raise ValueError("Action must be acknowledge or resolve")
    with get_connection() as conn:
        conn.execute(sql, (int(alert_id),))


def add_maintenance_record(machine_id, maintenance_type, description, maintenance_date, performed_by="", cost=None, next_due_date=None):
    with get_connection() as conn:
        conn.execute("""INSERT INTO maintenance_history
            (machine_id,maintenance_type,description,maintenance_date,performed_by,cost,next_due_date,data_mode)
            VALUES (?,?,?,?,?,?,?,'MANUAL')""",
            (machine_id, maintenance_type, description, maintenance_date, performed_by, cost, next_due_date))


def get_maintenance_history(limit=500):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM maintenance_history ORDER BY maintenance_date DESC, id DESC LIMIT ?", (limit,)).fetchall()]


def get_machine_count():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM machines WHERE active=1").fetchone()[0]
