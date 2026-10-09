"""Persisted application preferences and the searchable settings catalog."""

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "logs": "Logs",
    "notifications": "Notifications",
    "control": "Control Settings",
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
    58: ["display", "function", "control", "system", "notifications", "storage", "help", "upgrade", "about"],
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
    ("notifications","Notifications","Action history warning critical error permission notifications clear"),
    ("display", "Display Settings", "Screen brightness contrast resolution refresh rate UI scale accent color theme dark light appearance recommended preset corner number label font colors"),
    ("system", "System Settings", "Language font text size side button icons names date time clock automatic sleep shutdown idle factory reset restore defaults information tour tutorial guide lock startup boot login repair setup"),
    (
        "function",
        "Function Settings",
        "Laser 1 Laser 2 spectroscopy error graph baseline calibration X Y limits bandwidth sampling rate maximum points graph color laser color line width",
    ),
    ("storage", "Storage", "Disk space export settings JSON capture graph frame CSV clear search history"),
    ("about", "About", "Model organization firmware version serial number QR code"),
    ("help", "Help", "Touch gestures, navigation, search assistance"),
    ("upgrade", "Upgrade", "Firmware update, installed version"),
    ("control", "Control Settings", "RKJXT knob GPIO rotary encoder joystick push directions calibration shortcuts mapping target corner screen touch test diagnostics navigation buttons physical switch system lock shutdown countdown"),
]


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / "data" / "settings.json")
        from .preferences import NEW_DEFAULTS
        self.values = deepcopy(DEFAULTS)
        self.values.update(deepcopy(NEW_DEFAULTS))
        self.history = []
        self.error = ""
        try:
            content = json.loads(self.path.read_text(encoding="utf8"))
            self.values.update(
                {k: v for k, v in content.get("values", {}).items() if k in self.values}
            )
            self.history = [str(s) for s in content.get("history", [])][:8]
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        # Version migration also merges newly introduced graph keys.
        from .preferences import GRAPH_DEFAULTS
        for key in ('graph1','graph2'):
            loaded=self.values.get(key,{})
            self.values[key]=dict(GRAPH_DEFAULTS,**(loaded if isinstance(loaded,dict) else {}))
            if isinstance(loaded,dict):
                for prefix in ('main','error'):
                    if prefix+'_color' not in loaded:self.values[key][prefix+'_color']=loaded.get('graph_color',GRAPH_DEFAULTS['graph_color'])
                    if prefix+'_width' not in loaded:self.values[key][prefix+'_width']=loaded.get('line_width',1.7)
        if self.values.get('notification_size') not in ('Small','Medium','Large'):self.values['notification_size']='Medium'
        if self.values.get('home_graph_size') not in ('Small','Medium','Large'):self.values['home_graph_size']='Large'
        from interaction.workspace import PANEL_BUTTONS
        for key in ('panel_order_left','panel_order_right'):
            order=self.values.get(key)
            if not isinstance(order,list) or len(order)!=5 or any(not isinstance(value,str) for value in order) or set(order)!=set(PANEL_BUTTONS):
                self.values[key]=list(PANEL_BUTTONS)
        if self.values.get('sampling_rate') not in (5,10,20,30,60):self.values['sampling_rate']=20
        if self.values.get('language') not in ('English','Français','Deutsch','Español','Italiano','Português'):
            self.values['language']='English'
        from math import isfinite
        for key in ('alarms1','alarms2'):
            loaded=self.values.get(key,{})
            valid=deepcopy(NEW_DEFAULTS[key])
            if isinstance(loaded,dict):
                valid['enabled']=loaded.get('enabled') is True
                for field in ('main_high','error_high'):
                    try:value=float(loaded.get(field,valid[field]))
                    except (ValueError,TypeError):continue
                    if isfinite(value) and (0 if field=='error_high' else -1000)<=value<=1000:valid[field]=value
            self.values[key]=valid
        self.path.parent.mkdir(parents=True,exist_ok=True)

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
        from .translations import translate
        terms = query.casefold().split()
        return [
            item
            for item in SEARCH
            if all(t in (" ".join(item)+' '+translate(item[1],self.values['language'])).casefold() for t in terms)
        ]
