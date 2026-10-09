# v1.15 - Lobby and navigation

7 October 2026. Base: v1.14, preserved unchanged. Application version: 1.15.0; the existing firmware identifier is unchanged.

- Restore the exact v1.9 More wheel implementation, changing only two destinations to Logs and Lobby.
- Add a packed, square-corner Bento Lobby: 20 differently sized grey rectangles, 17 tools, three visible placeholders and dedicated icons.
- Move Diagnostics to Lobby and Logs to a separate fullscreen window reachable directly from More. Preserve the log journal, filters, exports, pause and clear controls.
- Add full-display screenshots named `phototype_<timestamp>.png`, including shortcut-button assignment and Wayland grim support.
- Centralize shortcut assignment and mouse/touch side-panel reordering in Buttons Panel, with persisted preferences and knob support.
- Add Small/Medium/Large Home graphs; use larger graphs by default and share geometry with drag previews/drop targets.
- Make Settings history selection fill and execute the search immediately.
- Wire the other requested Lobby destinations to existing interfaces or dedicated native pages. DLC opens the separately installed GPU assembly viewer.

See [README.md](README.md) for routes, deployment and dependencies, and [VALIDATION.json](VALIDATION.json) for the checks performed. This update was verified on Windows; physical CM5 acceptance remains outstanding.
