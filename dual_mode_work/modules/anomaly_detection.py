"""Isolation Forest anomaly detection trained on synthetic demo baselines by default."""
import numpy as np
from sklearn.ensemble import IsolationForest


class PredictiveMaintenanceAI:
    def __init__(self, contamination=0.05, random_state=42):
        self.model = IsolationForest(n_estimators=200, contamination=contamination,
                                     random_state=random_state)
        self.is_trained = False
        self.training_source = "NOT TRAINED"
        self.feature_names = ["Temperature", "Vibration", "RPM", "Machine load", "Current", "Voltage"]
        self.feature_center = np.array([55.0, 2.0, 1450.0, 68.0, 3.8, 400.0])
        self.feature_scale = np.array([5.0, .5, 30.0, 12.0, 1.0, 7.0])

    def train_demo_model(self, samples=2100):
        """Fit a fleet-wide synthetic baseline spanning supported machine families."""
        rng = np.random.default_rng(42)
        profiles = [
            (52, 7, 1.5, .55, 1500, 27),
            (58, 8, 2.0, .65, 2900, 72),
            (64, 9, 2.2, .75, 1450, 29),
            (43, 6, 1.0, .35, 3000, 36),
            (49, 7, 1.3, .5, 1450, 32),
            (57, 8, 2.1, .65, 1500, 30),
            (46, 6, 1.4, .5, 900, 22),
        ]
        per_profile = max(1, samples // len(profiles))
        batches = []
        for temp_mu, temp_sd, vib_mu, vib_sd, rpm_mu, rpm_sd in profiles:
            loads = np.clip(rng.normal(68, 12, per_profile), 5, 100)
            batch = np.column_stack((
                rng.normal(temp_mu, temp_sd, per_profile),
                rng.normal(vib_mu, vib_sd, per_profile),
                rng.normal(rpm_mu, rpm_sd, per_profile),
                loads,
                np.maximum(.1, loads / 100 * (2.5 + rpm_mu / 1800) * rng.normal(1, .06, per_profile)),
                rng.normal(400, 7, per_profile),
            ))
            batches.append(batch)
        training = np.vstack(batches)
        training = np.clip(training, [20, .05, 300, 0, .05, 150], [150, 25, 5000, 100, 100, 500])
        self.model.fit(training)
        self.feature_center = np.median(training, axis=0)
        self.feature_scale = np.maximum(np.std(training, axis=0), 1e-6)
        self.is_trained = True
        self.training_source = "SYNTHETIC MULTI-MACHINE DEMONSTRATION BASELINE"

    def train_from_history(self, readings):
        """Train from a caller-supplied curated dataset; requires >=100 finite rows."""
        data = np.asarray([[r["temperature"], r["vibration"], r["rpm"],
                            r.get("machine_load", 68.0), r.get("current_amp", 3.8),
                            r.get("voltage", 400.0)] for r in readings], dtype=float)
        if data.ndim != 2 or data.shape[0] < 100 or data.shape[1] != 6 or not np.isfinite(data).all():
            raise ValueError("At least 100 complete, finite historical readings are required.")
        self.model.fit(data)
        self.feature_center = np.median(data, axis=0)
        self.feature_scale = np.maximum(np.std(data, axis=0), 1e-6)
        self.is_trained = True
        self.training_source = "USER-SUPPLIED HISTORICAL READINGS (UNVALIDATED)"

    def predict(self, temperature, vibration, rpm, machine_load=68.0, current_amp=3.8, voltage=400.0):
        if not self.is_trained:
            raise RuntimeError("Train the model before prediction.")
        row = np.asarray([[temperature, vibration, rpm, machine_load, current_amp, voltage]], dtype=float)
        if not np.isfinite(row).all():
            raise ValueError("Prediction features must be finite numbers.")
        prediction = int(self.model.predict(row)[0])
        score = float(self.model.decision_function(row)[0])
        anomaly = prediction == -1
        risk = "HIGH" if anomaly and score < -0.08 else "ELEVATED" if anomaly else "LOW"
        action = ("Unusual multivariate pattern: inspect the machine and verify the sensors."
                  if anomaly else "No anomaly flagged by the current demonstration model; continue monitoring.")
        deviations = np.abs((row[0] - self.feature_center) / self.feature_scale)
        contributions = sorted(
            [{"feature": name, "standardized_deviation": round(float(dev), 2)}
             for name, dev in zip(self.feature_names, deviations)],
            key=lambda item: item["standardized_deviation"], reverse=True
        )
        return {"anomaly_detected": bool(anomaly), "risk_level": risk,
                "anomaly_score": round(score, 4), "recommended_action": action,
                "sensor_contributions": contributions,
                "model_type": "Isolation Forest", "training_source": self.training_source,
                "data_mode": "SIMULATED DEMO" if "SYNTHETIC" in self.training_source else "HISTORICAL DATA"}
