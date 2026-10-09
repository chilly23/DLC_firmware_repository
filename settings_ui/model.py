"""Settings and history shared by the three views; no device hardware writes."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "display": "Display Settings",
    "system": "System Settings",
    "function": "Function Settings",
    "storage": "Storage",
    "about": "About",
    "help": "Help",
    "upgrade": "Upgrade",
}
ORDERS = {
    32: ["display", "system", "function", "storage", "about", "help", "upgrade"],
    58: ["system", "function", "storage", "help", "upgrade", "about", "display"],
    59: ["system", "function", "storage", "help", "upgrade", "display", "about"],
}
DEFAULTS = {
    "brightness": 80,
    "animations": True,
    "timeout": "5 minutes",
    "sound": False,
    "language": "English",
    "units": "SI",
    "laser1": True,
    "laser2": True,
    "stabilisation": False,
    "scan_rate": "20 Hz",
    "logging": True,
    "retention": "30 days",
}
SEARCH = [
    ("display", "Display Settings", "Screen brightness, animations, sleep timeout"),
    ("system", "System Settings", "Language, touch sound, measurement units"),
    (
        "function",
        "Function Settings",
        "Laser 1, Laser 2, graph stabilisation, scan rate",
    ),
    ("storage", "Storage", "Data logging, retention, export settings"),
    ("about", "About", "Model, calibration time, firmware version, serial number"),
    ("help", "Help", "Touch gestures, navigation, search assistance"),
    ("upgrade", "Upgrade", "Firmware update, installed version"),
]


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / "data" / "settings.json")
        self.values = DEFAULTS.copy()
        self.history = []
        self.error = ""
        try:
            content = json.loads(self.path.read_text(encoding="utf8"))
            self.values.update(
                {k: v for k, v in content.get("values", {}).items() if k in DEFAULTS}
            )
            self.history = [str(s) for s in content.get("history", [])][:8]
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps({"values": self.values, "history": self.history}, indent=2),
                encoding="utf8",
            )
            temporary.replace(self.path)
            self.error = ""
        except OSError as exc:
            self.error = "Could not save settings: " + str(exc)
        return not self.error

    def remember(self, query):
        query = query.strip()
        if query:
            self.history = [query] + [
                q for q in self.history if q.casefold() != query.casefold()
            ]
            self.history = self.history[:8]
            self.save()

    def search(self, query):
        terms = query.casefold().split()
        return [
            item
            for item in SEARCH
            if all(t in (" ".join(item)).casefold() for t in terms)
        ]
