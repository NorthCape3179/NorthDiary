"""Package only reviewed project files; no user data, environment or Git state."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'LICENSE', 'COPYRIGHT', 'README.md', 'THIRD_PARTY_NOTICES.md',
             'requirements.txt', '.gitignore', 'AGENTS.md', 'main.py',
             'start.cmd', 'start-demo.cmd', '使用说明.txt', '展示模式说明.txt'}
TOP_DIRS = {'northdiary', 'tests', 'docs', 'packaging', 'licenses', 'scripts'}
ALLOWED = {'.py', '.md', '.txt', '.cmd', '.spec', '.iss', '.png', '.ico', '.json'}
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def make_bundle(destination):
    destination = Path(destination).resolve()
    entries = []
    for file in sorted(ROOT.rglob('*')):
        if not file.is_file():
            continue
        relative = file.relative_to(ROOT)
        if '__pycache__' in relative.parts or file.is_symlink():
            continue
        if len(relative.parts) == 1:
            if relative.name not in TOP_FILES:
                continue
        elif relative.parts[0] not in TOP_DIRS:
            continue
        elif relative.parts[0] != 'licenses' and file.suffix.lower() not in ALLOWED:
            continue
        if any(part.lower() in {'attachments', 'backups', '.git', '.venv'} for part in relative.parts):
            raise ValueError(f'Unexpected private data path: {relative}')
        if file.name == 'github.credentials' or '.sqlite' in file.name.lower() or file.suffix.lower() in {'.db', '.ndiary', '.epub', '.ini', '.zip'}:
            raise ValueError(f'Forbidden source file: {relative}')
        data = file.read_bytes()
        if file.suffix.lower() not in {'.png', '.ico'} and SECRET.search(data):
            raise ValueError(f'Credential pattern in {relative}; bundle aborted')
        entries.append((relative.as_posix(), data))
    names = {name for name, _ in entries}
    for required in ['LICENSE', 'COPYRIGHT', 'main.py', 'northdiary/resources/northdiary.ico',
                     'packaging/NorthDiary.spec', 'packaging/NorthDiary.iss', 'packaging/BUILD.md']:
        assert required in names, required
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in entries}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
        archive.writestr('SOURCE-MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(json.dumps({'source_files': len(entries), 'bytes': destination.stat().st_size,
                      'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    make_bundle(sys.argv[1])
