"""Per-laser chart presentation; independent of acquisition and pane assignment."""
from dataclasses import dataclass, field
from math import isfinite

DEFAULT_RATIO = 341 / 493  # Retain the v1.4 split geometry.
AXIS_DEFAULTS = {'main_scale': 2.75, 'main_position': 4.5,
                 'error_scale': 1.25, 'error_position': 0.0}


def axis_parameter(key):
    name = key.removeprefix('chart_')
    if name not in AXIS_DEFAULTS:
        return None
    signal, kind = name.split('_')
    return dict(label=f'{signal.title()} {kind}', unit='V/div' if kind == 'scale' else 'V',
                minimum=.01 if kind == 'scale' else -1000.,
                maximum=100. if kind == 'scale' else 1000., decimals=3, module='Y')


@dataclass
class ChartState:
    mode: str = 'split'
    main_upper: bool = True
    main_visible: bool = True
    error_visible: bool = True
    main_ratio: float = DEFAULT_RATIO
    axes: dict = field(default_factory=lambda: AXIS_DEFAULTS.copy())

    def snapshot(self):
        return dict(mode=self.mode, mainUpper=self.main_upper,
                    mainVisible=self.main_visible, errorVisible=self.error_visible,
                    mainRatio=self.main_ratio, **self.axes)

    def set_axis(self, key, raw):
        spec = axis_parameter(key)
        if spec is None:
            return 'Unknown chart parameter'
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 'Enter a number'
        if not isfinite(value) or not spec['minimum'] <= value <= spec['maximum']:
            return f"Range: {spec['minimum']:g} to {spec['maximum']:g} {spec['unit']}"
        self.axes[key.removeprefix('chart_')] = round(value, 3)
        return ''

    def bounds(self, error):
        prefix = 'error' if error else 'main'
        scale, center = self.axes[prefix+'_scale'], self.axes[prefix+'_position']
        return center-2*scale, center+2*scale

    def restore_axes(self):
        self.axes = AXIS_DEFAULTS.copy()
        self.main_ratio = DEFAULT_RATIO
