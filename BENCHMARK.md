# v1.17 benchmark and qualification

## Run the separate configuration

Windows: double-click `bench.cmd`. Pi desktop: `bash bench.sh`. Synthetic mode uses raw electrical replay through the production decoders, IPC, mailbox, gesture service and router; it does not request GPIO. Select `--benchmark-hardware` to read the actual Pi instead. Close the normal app first so pins have one owner.

The slider changes both channels from 100 to 10,000 samples per signal. Normal preferences are untouched. The default peak-preserving renderer reduces redundant display samples; the optional **Stress raster: draw every point** switch measures the unreduced raster workload. It can reduce frame rate. Start/stop synthetic input, probe the owner and save a timestamped JSON report. Synthetic and physical calibration/preferences have separate directories.

## Measured on the development computer

Windows 11 AMD64, Python 3.13.7, Qt 6.8.0.2 software renderer; native 1600 ? 720 logical application. Final run: 20 seconds per load, three simultaneously active knobs (200 encoder edges/second each; approximately 300 accepted steps/second total) and two 40 ms press/release contacts. Each stage includes pan/zoom, command probes and a deliberate 250 ms GUI stall.

Presented FPS is the Qt frameSwapped rate, not the physical display scanout. CPU is percent of one core for the application process, including its threads; 100% is one fully used core. Child-process CPU/RSS is not included. Paint time is per plot. Values below are measurements, not Pi predictions.

| Points/signal | Mean presented FPS | Mean CPU % | Peak app RSS MiB | Knob p95 ms | Button p95 ms | Command?owner p95 ms | Plot paint p95 ms | UI heartbeat delay p95 ms | Peak queued batches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 27.63 | 103.83 | 176.79 | 57.47 | 55.93 | 4.07 | 6.98 | 41.90 | 105 |
| 1000 | 11.29 | 105.75 | 180.68 | 111.48 | 106.73 | 2.83 | 20.35 | 117.73 | 124 |
| 10000 | 7.11 | 108.21 | 184.70 | 149.15 | 149.47 | 3.65 | 34.72 | 196.00 | 156 |

Final delivery: **18,060 / 18,060 knob steps** and **1,506 / 1,506 presses**. No runtime QML errors. All recorded input drained after the source stopped. Idle heartbeats can arrive immediately after an empty-queue check; exact event totals are checked independently.

Worst measured knob-to-application delay in the final run: **401.61 ms**, including forced stalls. This is not hard realtime. The all-point raster stress option is available but the table uses the production reduction policy.

An earlier 60-second-per-load run delivered 54,030 steps and 4,504 presses exactly, but revealed 2.1-second worst-case delay at 10,000 points with the smaller GUI dispatch budget. That evidence is preserved as `tests/v117/soak.json`; the final scheduler increases its work slice under backlog. The table and `tests/v117/stress.json` describe the final code. These runs are stress checks, not an overnight endurance certification.

## Timing interpretation

- Button timing starts at capture-time debounce completion. Add the configured stable interval for raw-contact-to-application timing. Encoder timing starts at the edge completing a decoded step.
- Delivery metrics distinguish reaching the application from completing its handler. Coalesced steps retain the oldest timestamp, conservatively measuring their queue delay.
- Command queue wait, command-to-owner, driver-operation duration and GUI-visible round trip are separate. A completed driver ACK can bypass the presentation backlog.
- Physical GPIO edge-to-owner timing comes from kernel timestamps in hardware mode. Synthetic replay cannot measure interrupt latency.
- No MCU/laser output transport exists here. GPIO-command-to-physical-hardware ACK latency is unavailable, rather than invented.
- Distributions retain up to 20,000 samples per metric; counts and maximums cover the entire measurement interval.

## Regression and endurance commands

```powershell
runtime\python.exe -m unittest discover -s tests -p "test_*.py"
runtime\python.exe tests/stress.py --native --seconds 60
# Extended 30-minute, three-load soak:
runtime\python.exe tests/stress.py --native --seconds 600
```

On Pi, use `.benchvenv/bin/python` after running `bench.sh`. Run GUI benchmarks serially without another app competing for the same display/CPU. The injected-driver suite verifies rapid buffered edges, debounce, simultaneous controls, first-event overflow, sequence wrap, repeated configure/close, partial failure, chip renumbering, 2,000 queued commands and unexpected owner exit. The process test deliberately blocks Qt for 650 ms while capture continues.

## Target Pi acceptance still required

1. Start physical benchmark mode; verify the reported RP1 chip, polarity, release-to-arm and all configured controls. Calibrate in this isolated profile if needed.
2. Measure 100 / 1,000 / 10,000 points with touch/knob activity. Export reports, including kernel edge-to-worker and button/encoder-to-handler distributions.
3. Use known-count electrical pulses or a logic analyser to compare generated edges against kernel/decoder counts. Include reversals, shared joystick/push contacts, short valid presses and simultaneous inputs.
4. Run an extended soak with recording/export and other expected OS load. Set acceptance thresholds for latency, rendering and queue high-water on the actual carrier/display.
5. Exercise safe temporary failure, Retry GPIO, repeated stop/start and calibration. Confirm no remaining owned lines after exit, no stuck autorepeat and no duplicate command.
6. Qualify interrupt support. A reported polling fallback cannot guarantee pulses occurring entirely between reads. Any sequence gap or invalid transition must be investigated.

Normal Linux userspace, finite kernel buffers and finite RAM cannot guarantee arbitrary pulse rates or safety certification. The UI lock is not a substitute for an independent hardware emission interlock.

Sources and implementation policy: [HARDWARE.md](HARDWARE.md). Raw final evidence: [stress.json](tests/v117/stress.json).
