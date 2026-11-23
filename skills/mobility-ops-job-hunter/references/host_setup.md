# 호스트별 설치·실행 (Claude / GPT 공용)

스크립트는 Python 3.9 이상 표준 라이브러리만 쓴다. 이전 조사표가 xlsx일 때만 `openpyxl`이 필요하다(ChatGPT 코드 실행 환경에는 기본 설치돼 있음). `ledger.py`는 `coverage_contract.json`을 다음 순서로 찾는다: `--contract` → 환경변수 `MOJH_CONTRACT` → `../references/` → 스크립트와 같은 폴더 → 현재 폴더 → `/mnt/data/`.

## Claude (Claude Code · Claude 앱 스킬)

- `dist/mobility-ops-job-hunter-v1.2.0.zip`을 스킬로 업로드하거나, 폴더를 `~/.claude/skills/` 또는 프로젝트의 `.claude/skills/`에 둔다.
- 명령: `python <스킬 폴더>/scripts/ledger.py ...`
- 웹 조회는 Claude의 웹 검색·가져오기 도구로 하고, 장부 기록은 코드 실행으로 한다.

## GPT — 스킬(SKILL.md) 폴더를 지원하는 환경 (Codex 등)

- 같은 `mobility-ops-job-hunter-v1.2.0.zip`을 그 환경의 스킬 폴더 규칙대로 설치한다. SKILL.md 형식은 동일하다.

## GPT — ChatGPT 맞춤형 GPT(GPTs) / 프로젝트

`dist/mobility-ops-job-hunter-v1.2.0-gpt.zip`을 푼다.

1. **Instructions**: `GPT_INSTRUCTIONS.md` 내용을 그대로 붙여넣는다(8,000자 이하).
2. **Knowledge**: `knowledge/` 폴더의 파일 전부를 올린다. 폴더 없이 평평하게 올라가도 되도록 구성돼 있다.
3. **Capabilities**: 웹 검색과 **코드 인터프리터·데이터 분석**을 모두 켠다. 코드 실행이 꺼져 있으면 자동 감사를 할 수 없다.
4. 실행: `python /mnt/data/ledger.py init /mnt/data/조사_YYYYMMDD.json --baseline /mnt/data/<이전조사표>.xlsx`
5. 대화가 끝나면 `/mnt/data`가 사라진다. 장부 JSON과 보고서 MD를 매번 내려받아 다음 회차에 다시 올린다.

## 공통 주의

- 한 대화에서 10개 유형을 다 못 끝내면 장부 파일을 받아 두고, 다음 대화에서 그 장부를 올려 이어서 `start-type`부터 진행한다. 이미 종료한 유형은 다시 열 수 없다. 재조사는 새 회차 장부로 한다.
- 어느 호스트든 실제로 열지 않은 페이지나 실행하지 않은 검색을 기록하면 안 된다. 감사는 기록의 정합성만 확인한다.
