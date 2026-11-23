#!/usr/bin/env python3
"""v1.1 호환 래퍼: `ledger.py init`과 같다. 사용: init_coverage.py LEDGER [--baseline 이전조사표]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402

if __name__ == '__main__':
    sys.exit(ledger.main(['init'] + sys.argv[1:]))
