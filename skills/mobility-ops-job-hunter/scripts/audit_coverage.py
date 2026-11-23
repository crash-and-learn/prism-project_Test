#!/usr/bin/env python3
"""v1.1 호환 래퍼: `ledger.py audit`과 같다. 종료 코드 0=완료 1=부분 조사 2=FAIL."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402

if __name__ == '__main__':
    sys.exit(ledger.main(['audit'] + sys.argv[1:]))
