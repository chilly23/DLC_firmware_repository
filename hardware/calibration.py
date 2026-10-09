"""Transactional direction/encoder calibration; failed or cancelled work never applies."""
from copy import deepcopy
from .config import CONTACTS,DIRECTIONS

class Calibration:
    TITLES=('Release the knob','Move up','Move right','Move down','Move left','Press the centre',
            'Rotate clockwise','Rotate anticlockwise','Review and save')
    def __init__(self,index,config):
        self.index=index;self.original=deepcopy(config);self.stage=0;self.released=None
        self.contacts={};self.candidate=None;self.rotation=0;self.cw_sign=0;self.error=''
        self.last_levels=None;self.stable_since=0.;self.last_count=None
    @property
    def title(self):return self.TITLES[self.stage]
    @property
    def detail(self):
        if self.stage==0:return 'Let go of the stick and button. Capture the released state when all contacts have settled.'
        if self.stage<6:
            return 'Release to continue.' if self.candidate else 'Make only this movement, then release. It is recorded automatically.'
        if self.stage<8:return 'Turn at least one click in this direction, stop, then choose Next. Observed steps: '+str(self.rotation)
        return 'Directions and rotation have been checked. Save applies this calibration to this knob only.'
    def feed(self,levels,count,now):
        contacts={k:levels[k] for k in CONTACTS}
        if contacts!=self.last_levels:self.last_levels=contacts;self.stable_since=now
        if self.last_count is not None and self.stage in (6,7):self.rotation+=count-self.last_count
        self.last_count=count
        if not 1<=self.stage<=5 or now-self.stable_since<.04:return
        changed=[k for k in CONTACTS if contacts[k]!=self.released[k]]
        if len(changed)>1:self.error='More than one contact is active. Release, then move in just one direction.';self.candidate=None;return
        if len(changed)==1:
            key=changed[0]
            if key in self.contacts.values():self.error='That contact is already assigned. Release and make the requested movement.';return
            self.candidate=key;self.error=''
        elif self.candidate:
            requested=DIRECTIONS[self.stage-1] if self.stage<=4 else 'push'
            self.contacts[requested]=self.candidate;self.candidate=None;self.stage+=1;self.rotation=0;self.error=''
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
