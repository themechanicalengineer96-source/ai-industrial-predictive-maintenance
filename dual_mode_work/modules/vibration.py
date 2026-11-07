"""Vibration signal generation and time/frequency-domain analysis."""
import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal import find_peaks


def generate_vibration_signal(sampling_rate=2000, duration=2, fault_mode=False, amplitude=1.4, seed=None):
    if sampling_rate <= 0 or duration <= 0:
        raise ValueError("Sampling rate and duration must be positive.")
    rng = np.random.default_rng(seed)
    time = np.arange(0, duration, 1 / sampling_rate)
    signal = amplitude * np.sin(2 * np.pi * 25 * time) + .5 * np.sin(2 * np.pi * 75 * time)
    if fault_mode:
        signal += 2.0 * np.sin(2 * np.pi * 120 * time)
    signal += rng.normal(0, .15, len(time))
    return time, signal


def analyze_vibration(signal, sampling_rate=2000, warning_rms=4.5, critical_rms=7.1):
    signal = np.asarray(signal, dtype=float)
    if sampling_rate <= 0 or signal.size < 2 or not np.all(np.isfinite(signal)):
        raise ValueError("Signal must contain at least two finite samples and sampling_rate must be positive.")
    signal = signal - np.mean(signal)
    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))
    crest = peak / rms if rms > 0 else 0.0
    spectrum = np.abs(rfft(signal)) * 2 / len(signal)
    frequencies = rfftfreq(len(signal), 1 / sampling_rate)
    spectrum[0] = 0
    max_amp = float(np.max(spectrum))
    peaks, _ = find_peaks(spectrum, height=max_amp * .1 if max_amp else 0)
    dominant = float(frequencies[int(np.argmax(spectrum))]) if max_amp else 0.0
    status = "CRITICAL" if rms >= critical_rms else "WARNING" if rms >= warning_rms else "NORMAL"
    return {"rms": round(rms, 3), "peak": round(peak, 3), "crest_factor": round(float(crest), 3),
            "dominant_frequency": round(dominant, 2), "frequencies": frequencies,
            "spectrum": spectrum, "significant_frequencies": [round(float(frequencies[i]), 2) for i in peaks],
            "status": status}
