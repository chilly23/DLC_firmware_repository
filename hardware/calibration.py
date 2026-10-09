"""Transactional direction/encoder calibration; failed or cancelled work never applies."""
from copy import deepcopy
from .config import CONTACTS,DIRECTIONS

class Calibration:
    TITLES=('Release the knob','Press the centre','Move up','Move right','Move down','Move left',
            'Rotate clockwise','Rotate anticlockwise','Review and save')
    def __init__(self,index,config):
        self.index=index;self.original=deepcopy(config);self.stage=0;self.released=None
        self.contacts={};self.candidate=None;self.rotation=0;self.cw_sign=0;self.error='';self.invalid=False
        self.last_levels=None;self.stable_since=0.;self.last_count=None
    @property
    def title(self):return self.TITLES[self.stage]
    @property
    def detail(self):
        if self.stage==0:return 'Let go of the stick and button. Capture the released state when all contacts have settled.'
        if self.stage<6:
            if self.invalid:return 'Release the knob completely, then try the requested movement again.'
            if self.candidate:return 'Release the stick and centre contact completely to continue.'
            if self.stage==1:return 'Press straight into the centre without tilting, then release. This identifies the shared push contact.'
            return 'Move in this direction, then release. The centre contact may close with the direction contact.'
        if self.stage<8:return 'Turn at least one click in this direction, stop, then choose Next. Observed steps: '+str(self.rotation)
        return 'Directions and rotation have been checked. Save applies this calibration to this knob only.'
    def feed(self,levels,count,now):
        contacts={k:levels[k] for k in CONTACTS}
        if contacts!=self.last_levels:self.last_levels=contacts;self.stable_since=now
        if self.last_count is not None and self.stage in (6,7):self.rotation+=count-self.last_count
        self.last_count=count
        if not 1<=self.stage<=5 or now-self.stable_since<.04:return
        changed=[k for k in CONTACTS if contacts[k]!=self.released[k]]
        if not changed:
            if self.candidate and not self.invalid:
                requested='push' if self.stage==1 else DIRECTIONS[self.stage-2]
                self.contacts[requested]=self.candidate;self.stage+=1;self.rotation=0
            self.candidate=None;self.invalid=False;self.error=''
            return
        if self.invalid:return
        # Learn the centre-only contact first. A tilt may close it as well as
        # exactly one directional contact; that is a single physical movement.
        primary=changed if self.stage==1 else [k for k in changed if k!=self.contacts['push']]
        if not primary:return  # push-leading / push-trailing part of a tilt
        if len(primary)>1:
            self.error='More than one direction is active. Release, then move in just one direction.';self.invalid=True
        elif primary[0] in self.contacts.values():
            self.error='That contact is already assigned. Release and make the requested movement.';self.invalid=True
        elif self.candidate and primary[0]!=self.candidate:
            self.error='Direction changed before release. Let go, then try again.';self.invalid=True
        else:self.candidate=primary[0];self.error=''
    def next(self,now):
        self.error=''
        if self.stage==0:
            if self.last_levels is None or now-self.stable_since<.3:self.error='Wait for stable readings with the knob released.';return False
            self.released=dict(self.last_levels);self.stage=1;return True
        if self.stage in (6,7):
            if not self.rotation:self.error='No complete encoder click detected. Turn the knob, then choose Next.';return False
            sign=1 if self.rotation>0 else -1
            if self.stage==6:self.cw_sign=sign
            elif sign==self.cw_sign:self.error='This has the same sign as clockwise. Turn anticlockwise and try again.';self.rotation=0;return False
            self.stage+=1;self.rotation=0;return True
        return False
    def result(self):
        if self.stage!=8:raise ValueError('Complete every calibration step before saving.')
        result=deepcopy(self.original);result.update(calibrated=True,released=self.released,
            directions={k:self.contacts[k] for k in DIRECTIONS},push_contact=self.contacts['push'],reverse_encoder=self.cw_sign<0)
        return result
