# ChatGPT 맞춤형 GPT 설정 (Mobility Ops Job Hunter v1.2)

1. ChatGPT → GPT 만들기 → 구성(Configure).
2. **Instructions**: `GPT_INSTRUCTIONS.md` 전체를 붙여넣는다.
3. **Knowledge**: `knowledge/` 폴더의 파일 7개를 모두 업로드한다.
4. **Capabilities**: 웹 검색, 코드 인터프리터·데이터 분석을 켠다.
5. 대화 시작 예: "이전 조사표 올렸어. 10개 유형 조사 진행해줘." (+ 이전 xlsx 또는 장부 json 첨부)
6. 대화가 끝나기 전에 장부 JSON과 보고서 MD를 꼭 내려받는다. 다음 회차에 다시 올린다.

동작 확인(선택): 코드 인터프리터에서 `python /mnt/data/ledger.py init /mnt/data/t.json` 후 `python /mnt/data/ledger.py audit /mnt/data/t.json`을 실행하면 `FAIL ... {'not_done': 10}`이 나와야 한다(아직 아무것도 조사하지 않았으므로 정상).
