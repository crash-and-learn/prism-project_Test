---
name: mobility-ops-job-hunter
description: 국내 모빌리티 10개 유형(64개 초기 후보)의 운영 개선·데이터 분석 채용을 유형 01→10 순서로 하나씩 조사한다. 각 유형에서 법인 확인, 이전 조사표 URL 재방문, 기업명 고정·비고정 신규 발굴, 768개 후보×채널 확인, 발견 공고 전건 판정을 장부(ledger.py)에 기록하고, 유형별 완료/부분 조사/미실시와 공고 목록·휴대폰 요약을 보고할 때 사용.
---

# Mobility Ops Job Hunter v1.2

국내 모빌리티 분야의 **데이터 기반 운영 개선** 직무를 찾는 조사 절차다. 결과는 한국어로 쓴다. 사용자가 범위를 줄이라고 하지 않는 한 표본으로 줄이지 않고, 중간 승인 질문 없이 가능한 작업을 계속한다. Claude와 GPT가 같은 절차를 따른다(호스트별 실행 방법: `references/host_setup.md`).

## 0. 용어와 원칙

- `SKILL_DIR`: 이 파일이 있는 폴더. 모든 명령은 `python SKILL_DIR/scripts/ledger.py ...`로 실행한다. 파일이 한 폴더에 평평하게 올라간 환경(예: ChatGPT의 `/mnt/data`)이면 `python /mnt/data/ledger.py ...`.
- **장부(ledger)**: 이번 회차의 유일한 작업 기록. 모든 기록은 `ledger.py add`로만 쓴다. JSON을 직접 고치지 않는다. 시각은 도구가 자동으로 찍는다.
- **판정 기준은 문장이 아니라 장부 검사다.** 아래 각 단계의 "끝나는 조건"은 `ledger.py todo`가 해당 항목을 0건으로 보고하는 것이다.
- 실제로 하지 않은 일을 기록하지 않는다. 열지 않은 URL, 실행하지 않은 검색, 보지 않은 결과 수를 쓰지 않는다. 하지 못한 일은 미실시로 남긴다.
- 회원 전용·robots·이용약관 제한을 우회하지 않는다. 막히면 `access_blocked`로 기록하고 대체 원문을 찾는다.

## 1. 조사 전 준비 (한 번)

1. `references/company_watchlist.md`, `references/ledger_schema.md`, `references/channels_and_search.md`를 읽는다.
2. 장부 생성. 이전 조사표가 있으면 반드시 함께 넣는다.
   `python SKILL_DIR/scripts/ledger.py init 조사_YYYYMMDD.json --baseline 이전조사표.xlsx`
   (이전 회차가 v1.2 장부 JSON이면 그 파일을 `--baseline`에 준다. 이전 자료가 정말 없을 때만 생략하고, 보고서에 `최초 기준선`이라고 쓴다.)
3. 출력에 `유형 미배정`이 있으면 각 URL을 보고 `assign-baseline 조사.json T0012=08 T0013=00:비모빌리티 공고` 식으로 모두 지정한다. 미배정이 1건이라도 있으면 `start-type`이 거부된다.

## 2. 유형 반복 — 01부터 10까지 순서대로, 한 번에 한 유형

각 유형마다 아래 A~G를 이 순서로 수행한다. 다른 유형의 기록은 도구가 거부한다.

**A. 시작** — `start-type 조사.json 01`. 출력된 남은 작업 목록이 이 유형의 할 일이다.

**B. 기업·법인 확인** — 유형의 각 후보마다 서비스명·브랜드·운영 법인·모회사·영문명을 검색해 실제 채용 법인을 정한다. `legal_hint`는 가설이다.
`add 조사.json candidate --json '{"id":"01-01","relation_status":"verified","resolved_company_id":"socar","relation_evidence_url":"https://...","queries":["일레클 운영사"],"note":"..."}'`
끝나는 조건: 이 유형 후보 중 `relation_status=unsearched`가 0건.

**C. 이전 경로 재점검** — `todo`에 나온 `재방문 누락 T....` URL을 모두 연다. 각 URL에 결과(`ok/redirected/closed/gone/blocked`)와 **그 페이지에서 본 관련 공고 수 `relevant_found`**를 기록한다. 공고 상세 URL(`job_posting`)이면 그 공고를 반드시 발견 목록(E)에 올린다.
`add 조사.json revisit --json '{"target_id":"T0002","result":"ok","final_url":"https://...","relevant_found":1}'`
끝나는 조건: 이 유형의 재방문 누락 0건, 재확인 대상 공고 중 발견 목록에 없는 것 0건.

**D. 신규 발굴** — 기존 주소가 모두 정상이어도 생략하지 않는다.
- 후보별 `E-<후보ID>` 작업: 브랜드·법인·모회사 별칭으로 새 채용 경로와 외부 플랫폼 공고를 검색한다.
- 유형별 `U-<유형>-*` 작업: **기업명을 넣지 않은** 검색식(`suggested_query`)을 web·원티드·사람인·잡코리아에서 각각 실행해 후보 목록 밖의 기업·공고를 찾는다.
- 각 검색에 `query`, `results_reviewed`(실제로 훑어본 결과 수, 기준 10개 또는 결과 전체), `result_count_seen`, `relevant_found`를 기록한다. 첫 화면의 브랜드명 결과만 보고 멈추지 않는다. 위탁사·채용대행사 게시가 보이면 후순위 결과에서 실제 채용 법인 페이지를 찾는다.
- 새 기업은 `candidate`(`origin` 자동 `discovered`, `discovered_by`=발견한 search_id)로 추가하고, 그 기업의 채용 경로를 `channel`로 1개 이상 기록한다.
`add 조사.json search --json '{"task_id":"U-01-1-wanted","channel_id":"wanted","query":"공유 킥보드 운영 채용","results_reviewed":20,"result_count_seen":34,"relevant_found":2}'`
끝나는 조건: 이 유형의 `신규 발굴 미실시` 0건.

**E. 채널 768칸** — 이 유형 후보 × 12개 채널을 모두 확인한다(상태 정의: `references/channels_and_search.md`). 채용 목록을 연 경우(`page_checked`/`posting_checked`) 목록에서 본 관련 공고 수 `relevant_found`를 기록한다.
끝나는 조건: `채널 미실시` 0건.

**F. 발견 공고 등록과 판정** — C·D·E에서 본 관련 공고는 제목만 봤더라도 모두 `discovered`로 등록한다(`found_via`: `revisit:T0002` / `search:S0007` / `channel:02-01/official`). 등록 건수가 앞에서 기록한 `relevant_found`보다 적으면 FAIL이다. 등록한 공고마다 판정을 정확히 1건 남긴다.
- 포함: 상세 원문을 열어 `job`을 기록하고 `decision {"outcome":"job","job_key":...}`.
- 제외: `decision {"outcome":"excluded","reason_code":..., "reason":"원문 근거"}`. 코드는 `duplicate`(+`duplicate_of`), `closed`, `condition_mismatch`, `irrelevant_jd`, `detail_blocked`, `out_of_scope`.
- `job` 필수 값: 채용 법인(`hiring_entity`), 게시 주체(`poster_entity`, `poster_relation`=direct/parent/agency), 근무지, 경력, 고용형태, 마감, 적합도 점수와 근거, 사용자 조건 부합(`match/mismatch/check`), 원문 URL, 출처별 상태(`sources[].status_seen`). 값이 없으면 `미표기`.
- **모집 중(`open_verified`)**은 상세 원문의 접수기간·상시채용 문구·지원 가능 표시를 `open_evidence`(url, kind, quote)로 남긴 경우에만 쓴다. 마감일이 지났으면 모집 중이 아니다.
- **출처 상태 충돌**(공식은 마감, 외부는 모집 등)은 해결될 때까지 `unknown_conflict`로 둔다.
- 위탁·대행 게시(`agency`)는 실제 채용 법인을 따로 적는다. 못 찾으면 `"확인 불가"`.
- 중복은 `법인 + 직무명 + 근무지 + JD 핵심`이 같을 때만 하나의 `job_key`로 합치고, 다른 게시처는 `sources`에 보존한다.
끝나는 조건: `최종 판정 0건`, `발견 목록 등록 n건` 지적이 0건.

**G. 종료** — `todo 조사.json`으로 남은 작업이 0건인지 확인하고 `finish-type 조사.json 01`.
- 접근 제한이 남아 대체 원문이 없으면 도구가 부분 조사로 판정한다. `--partial-reason "LinkedIn 로그인 제한, 대체 원문 없음"`을 붙여 종료하고 **다음 유형으로 계속 진행한다.**
- 미실시가 남으면 종료가 거부된다. 처리하는 것이 원칙이며, 도구·시간 한계로 끝내 못 하면 `--abandon "사유"`로 미실시 종료하고 다음 유형으로 간다. 이 유형은 최종 FAIL로 보고된다.
- 정상 조사 후 관련 공고가 0건이면 그대로 완료(0건)다.

## 3. 마무리와 보고

1. `python SKILL_DIR/scripts/ledger.py audit 조사.json` — 종료 코드 0=COMPLETE, 1=PARTIAL, 2=FAIL.
2. `python SKILL_DIR/scripts/ledger.py report 조사.json 보고서.md` — 보고서는 이 출력을 바탕으로 쓴다. 숫자를 바꾸거나 표를 빼지 않는다.
3. 보고 순서: **휴대폰 요약(지원 우선순위 5건 + 주요 제약) → 유형별 상태표 → 공고 목록(근무지·경력·고용형태·마감·적합도·원문 링크) → 미확인·부분 조사·미실시 항목.**
4. 표현 규칙
   - `COMPLETE`일 때만 "10개 유형 조사 완료"라고 쓴다. `PARTIAL`이면 "부분 조사(유형 n개)"와 사유, `FAIL`이면 "조사 미완료"와 미실시 항목을 제목 바로 아래에 쓴다.
   - 이전 장부가 없으면 `최초 기준선`. 비교 근거 없이 '오늘 신규', '어제 대비 마감'이라고 쓰지 않는다.
   - COMPLETE도 공개 채널의 기록 완결성일 뿐 모든 채용을 찾았다는 증명이 아니다.
5. 장부 JSON과 보고서를 사용자에게 파일로 넘긴다. 다음 회차의 `--baseline` 입력이 된다.

## 4. 코드 실행이 불가능한 환경

`ledger.py`를 실행할 수 없으면 같은 절차를 표로 수동 기록하고, 보고서 첫 줄에 `자동 감사 미실행`을 쓴다. 이 경우 "완료"라고 쓰지 않고 유형별로 "수동 기록 기준 완료/부분/미실시"만 쓴다. 백그라운드 실행이나 나중의 자동 완료를 약속하지 않는다.

## 5. 적합도 점수

운영 개선 직접성 40 + 데이터 분석 25 + KPI 20 + 운영 의사결정 15 = 100. `fit_reason`에 JD 문장을 짧게 인용한다. 사용자 조건(경력·고용형태·지역·급여 등)은 대화나 확인 가능한 개인 맥락에 근거가 있을 때만 `condition_fit`에 반영하고, 근거가 없으면 `check`로 둔다. 제목만 보고 점수를 매기지 않는다.
