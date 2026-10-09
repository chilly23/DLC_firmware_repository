# v1.16 release notes

Base: v1.15. Date: 8 October 2026. Scope: Lobby completion and user-facing organisation.

- Retained the 20-card Bento layout and the original More animation; replaced generic routes with dedicated Control Parameters, Laser Config, Sub Parameters and Home Controls pages.
- Added shared parameter validation/persistence, CC/TC/PC catalogues, read-only readbacks and a two-column parameter tree.
- Moved diagnostic actions into Lobby Diagnostics; added check results, JSON export and direct Screen Check.
- Expanded monitoring to twelve host/runtime values with lifecycle-bound polling.
- Completed screenshot naming, category browsing, image thumbnails/previews and text/log previews; exports use the same saved-file library.
- Preserved shortcut assignment and touch/mouse reordering; Screenshot remains assignable.
- Restricted DLC View, Legal Information and Digital Manual to the requested placeholders.
- Added red/orange/green/white status indication to the fullscreen Logs window.
- Reduced routine notification noise, suppressed duplicates, retained the two-card limit and added countdown rings around dismiss controls in both rendering paths.
- Added touch-sized dropdowns and native UI regression coverage, including a press held across live readback updates.

## Boundaries

GPIO decoding, queueing, driver access, calibration storage, firmware integration and startup provisioning are unchanged. The high-level input router only gains forwarding to the independently opened diagnostic screen. Laser transport and readbacks remain simulated. TC I/D fields are persisted configuration; this release does not implement a hardware PID loop.

No existing version is overwritten. See README.md for operation and architecture, RELEASE.json for changed-file hashes, and VALIDATION.json for the final checks.
