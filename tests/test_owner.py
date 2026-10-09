"""Driver-contract tests: real reactor/decoders with exclusive fake line requests."""
import errno
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hardware.capture import Reactor
from hardware.config import DEFAULTS
from hardware.events import ordered_frames


class Selector:
    def __init__(self):self.registered={}
    def register(self,fd,events,data):
        assert fd not in self.registered
        self.registered[fd]=data
    def unregister(self,fd):return self.registered.pop(fd)
    def close(self):self.registered.clear()


class Connection:
    def __init__(self):self.messages=[]
    def send(self,message):self.messages.append(message)


class Driver:
    def __init__(self):
        self.used=set();self.live=[];self.next_fd=10;self.fail={};self.read_fail=set()
        self.EdgeEvent=types.SimpleNamespace(Type=types.SimpleNamespace(RISING_EDGE='rise'))
        self.line=types.SimpleNamespace(Direction=types.SimpleNamespace(INPUT='input'),
            Edge=types.SimpleNamespace(BOTH='both',NONE='none'),
            Bias=types.SimpleNamespace(PULL_UP='pullup'),Value=types.SimpleNamespace(ACTIVE=1))
        self.LineSettings=lambda **kw:kw
    def request_lines(self,path,**kw):
        pins=[p for group in kw['config'] for p in group]
        for p in pins:
            if p in self.fail:raise OSError(self.fail[p],'Injected request fault')
            if p in self.used:raise OSError(errno.EBUSY,'Duplicate request')
        self.used.update(pins);self.next_fd+=1
        req=Request(self,pins,self.next_fd,kw);self.live.append(req);return req


class Request:
    def __init__(self,driver,pins,fd,settings):
        self.driver=driver;self.pins=pins;self.fd=fd;self.settings=settings
        self.closed=False;self.events=[];self.levels=dict.fromkeys(pins,1);self.seq=0
    def release(self):
        assert not self.closed,'double close'
        self.closed=True;self.driver.used.difference_update(self.pins)
    def get_values(self,pins):
        if set(pins)&self.driver.read_fail:raise OSError(errno.EIO,'Injected disconnect')
        return [self.levels[p] for p in pins]
    def wait_edge_events(self,timeout=0):return bool(self.events)
    def read_edge_events(self,max_events):
        result=self.events[:max_events];del self.events[:max_events];return result
    def edge(self,pin,value,stamp,skip=0):
        self.seq+=1+skip;self.levels[pin]=value
        self.events.append(types.SimpleNamespace(line_offset=pin,event_type='rise' if value else 'fall',timestamp_ns=stamp,global_seqno=self.seq))


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.driver=Driver();self.connection=Connection();self.selector=Selector()
        self.config=deepcopy(DEFAULTS);self.config['chip']='/dev/gpiochip4'
        self.reactor=Reactor(self.connection,self.config,module=self.driver,line=self.driver.line,selector=self.selector)
        with patch('hardware.capture.time.monotonic_ns',return_value=0):self.reactor.configure(self.config)
    def tearDown(self):
        self.reactor.close();self.assertFalse(self.driver.used);self.assertFalse(self.selector.registered)
    def frames(self):
        return [(g,f) for m in self.connection.messages if m['kind']=='batch' for g,f in ordered_frames(m['groups'])]
    def test_every_connected_contact_uses_kernel_edges(self):
        self.assertEqual(len(self.driver.used),26)
        for req in self.driver.live:
            for settings in req.settings['config'].values():self.assertEqual(settings['edge_detection'],'both')
    def test_short_valid_press_survives_delayed_acquisition(self):
        # A complete 40 ms press happens while userspace is descheduled.
        g=self.reactor.groups['panel:left_shortcut'];r=g.request
        r.edge(16,0,10_000_000);r.edge(16,1,50_000_000)
        self.reactor.read_edges([g]);g.decoder.settle(100_000_000);self.reactor.publish(g);self.reactor.flush()
        self.assertEqual([e for key,f in self.frames() for e in f['events']], [('left_shortcut',True),('left_shortcut',False)])
    def test_rapid_encoder_batches_drain_without_losing_steps(self):
        g=self.reactor.groups['knob:0'];r=g.request
        stamp=1
        for cycle in range(3000):
            for pin,value in ((4,0),(22,0),(4,1),(22,1)):
                r.edge(pin,value,stamp);stamp+=10_000
        self.reactor.read_edges([g]);self.reactor.flush()
        self.assertFalse(r.events)
        self.assertEqual(sum(v for _,f in self.frames() for n,v in f['events'] if n=='rotation'),6000)
    def test_sequence_gap_at_first_event_is_detected_and_not_fabricated(self):
        g=self.reactor.groups['knob:0'];g.request.edge(4,0,1,skip=4)
        self.reactor.read_edges([g]);self.reactor.flush()
        self.assertEqual(self.reactor.metrics.snapshot()['counts']['kernel_missing_edges'],4)
        self.assertEqual(g.decoder.lost,1)
        self.assertTrue(any(m['kind']=='fault' and 'overflow' in m['message'] for m in self.connection.messages))
    def test_failure_after_request_creation_releases_descriptor(self):
        self.reactor.close();self.driver.read_fail={17}
        self.reactor.configure(self.config)
        self.assertIsNone(self.reactor.groups['knob:0'].request)
        self.assertTrue(self.driver.live[-8].closed)
        self.assertNotIn(17,self.driver.used)
        self.assertIn(24,self.driver.used)
    def test_retry_preserves_healthy_requests_and_recovers_only_failed_control(self):
        bad=self.reactor.groups['panel:left_shortcut'];good=self.reactor.groups['knob:1'].request
        self.reactor.fail_group(bad,OSError(errno.ENODEV,'unplugged'))
        self.assertIsNone(bad.request)
        self.reactor.command(dict(command='retry',id=1,sent_ns=1))
        self.assertIs(self.reactor.groups['knob:1'].request,good)
        self.assertIsNotNone(bad.request)
        self.assertTrue(self.connection.messages[-1]['ok'])
    def test_invalid_config_leaves_requests_owned(self):
        good=self.reactor.groups['knob:1'].request
        config=deepcopy(self.config);config['knobs'][0]['pins']['A']=24
        self.reactor.command(dict(command='configure',config=config,id=1,sent_ns=1))
        self.assertIs(self.reactor.groups['knob:1'].request,good)
        self.assertFalse(self.connection.messages[-1]['ok'])
    def test_auto_chip_rediscovery_after_device_renumbering(self):
        self.reactor.config['chip']='auto'
        for group in self.reactor.groups.values():self.reactor.fail_group(group,OSError(errno.ENODEV,'removed'))
        with patch('hardware.capture.select_chip',return_value='/dev/gpiochip9') as select:
            self.reactor.retry_failed(float('inf'))
        select.assert_called_once_with(self.driver,'auto')
        self.assertEqual(self.reactor.path,'/dev/gpiochip9')
        self.assertEqual(len(self.driver.used),26)
    def test_missing_auto_chip_remains_recoverable_without_busy_loop(self):
        self.reactor.config['chip']='auto'
        for group in self.reactor.groups.values():self.reactor.fail_group(group,OSError(errno.ENODEV,'removed'))
        with patch('hardware.capture.select_chip',side_effect=RuntimeError('No GPIO device found.')):
            self.reactor.retry_failed(float('inf'))
        self.assertTrue(all(g.request is None and g.retry_at<float('inf') for g in self.reactor.groups.values()))
    def test_repeated_configure_close_has_one_owner_and_no_fd_leaks(self):
        for _ in range(100):
            self.reactor.configure(self.config)
            self.assertEqual(len(self.driver.used),26)
            self.assertEqual(len(self.selector.registered),8)
        self.assertEqual(sum(not r.closed for r in self.driver.live),8)
    def test_unknown_command_is_rejected_and_acknowledged(self):
        self.reactor.command(dict(command='write_pin',id=7,sent_ns=1))
        self.assertFalse(self.connection.messages[-1]['ok'])
        self.assertEqual(len(self.driver.used),26)
    def test_sequence_wrap_does_not_report_overflow(self):
        g=self.reactor.groups['knob:0'];g.last_seq=0xffffffff
        g.request.seq=-1;g.request.edge(4,0,1)
        self.reactor.read_edges([g])
        self.assertEqual(g.decoder.lost,0)
    def test_lock_edges_and_two_knobs_preserve_global_timestamp_order(self):
        a=self.reactor.groups['knob:0'];b=self.reactor.groups['knob:3'];lock=self.reactor.groups['panel:lock']
        # Each partial pair makes one encoder detent. Lock's stable edge at31ms.
        a.request.edge(4,0,10_000_000);a.request.edge(22,0,11_000_000)
        lock.request.edge(20,0,1_000_000);lock.request.edge(20,1,50_000_000)
        b.request.edge(5,0,40_000_000);b.request.edge(19,0,41_000_000)
        self.reactor.read_edges([b,lock,a])
        for g in (a,b,lock):g.decoder.settle(90_000_000);self.reactor.publish(g)
        self.reactor.flush()
        frames=self.frames()
        self.assertEqual([g for g,f in frames],['knob:0','panel:lock','knob:3','panel:lock'])
        self.assertEqual([f['event_times'][0] for g,f in frames],sorted(f['event_times'][0] for g,f in frames))

if __name__=='__main__':unittest.main(verbosity=2)
