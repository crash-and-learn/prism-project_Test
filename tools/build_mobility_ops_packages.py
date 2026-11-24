#!/usr/bin/env python3
"""skills/mobility-ops-job-hunter → dist/mobility-ops-job-hunter-v<ver>.zip (스킬 폴더 그대로, GPT 지침은 gpt/ 포함)."""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'mobility-ops-job-hunter'
DIST = ROOT / 'dist'
STAMP = (2026, 11, 24, 0, 0, 0)  # 재현 가능한 zip


def main():
    ver = re.search(r'^## (\d+\.\d+\.\d+)', (SKILL / 'CHANGELOG.md').read_text(encoding='utf-8'), re.M).group(1)
    ins = len((SKILL / 'gpt' / 'GPT_INSTRUCTIONS.md').read_text(encoding='utf-8'))
    if ins > 8000:
        sys.exit(f'GPT_INSTRUCTIONS.md {ins}자 > 8000자')
    DIST.mkdir(exist_ok=True)
    files = sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    out = DIST / f'mobility-ops-job-hunter-v{ver}.zip'
    with zipfile.ZipFile(out, 'w') as z:
        for p in files:
            info = zipfile.ZipInfo(f'mobility-ops-job-hunter/{p.relative_to(SKILL).as_posix()}', STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    print(f'{out.name} ({len(files)} files, GPT 지침 {ins}자)')


if __name__ == '__main__':
    main()
