"""Fail-closed source-release file inventory and limited sensitive-pattern scan.

This guard is not a secret scanner certification. Review the actual staged diff,
provenance, remote destination and Git history independently before publishing.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOTS = {'tests', 'web', 'docs', 'scripts', 'examples', '.agents', '.github'}
ROOT_FILES = {'README.md', 'README.ja.md', 'LICENSE', 'DEPENDENCIES.md', 'PROVENANCE.md',
              'CONTRIBUTING.md', 'SECURITY.md', '.gitignore', 'requirements.txt', 'Makefile'}
EXTENSIONS = {'.py', '.js', '.cjs', '.css', '.html', '.md', '.txt', '.json', '.yml', '.yaml'}
IGNORED = {'.git', '__pycache__', '.venv', '.pytest_cache', 'output', 'work', 'build', 'dist'}
PATTERNS = {
    'absolute-workstation-path': re.compile('/' + r'(?:workspace|home|Users)/[^\s\"\'<>]+'),
    'embedded-image-payload': re.compile('data:image/' + r'\w+;base64,[A-Za-z0-9+/]{80,}'),
    'private-key': re.compile('-----BEGIN ' + r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'provider-key': re.compile(r'\b(?:gh' + r'[posu]_[A-Za-z0-9]{30,}|sk-' + r'[A-Za-z0-9_-]{30,})'),
    'cloud-upload-identity': re.compile(r'(?:library_file_' + r'id|sedi' + r'ment://|chatgpt\.com/backend-api/)'),
}

def inventory(root):
    root = Path(root).resolve()
    files, errors = [], []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append(f'Symlink is not allowed: {relative}'); continue
        if not path.is_file():
            continue
        if (len(relative.parts) == 1 and relative.name not in ROOT_FILES and path.suffix != '.py') or (len(relative.parts) > 1 and relative.parts[0] not in ROOTS):
            errors.append(f'Unrecognized release path: {relative}'); continue
        if path.suffix not in EXTENSIONS and relative.name not in {'LICENSE', 'Makefile', '.gitignore'}:
            errors.append(f'Binary/unexpected file type: {relative}'); continue
        data = path.read_bytes()
        try:
            content = data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'Non-UTF8 source file: {relative}'); continue
        for kind, pattern in PATTERNS.items():
            if pattern.search(content):
                errors.append(f'{kind}: {relative}')
        files.append({'path': relative.as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return files, errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1]);p.add_argument('--manifest', type=Path);a=p.parse_args()
    files, errors=inventory(a.root)
    report={'schema':'source-release-inventory/1','files':files,'errors':errors,'passed':not errors,
            'limitation':'Pattern/file guard only; independent staged-content and history review required.'}
    if a.manifest:a.manifest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'files':len(files),'bytes':sum(x['bytes'] for x in files),'errors':errors,'passed':not errors},indent=2))
    return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
