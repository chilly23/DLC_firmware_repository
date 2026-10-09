"""Validated wiring, calibration and user mappings; BCM numbers, never header positions."""
from copy import deepcopy
import json
from pathlib import Path
from .panel import PANEL_DEFAULTS

CONTACTS=('A','B','C','D','push')
SIGNALS=('encoder_a','encoder_b',*CONTACTS)
DIRECTIONS=('up','right','down','left')
OPERATIONS=('clockwise','anticlockwise','up','down','left','right','push')
LOCATIONS=('Top left','Bottom left','Top right','Bottom right')
PIN_MAPS=(
    dict(C=2,D=3,encoder_a=4,A=17,push=27,encoder_b=22,B=10),
    dict(C=14,B=15,encoder_b=18,push=23,A=24,encoder_a=25,D=8),
    {},
    dict(B=26,encoder_b=19,C=13,D=6,encoder_a=5,A=0,push=21),
)
# Explicit commands cross the hardware/frontend seam. Labels are UI metadata.
ACTIONS={
 'none':'Not assigned', 'value.increase':'Increase selected digit', 'value.decrease':'Decrease selected digit',
 'cursor.left':'Select digit to the left', 'cursor.right':'Select digit to the right',
 'focus.next':'Focus next control', 'focus.previous':'Focus previous control', 'focus.activate':'Activate focused control',
 'focus.back':'Back / close panel', 'editor.open':'Open corner value editor',
 'graph.lock':'Toggle graph lock', 'graph.left':'Pan graph left', 'graph.right':'Pan graph right',
 'graph.up':'Pan graph up', 'graph.down':'Pan graph down', 'graph.zoom_in':'Zoom graph in',
 'graph.zoom_out':'Zoom graph out', 'graph.reset':'Reset graph view', 'emission.toggle':'Toggle emission',
 'stabilise.toggle':'Toggle stabilisation', 'view.swap':'Switch displayed laser',
 'view.fullscreen':'Toggle graph fullscreen', 'signals.open':'Open chart signals',
 'more.open':'Open More menu', 'settings.open':'Open Settings', 'capture.frame':'Export graph frame',
}

def default_knob(index):
    mapping=dict(clockwise='value.increase',anticlockwise='value.decrease',up='focus.previous',
                 down='focus.next',left='cursor.left',right='cursor.right',push='graph.lock')
    if index==1:
        mapping=dict(clockwise='focus.next',anticlockwise='focus.previous',up='graph.up',down='graph.down',
                     left='graph.left',right='graph.right',push='more.open')
    return dict(name=f'Knob {index+1}',location=LOCATIONS[index],enabled=bool(PIN_MAPS[index]),pins=dict(PIN_MAPS[index]),
                target=index,calibrated=False,directions=dict(up='A',right='D',down='C',left='B'),push_contact='push',
                released=dict.fromkeys(CONTACTS,1),reverse_encoder=False,transitions_per_detent=2,
                switch_debounce_ms=8,mapping=mapping)

DEFAULTS=dict(schema=1,wiring_revision=3,chip='auto',knobs=[default_knob(i) for i in range(4)],panel=deepcopy(PANEL_DEFAULTS))

def migrate_wiring(config):
    """Upgrade stock wiring without discarding calibration or custom assignments.

    Custom pin layouts are left intact. Knobs 1/2 keep their calibration and
    shortcuts. The replacement knob must be calibrated as a new physical unit.
    Revision 3 moves the disabled stock left shortcut from GPIO8 to GPIO16.
    """
    cfg=deepcopy(config)
    revision=cfg.get('wiring_revision',1)
    if revision<2:
        old,new=cfg['knobs'][2:4]
        if old['pins']==PIN_MAPS[3] and not new['pins']:
            replacement=default_knob(3)
            for key in ('mapping','transitions_per_detent','switch_debounce_ms'):
                replacement[key]=deepcopy(old[key])
            replacement['target']=3 if old['target']==2 else old['target']
            cfg['knobs'][2]=default_knob(2);cfg['knobs'][3]=replacement
    new_panel='panel' not in cfg
    cfg.setdefault('panel',deepcopy(PANEL_DEFAULTS))
    if revision<3:
        left=cfg['panel'].get('left_shortcut')
        used={p for knob in cfg['knobs'] for p in knob['pins'].values()}
        used.update(c['pin'] for key,c in cfg['panel'].items() if key!='left_shortcut' and c['enabled'])
        if left and left['pin']==8 and not left['enabled'] and not left.get('calibrated') and 16 not in used:
            left.update(pin=16,enabled=True,active_level=0,calibrated=True)
        elif new_panel and left and 16 in used:
            left['enabled']=False
    cfg['wiring_revision']=max(revision,3)
    return validate(cfg)

def validate(config):
    if config.get('schema')!=1 or len(config.get('knobs',[]))!=4:raise ValueError('Expected four knob slots and schema 1.')
    if not isinstance(config.get('chip'),str) or not (config['chip']=='auto' or config['chip'].startswith('/dev/gpiochip')):
        raise ValueError('Chip must be auto or a /dev/gpiochip path.')
    used=set()
    for knob in config['knobs']:
        pins=knob.get('pins',{})
        if not pins and not knob['enabled']:continue
        if set(pins)!=set(SIGNALS):raise ValueError('Each connected knob needs all seven signals.')
        for pin in pins.values():
            if type(pin) is not int or not 0<=pin<=27 or pin in used:raise ValueError('BCM GPIO assignments must be unique, from 0 to 27.')
            used.add(pin)
        if knob.get('target') not in range(4):raise ValueError('Invalid target corner.')
        contacts=list(knob['directions'].values())+[knob['push_contact']]
        if set(knob['directions'])!=set(DIRECTIONS) or len(set(contacts))!=5 or set(contacts)!=set(CONTACTS):
            raise ValueError('Directions and push must each use a distinct switch contact.')
        if knob['transitions_per_detent'] not in (1,2,4):raise ValueError('Encoder transitions must be 1, 2 or 4.')
        if not 1<=knob['switch_debounce_ms']<=50:raise ValueError('Debounce must be 1–50 ms.')
        if set(knob['released'])!=set(CONTACTS) or any(v not in (0,1) for v in knob['released'].values()):raise ValueError('Invalid released-state calibration.')
        if set(knob['mapping'])!=set(OPERATIONS) or any(v not in ACTIONS for v in knob['mapping'].values()):raise ValueError('Unknown knob action.')
    for name,contact in config.get('panel',{}).items():
        if name not in PANEL_DEFAULTS:raise ValueError('Unknown panel contact.')
        if type(contact['pin']) is not int or not 0<=contact['pin']<=27:raise ValueError('Panel pins must be BCM 0-27.')
        if contact['active_level'] not in (0,1) or not 5<=contact['debounce_ms']<=100:raise ValueError('Invalid panel polarity/debounce.')
        if contact['enabled']:
            if contact['pin'] in used:raise ValueError(f'GPIO{contact["pin"]} is already assigned. Each physical control needs its own GPIO.')
            used.add(contact['pin'])
    return config

class ControlStore:
    def __init__(self,path):
        self.path=Path(path);self.error='';self.config=deepcopy(DEFAULTS)
        if self.path.exists():
            try:
                original=validate(json.loads(self.path.read_text(encoding='utf8')))
                self.config=migrate_wiring(original)
            except (OSError,ValueError,TypeError,KeyError) as exc:
                self.error='Cannot load controls file; defaults loaded: '+str(exc)
                return
            if self.config!=original:
                try:self.commit(self.config)
                except OSError as exc:self.error='Updated wiring is active but could not be saved: '+str(exc)
    def commit(self,config):
        validate(config)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(config,indent=2)+'\n',encoding='utf8');temp.replace(self.path)
        self.config=deepcopy(config);self.error=''
    def update(self,index,key,value):
        cfg=deepcopy(self.config);cfg['knobs'][index][key]=value;self.commit(cfg)
