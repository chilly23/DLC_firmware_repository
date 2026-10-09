"""Local visual signal model; no device commands or measurement claims."""
from math import exp, sin
from random import Random

X_MIN, X_MAX, SAMPLE_COUNT = 48.2, 68.2, 1001
X_STEP = (X_MAX-X_MIN)/(SAMPLE_COUNT-1)
PEAK_SETS = (
    ((52.0,3.15,.16),(53.5,5.45,.18),(55.35,2.7,.17),(61.0,6.85,.18),(62.5,4.25,.17),(64.3,8.1,.18)),
    ((51.3,2.25,.23),(53.1,6.35,.21),(56.1,3.75,.25),(59.9,4.65,.22),(63.0,7.1,.24),(65.4,5.4,.20)),
)


class SignalSimulation:
    """One coherent sample buffer for both plots, with warm temporal filters."""
    def __init__(self, values, number):
        self.live = values.copy()
        self.peaks = PEAK_SETS[number-1]
        self.number = number
        self.random=Random(2107+number);self.noise_memory=[0.0]*SAMPLE_COUNT
        self.raw_s = [0.0]*SAMPLE_COUNT
        self.raw_e = [0.0]*SAMPLE_COUNT
        self.filtered_s = [0.0]*SAMPLE_COUNT
        self.filtered_e = [0.0]*SAMPLE_COUNT
        self.limited_s = [0.0]*SAMPLE_COUNT
        self.limited_e = [0.0]*SAMPLE_COUNT
        self.ready = False
        self.smoothing = 0.0
        self.level = 0.0
        self.fade_start = 0.0
        self.fade_target = 0.0
        self.fade_time = 0.0
        self.fade_duration = 1.5
        self.elapsed = 0.0
        self.config = dict(x_min=X_MIN,x_max=X_MAX,max_points=SAMPLE_COUNT,auto_bandwidth=False,sampling_rate=20,baseline_main=0.,baseline_error=0.)
        self.x_values = [X_MIN+i*X_STEP for i in range(SAMPLE_COUNT)]

    def configure(self,settings):
        old=(self.config['x_min'],self.config['x_max'],self.config['max_points'])
        self.config.update(settings)
        new=(self.config['x_min'],self.config['x_max'],self.config['max_points'])
        if new!=old:
            n=int(new[2]);self.x_values=[new[0]+i*(new[1]-new[0])/(n-1) for i in range(n)]
            for name in ('raw_s','raw_e','filtered_s','filtered_e','limited_s','limited_e'):setattr(self,name,[0.]*n)
            self.ready=False
            self.noise_memory=[0.0]*n

    def emission(self, enabled):
        self.fade_start = self.level
        self.fade_target = float(enabled)
        self.fade_time = 0.0

    def center(self, center):
        span = max(.2, min(1.3, self.live['amplitude']/20))
        return 58.2+(center-58.2)*span+(self.live['offset']-58.2)+.2*(self.live['temperature']-24)+self.drift()

    def drift(self):
        return sin(self.elapsed*(.32+.033*self.live['frequency'])+self.number)*.035

    def advance(self, dt, elapsed, targets, stabilised):
        self.elapsed = elapsed
        self.fade_time = min(self.fade_duration,self.fade_time+dt)
        t = self.fade_time/self.fade_duration
        ease = t*t*(3-2*t)
        self.level = self.fade_start+(self.fade_target-self.fade_start)*ease
        for key, value in targets.items():
            self.live[key] += (value-self.live[key])*(1-exp(-dt/.25))
        self.smoothing += (float(stabilised)-self.smoothing)*(1-exp(-dt/.2))
        values=self.live
        intensity=max(0,values['current']/229.547)**.45
        intensity *= max(.1,min(1.3,values['umax']/2.81))
        intensity=min(1.18,intensity)
        noise_phase=elapsed*(5+values['frequency']*.3)+self.number*3.1
        error_gain=10**((values['pid']+35.5)/80)
        centers=[(self.center(c),height,width) for c,height,width in self.peaks]
        cutoff=min(8.,self.config.get('sampling_rate',20)*.2)
        alpha=1-exp(-dt/.24)
        bandwidth_alpha=1-exp(-dt*2*3.141592653589793*cutoff)
        for i,x in enumerate(self.x_values):
            s,e=.48,0.0
            for center,height,width in centers:
                u=(x-center)/width
                denominator=1+u*u
                s += height*intensity/denominator
                e += height*intensity*.24*(-2*u)/denominator**2
            residual=(sin(x*47+noise_phase)+.48*sin(x*113-noise_phase*1.3)+.23*sin(x*211+noise_phase*.7))
            # Independent broadband detector noise plus correlated electronic
            # pickup. Stabilisation retains its warm temporal noise filter.
            self.noise_memory[i]=.35*self.noise_memory[i]+self.random.gauss(0,.075)
            detector=self.noise_memory[i]
            s += .072*residual+detector+.004*values['feedforward']*(x-58.2)
            e = e*error_gain-values['setpoint']+.095*residual+.7*detector+self.random.gauss(0,.038)+.001*values['feedforward']*(x-58.2)
            s=max(-.85,min(9.65,s));e=max(-2.35,min(2.35,e))
            self.raw_s[i],self.raw_e[i]=s,e
            if not self.ready:
                self.filtered_s[i],self.filtered_e[i]=s,e
                self.limited_s[i],self.limited_e[i]=s,e
            else:
                self.filtered_s[i] += alpha*(s-self.filtered_s[i])
                self.filtered_e[i] += alpha*(e-self.filtered_e[i])
                mixed_s=s+self.smoothing*(self.filtered_s[i]-s)
                mixed_e=e+self.smoothing*(self.filtered_e[i]-e)
                self.limited_s[i]+=bandwidth_alpha*(mixed_s-self.limited_s[i])
                self.limited_e[i]+=bandwidth_alpha*(mixed_e-self.limited_e[i])
        self.ready=True

    def sample(self,x):
        if not self.ready or self.level == 0:
            return 0.0,0.0
        count=len(self.x_values)
        position=max(0,min(count-1,(x-self.x_values[0])/(self.x_values[-1]-self.x_values[0])*(count-1)))
        i=min(count-2,int(position));fraction=position-i
        output=[]
        for raw,filtered,limited,key in ((self.raw_s,self.filtered_s,self.limited_s,'baseline_main'),(self.raw_e,self.filtered_e,self.limited_e,'baseline_error')):
            a=limited[i] if self.config['auto_bandwidth'] else raw[i]+self.smoothing*(filtered[i]-raw[i])
            b=limited[i+1] if self.config['auto_bandwidth'] else raw[i+1]+self.smoothing*(filtered[i+1]-raw[i+1])
            output.append((a+(b-a)*fraction-self.config[key])*self.level)
        return tuple(output)
