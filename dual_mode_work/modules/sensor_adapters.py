"""Future sensor integration contracts. No real adapter is enabled by default.

Implementations must validate endpoint identity, units, timestamps, calibration,
data quality and authorization before reporting is_connected=True.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class AdapterStatus:
    connected: bool
    status: str
    message: str
    source_id: Optional[str] = None

class SensorAdapter(ABC):
    adapter_name = "UNCONFIGURED"

    @abstractmethod
    def verify_connection(self) -> AdapterStatus:
        """Return connected=True only after a real endpoint is verified."""
        raise NotImplementedError

    @abstractmethod
    def read_machine(self, machine_id: str) -> dict:
        """Return validated real telemetry with timestamp and source_id."""
        raise NotImplementedError

class DisabledHardwareAdapter(SensorAdapter):
    adapter_name = "HARDWARE DISABLED"

    def verify_connection(self) -> AdapterStatus:
        return AdapterStatus(False, "HARDWARE DISCONNECTED",
            "No verified hardware adapter is configured. Real data ingestion is disabled.")

    def read_machine(self, machine_id: str) -> dict:
        raise RuntimeError("Real hardware mode is disabled: configure and verify a sensor adapter first.")

SUPPORTED_INTEGRATIONS = (
    "Temperature sensors", "Vibration sensors / accelerometers", "RPM sensors",
    "Current and voltage sensors", "PLC gateways", "Industrial IoT gateways",
    "Modbus TCP", "MQTT", "OPC UA"
)

def get_hardware_status():
    return DisabledHardwareAdapter().verify_connection()
