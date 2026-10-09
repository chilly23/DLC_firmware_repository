# v1.17 release notes

Base: v1.16.0 only. Date: 8 October 2026.

- Replace mixed polling/direct access with a single-owner GPIO capture process, buffered edge handling, explicit input mailbox and serialized driver commands.
- Preserve capture timestamps and intermediate contact states; fix three reproduced delayed-batch gesture failures.
- Isolate failed controls, detect kernel sequence gaps, support explicit repair and safe transient recovery, and clean up requests/processes without concurrent replacement owners.
- Eliminate the full-duplex command-burst deadlock with one in-flight command and continuous reply/event draining.
- Add queue, driver, input-handler and GUI/render timing measurements.
- Remove repeated scene searches, hidden-page refreshes and synchronous audit-database waits from the hot input path.
- Vectorize simulation and retain extrema during display reduction. Reduce Home graph padding/gaps only.
- Add separate synthetic/physical benchmark profiles, 100–10,000-point slider, raw-raster stress and report export.
- Preserve Lobby, More wheel, wiring, device/display backends and unrelated application workflows.

The application runs with simulated laser acquisition, as before. Physical GPIO timing and electrical acceptance remain unverified on the user's Pi. No hardware/MCU acknowledgement is invented. Finite-buffer overflow and degraded polling are reported explicitly; no hard-realtime claim is made.

[README](README.md), [architecture/root causes](HARDWARE.md), [benchmark results](BENCHMARK.md), [validation manifest](VALIDATION.json), [source inventory](RELEASE.json).
