#!/usr/bin/env python3
"""skills/mobility-ops-job-hunter → dist/ 의 배포 zip 2종을 만든다.

- mobility-ops-job-hunter-v<ver>.zip      : 스킬 폴더 그대로 (Claude 스킬, SKILL.md를 읽는 GPT/Codex 환경)
- mobility-ops-job-hunter-v<ver>-gpt.zip  : ChatGPT 맞춤형 GPT용 (Instructions + 평평한 knowledge/ 파일)
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'mobility-ops-job-hunter'
DIST = ROOT / 'dist'
STAMP = (2026, 11, 23, 0, 0, 0)  # 재현 가능한 zip을 위해 고정
KNOWLEDGE = ['SKILL.md', 'scripts/ledger.py', 'references/coverage_contract.json', 'references/company_watchlist.md',
             'references/channels_and_search.md', 'references/ledger_schema.md', 'references/host_setup.md']


def put(z, arc, data):
    info = zipfile.ZipInfo(arc, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def main():
    ver = re.search(r'^## (\d+\.\d+\.\d+)', (SKILL / 'CHANGELOG.md').read_text(encoding='utf-8'), re.M).group(1)
    DIST.mkdir(exist_ok=True)
    files = sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    a = DIST / f'mobility-ops-job-hunter-v{ver}.zip'
    with zipfile.ZipFile(a, 'w') as z:
        for p in files:
            put(z, f'mobility-ops-job-hunter/{p.relative_to(SKILL).as_posix()}', p.read_bytes())
    b = DIST / f'mobility-ops-job-hunter-v{ver}-gpt.zip'
    names = [Path(k).name for k in KNOWLEDGE]
    if len(set(names)) != len(names):
        sys.exit('knowledge 파일명 중복')
    with zipfile.ZipFile(b, 'w') as z:
        put(z, 'GPT_INSTRUCTIONS.md', (SKILL / 'gpt' / 'GPT_INSTRUCTIONS.md').read_bytes())
        put(z, 'README.md', (SKILL / 'gpt' / 'README.md').read_bytes())
        for k in KNOWLEDGE:
            put(z, f'knowledge/{Path(k).name}', (SKILL / k).read_bytes())
    ins = len((SKILL / 'gpt' / 'GPT_INSTRUCTIONS.md').read_text(encoding='utf-8'))
    if ins > 8000:
        sys.exit(f'GPT_INSTRUCTIONS.md {ins}자 > 8000자')
    print(f'{a.name} ({len(files)} files), {b.name} (instructions {ins}자, knowledge {len(KNOWLEDGE)} files)')


if __name__ == '__main__':
    main()
