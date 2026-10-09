"""Pure Python simulation. No device transport or hardware commands."""
from dataclasses import dataclass, field
from math import isfinite, sin


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
    "temperature": Parameter("Set Temp", "C", 10, 40, 3, "TC"),
    "umax": Parameter("Umax", "V", 0, 100, 2),
    "pid": Parameter("TC PID P", "dB", -80, 20, 1, "TC"),
    "feedforward": Parameter("Feedforward factor", "mA/V", -100, 100, 3, "CC"),
    "offset": Parameter("Offset", "V", 0, 100, 3),
    "amplitude": Parameter("Scan amplitude", "Vpp", 0, 100, 3),
    "frequency": Parameter("Scan frequency", "Hz", 0.01, 1000, 2),
    "setpoint": Parameter("Lock setpoint", "V", -10, 10, 3),
}
MODULES = {"TC": ("temperature", "pid"), "CC": ("current", "feedforward"),
           "PC": ("offset", "amplitude", "frequency", "setpoint", "umax")}
PEAKS = ((52.0, 3.15, .16), (53.5, 5.45, .18), (55.35, 2.7, .17),
         (61.0, 6.85, .18), (62.5, 4.25, .17), (64.3, 8.1, .18))


@dataclass
class Laser:
    number: int
    values: dict = field(default_factory=lambda: {
        "current": 229.547, "temperature": 24.0, "umax": 2.81, "pid": -35.5,
        "feedforward": 0.0, "offset": 58.2, "amplitude": 20.0,
        "frequency": 10.0, "setpoint": 0.0})
    top: str = ""
    bottom: str = ""
    locked: bool = False
    stabilised: bool = False
    selected: int = -1
    show_error: bool = True
    revision: int = 0

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
        self.values[key] = round(value, spec.decimals)
        self.revision += 1
        return ""

    def top_field(self) -> str:
        return self.top or ("current" if self.number == 1 else "temperature")

    def bottom_field(self) -> str:
        return self.bottom or ("umax" if self.number == 1 else "pid")

    def drift(self, time: float) -> float:
        if self.locked:
            return 0.0
        return sin(time * .65 + self.number - 1) * (.007 if self.stabilised else .055)

    def sample(self, x: float, time: float) -> tuple[float, float]:
        drift = self.drift(time)
        absorption, error = .48, 0.0
        gain = 1 + (self.values["current"] - 229.547) * .0002
        for center, amplitude, width in PEAKS:
            u = (x - center - drift) / width
            absorption += amplitude * gain / (1 + u * u)
            error += amplitude * .24 * (-2 * u) / (1 + u * u) ** 2
        noise = .002 if self.stabilised or self.locked else .014
        error += noise * sin(x * 31 + time * 8 + self.number)
        return absorption, error


class Instrument:
    def __init__(self):
        self.lasers = [Laser(1), Laser(2)]
        self.views = [0, 1]

    def switch_view(self, side: int):
        self.views[side] = 1 - self.views[side]

    def laser_for_view(self, side: int) -> Laser:
        return self.lasers[self.views[side]]
