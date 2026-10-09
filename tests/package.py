"""Create a portable source archive, omitting local environments and bytecode."""
from pathlib import Path
import ast
import zipfile

root = Path(__file__).resolve().parents[1]
for script in root.glob('*.sh'):
    script.write_bytes(script.read_bytes().replace(b'\r\n', b'\n'))
for source in root.rglob('*.py'):
    if '.venv' not in source.parts:
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
destination = root.parent / 'Nexatom-mock1-PySide6-RPi5.zip'
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob('*')):
        if not file.is_file() or any(p in {'.venv', '__pycache__', '.git'} for p in file.parts):
            continue
        if file.name in {'home.png'} or file.suffix == '.pyc':
            continue
        archive.write(file, str(Path(root.name) / file.relative_to(root)))
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    for required in ('main.py', 'run.sh', 'setup_pi.sh', 'assets/logo.png', 'qml/Main.qml', 'tests/ui-results.json'):
        assert f'{root.name}/{required}' in names
print(destination)
print(f'{len(names)} files; {destination.stat().st_size:,} bytes')
