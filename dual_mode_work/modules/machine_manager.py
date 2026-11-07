"""Machine catalogue and configuration helpers."""

MACHINE_TYPES = {
    "Electric Motor": {"rpm": 1500, "temperature_limit": 75, "vibration_limit": 4.5},
    "Centrifugal Pump": {"rpm": 2900, "temperature_limit": 80, "vibration_limit": 4.5},
    "Gearbox": {"rpm": 1500, "temperature_limit": 80, "vibration_limit": 4.0},
    "Air Compressor": {"rpm": 1450, "temperature_limit": 90, "vibration_limit": 5.0},
    "Industrial Fan": {"rpm": 1450, "temperature_limit": 75, "vibration_limit": 4.5},
    "Conveyor Belt": {"rpm": 900, "temperature_limit": 75, "vibration_limit": 4.5},
    "CNC Machine": {"rpm": 3000, "temperature_limit": 70, "vibration_limit": 3.5},
    "Hydraulic Pump": {"rpm": 1800, "temperature_limit": 80, "vibration_limit": 4.5},
    "Cooling Tower": {"rpm": 750, "temperature_limit": 65, "vibration_limit": 4.0},
    "Generator": {"rpm": 1500, "temperature_limit": 85, "vibration_limit": 5.0},
}


def create_machine(machine_number, machine_type="Electric Motor"):
    if machine_type not in MACHINE_TYPES:
        raise ValueError(f"Unsupported machine type: {machine_type}")
    limits = MACHINE_TYPES[machine_type]
    return {
        "machine_id": f"Machine {int(machine_number):02d}",
        "machine_type": machine_type,
        "active": True,
        "data_mode": "SIMULATION",
        "rpm": limits["rpm"],
        "temperature_limit": limits["temperature_limit"],
        "vibration_limit": limits["vibration_limit"],
    }


def create_initial_machines(count=3):
    return [create_machine(n) for n in range(1, count + 1)]


def get_next_machine_number(machines):
    numbers = []
    for machine in machines:
        try:
            numbers.append(int(str(machine["machine_id"]).split()[-1]))
        except (KeyError, ValueError, IndexError):
            continue
    return max(numbers, default=0) + 1


def add_machine(machines, machine_type="Electric Motor"):
    machine = create_machine(get_next_machine_number(machines), machine_type)
    machines.append(machine)
    return machines
