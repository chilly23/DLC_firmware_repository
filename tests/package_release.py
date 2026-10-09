"""Build source and self-contained Windows archives, excluding personal state."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results = []
for windows in (False, True):
    archive = ROOT.parent / ('Nexatom-v1.4-Windows.zip' if windows else 'Nexatom-v1.4-Source.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for path in sorted(ROOT.rglob('*')):
            relative = path.relative_to(ROOT)
            if not path.is_file() or any(part in {'__pycache__','.ruff_cache','.git'} for part in relative.parts):continue
            if relative.parts[0] in {'data','logs','exports'}:continue
            if not windows and relative.parts[0] in {'runtime','packages'}:continue
            bundle.write(path, 'mock1.4-pyside6/' + relative.as_posix())
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        count = len(bundle.infolist())
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = dict(file=archive.name, bytes=archive.stat().st_size, entries=count, sha256=digest)
    results.append(result)
    print(json.dumps(result), flush=True)
(ROOT.parent/'Nexatom-v1.4-Checksums.json').write_text(json.dumps(results,indent=2),encoding='utf8')
