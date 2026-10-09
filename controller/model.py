"""Pure Python simulation. No device transport or hardware commands."""
from dataclasses import dataclass, field
from math import isfinite
from .simulation import SignalSimulation
from .charts import ChartState


@dataclass(frozen=True)
class Parameter:
    label: str
    unit: str
    minimum: float
    maximum: float
    decimals: int
    module: str = "PC"


PARAMETERS = {
    "current": Parameter("Set Current", "mA", 0, 500, 3, "CC"),
    "temperature": Parameter("Set Temp", "°C", 10, 40, 3, "TC"),
    "umax": Parameter("Umax", "V", 0, 100, 2),
    "pid": Parameter("TC PID P", "dB", -80, 20, 1, "TC"),
    "feedforward": Parameter("Feedforward factor", "mA/V", -100, 100, 3, "CC"),
    "offset": Parameter("Offset", "V", 0, 100, 3),
    "amplitude": Parameter("Scan amplitude", "Vpp", 0, 100, 3),
    "frequency": Parameter("Scan frequency", "Hz", 0.01, 1000, 2),
    "setpoint": Parameter("Lock setpoint", "V", -10, 10, 3),
    "maximum_current": Parameter("Maximum Current Imax", "mA", 0, 500, 3, "CC"),
    "minimum_temperature": Parameter("Minimum Temperature", "°C", 10, 40, 3, "TC"),
    "maximum_temperature": Parameter("Maximum Temperature", "°C", 10, 40, 3, "TC"),
    "pid_i": Parameter("TC Regulator I Parameter", "dB", -100, 20, 1, "TC"),
    "pid_d": Parameter("TC Regulator D Parameter", "dB", -100, 20, 1, "TC"),
}
MODULES = {"TC": ("temperature", "pid", "pid_i", "pid_d"), "CC": ("current", "feedforward", "maximum_current"),
           "PC": ("offset", "amplitude", "frequency", "setpoint", "umax")}
PEAKS = ((52.0, 3.15, .16), (53.5, 5.45, .18), (55.35, 2.7, .17),
         (61.0, 6.85, .18), (62.5, 4.25, .17), (64.3, 8.1, .18))


@dataclass
class Laser:
    number: int
    values: dict = field(default_factory=lambda: {
        "current": 229.547, "temperature": 24.0, "umax": 2.81, "pid": -35.5,
        "feedforward": 0.0, "offset": 58.2, "amplitude": 20.0,
        "frequency": 10.0, "setpoint": 0.0, "maximum_current": 300.0,
        "minimum_temperature": 15.0, "maximum_temperature": 32.0,
        "pid_i": -57.0, "pid_d": -55.1})
    top: str = ""
    bottom: str = ""
    locked: bool = False
    emission: bool = True
    stabilised: bool = False
    selected: int = -1
    alarms: dict = field(default_factory=lambda: {'enabled': False, 'main_high': 8.5, 'error_high': 2.0})
    chart: ChartState = field(default_factory=ChartState)
    revision: int = 0
    signal: SignalSimulation = field(init=False)

    def __post_init__(self):
        self.signal = SignalSimulation(self.values, self.number)

    def set_value(self, key: str, raw: str) -> str:
        """Validate before mutation; rejected edits leave accepted state intact."""
        spec = PARAMETERS.get(key)
        if spec is None:
            return "Unknown parameter"
        try:
            value = float(raw)
        except ValueError:
            return "Enter a number"
        if not isfinite(value) or not spec.minimum <= value <= spec.maximum:
            return f"Range: {spec.minimum:g} to {spec.maximum:g} {spec.unit}"
        if key == 'current' and value > self.values['maximum_current']:
            return f"Maximum current: {self.values['maximum_current']:g} mA"
        if key == 'maximum_current' and value < self.values['current']:
            return 'Reduce Set Current before lowering this limit'
        if key == 'temperature' and not self.values['minimum_temperature'] <= value <= self.values['maximum_temperature']:
            return f"Temperature range: {self.values['minimum_temperature']:g} to {self.values['maximum_temperature']:g} °C"
        if key == 'minimum_temperature' and value > self.values['temperature']:
            return 'Minimum cannot exceed the set temperature'
        if key == 'maximum_temperature' and value < self.values['temperature']:
            return 'Maximum cannot be below the set temperature'
        self.values[key] = round(value, spec.decimals)
        self.revision += 1
        return ""

    def top_field(self) -> str:
        return self.top or ("current" if self.number == 1 else "temperature")

    def bottom_field(self) -> str:
        return self.bottom or ("umax" if self.number == 1 else "pid")

    def drift(self, time: float) -> float:
        return self.signal.drift()

    def sample(self, x: float, time: float) -> tuple[float, float]:
        return self.signal.sample(x)


class Instrument:
    def __init__(self):
        self.lasers = [Laser(1), Laser(2)]
        self.views = [0, 1]

    def switch_view(self, side: int):
        self.views[side] = 1 - self.views[side]

    def laser_for_view(self, side: int) -> Laser:
        return self.lasers[self.views[side]]
