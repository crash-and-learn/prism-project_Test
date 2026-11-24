# ChatGPT에서 쓰기 (Mobility Ops Job Hunter v1.2.1)

**스킬로 쓰는 경우(권장)**: 이 zip 전체를 스킬로 올려 이전 버전을 교체한다. `@Mobility Ops Job Hunter`로 부른다.

**맞춤형 GPT로 쓰는 경우**
1. 지침(Instructions): `gpt/GPT_INSTRUCTIONS.md` 내용 전체를 붙여넣는다.
2. 지식(Knowledge): `SKILL.md`, `scripts/ledger.py`, `references/` 안 파일 5개를 올린다.
3. 기능: 웹 검색과 코드 실행(코드 인터프리터)을 켠다. 브라우저 조작 모드가 있으면 그 모드에서 실행한다.

매 턴 끝에 장부 JSON을 내려받고, 다음 회차에는 그 파일 하나만 첨부한다.
