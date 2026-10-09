"""Read-only chip identification and concise device errors; no persistent ownership."""
from glob import glob
import errno, logging
LOG=logging.getLogger("nexatom.gpio")

def gpio_module():
    import gpiod
    if not hasattr(gpiod, 'request_lines'):
        raise RuntimeError('GPIO library needs updating. Run Repair setup.')
    return gpiod


def discover(gpiod):
    result = []
    for path in sorted(glob('/dev/gpiochip*')):
        try:
            with gpiod.Chip(path) as chip:
                info = chip.get_info()
                result.append(dict(path=path, label=info.label, lines=info.num_lines))
        except OSError as exc:
            result.append(dict(path=path, label=str(exc), lines=0, error=exc.errno))
    return result


def select_chip(gpiod, configured):
    if configured != 'auto':
        return configured
    chips = discover(gpiod)
    LOG.debug('GPIO chip inventory: %s', chips)
    candidates = [c['path'] for c in chips if 'rp1' in c['label'].lower() and c['lines'] >= 28]
    if len(candidates) == 1:
        return candidates[0]
    # Kernel chip numbering/labels can change. Verify BCM line names rather
    # than guessing chip0 or accidentally requesting an unrelated GPIO bank.
    if not candidates:
        for entry in chips:
            if entry['lines'] < 28:
                continue
            try:
                with gpiod.Chip(entry['path']) as chip:
                    if all(chip.get_line_info(pin).name == f'GPIO{pin}' for pin in (2, 3, 4, 17, 27)):
                        candidates.append(entry['path'])
            except OSError as exc:
                entry['error']=exc.errno  # Device disappeared between inventory and inspection.
    if len(candidates) == 1:
        return candidates[0]
    if any(c.get('error') in (errno.EACCES, errno.EPERM) for c in chips):
        raise PermissionError(errno.EACCES, 'GPIO chip access denied')
    if not chips:
        raise RuntimeError('No GPIO device found. Check Raspberry Pi OS.')
    LOG.error('GPIO chip selection failed: %s', chips)
    raise RuntimeError('GPIO chip not identified. Check logs/controls.log.')


def short_error(exc):
    """Actionable single-line operator text; full exceptions go to controls.log."""
    code = getattr(exc, 'errno', None)
    if isinstance(exc, ImportError):
        return 'GPIO library missing. Run Repair setup.'
    if isinstance(exc, PermissionError) or code in (errno.EACCES, errno.EPERM):
        return 'GPIO access denied. Run Repair setup.'
    if code == errno.EBUSY:
        return 'GPIO in use. Close other GPIO apps, then Retry GPIO.'
    if code in (errno.ENOENT, errno.ENODEV):
        return 'GPIO device missing. Check the selected chip.'
    if code in (errno.ENXIO, errno.EINVAL, errno.EOPNOTSUPP):
        return 'GPIO request unsupported. See Control settings and logs.'
    text = ' '.join(str(exc).split())
    return text if len(text) <= 108 else text[:105] + '...'

