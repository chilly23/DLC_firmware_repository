# Nexatom Digital Laser Controller — v1.16

This checkout contains **v1.16**. The default branch contains the latest application only. Older apps are available through [version tags](https://github.com/chilly23/DLC_firmware_repository/tags) and [HISTORY.md](HISTORY.md).

## Download and run

- **Windows, complete one-click app:** download the Windows ZIP from [Latest release](https://github.com/chilly23/DLC_firmware_repository/releases/latest), extract it, then double-click `start.cmd`. That package contains the current application and its bundled runtime.
- **Raspberry Pi OS:** download [current source](https://github.com/chilly23/DLC_firmware_repository/archive/refs/heads/main.zip), extract it, and run `bash start.sh` from the Pi graphical desktop. The latest launcher provisions dependencies.
- **Current source only:** use GitHub Code → Download ZIP, or `git clone --depth 1 https://github.com/chilly23/DLC_firmware_repository.git`.
- **An older checkpoint:** open its tag in [HISTORY.md](HISTORY.md) and download that source. Follow that checkpoint's application instructions and dependencies.

## Version navigation

```bash
git fetch origin --tags
git switch --detach v1.16
# Return to the latest app:
git switch main
# Develop from a checkpoint:
git switch -c my-change v1.17
```

Source downloads exclude installed Python/Qt packages and generated user data. The Windows release ZIP supplies its runtime. Git history stores changes between checkpoints; it does not put every version folder inside the current download.

[Application documentation](APP.md) · [Release notes](RELEASE.md) · [Version history](HISTORY.md) · [Import provenance](SOURCE.json)

The application uses PySide6. Physical GPIO qualification applies to the target Pi; archived validation is documented per checkpoint. See APP.md for the full application guide.
