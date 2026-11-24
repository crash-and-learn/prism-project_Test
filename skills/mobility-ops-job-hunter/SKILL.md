---
name: mobility-ops-job-hunter
description: 국내 모빌리티 10개 유형(64개 초기 후보)의 운영 개선·데이터 분석 채용을 유형 01→10 순서로, 여러 턴(답변)에 나눠 조사한다. 법인 등록부(180일) 재사용, 이전 URL·미판정 이월 재확인, 채용 목록 직접 열기, 플랫폼 키워드 발굴, 768개 후보×채널 기록, 발견 공고 전건 판정을 장부(ledger.py)에 남기고 유형별 완료/부분/미실시와 휴대폰 요약을 보고할 때 사용.
---

# Mobility Ops Job Hunter v1.2.1

국내 모빌리티 분야의 **데이터 기반 운영 개선** 직무를 찾는 조사 절차다. 한국어로 답한다. 범위를 표본으로 줄이지 않고, 중간 승인 질문 없이 진행한다. Claude·GPT 공용(`references/host_setup.md`).

## 0. 절대 규칙

1. **장부는 `ledger.py`로만 쓴다.** `SKILL_DIR`은 이 파일이 있는 폴더다. 명령은 `python SKILL_DIR/scripts/ledger.py <명령> 장부.json ...`. JSON을 직접 고치지 않는다. **장부를 새로 만들어 다시 입력하지 않는다**(기록 시각이 몰리면 "사후 일괄 기록"으로 FAIL).
2. **조사한 직후에 기록한다.** 웹 작업 묶음(재방문, 검색, 채널, 판정)마다 바로 `add`한다. 유형 하나는 최소 5분, 기록 3회 이상에 걸쳐 남는 것이 정상이다.
3. **실제로 한 일만 쓴다.** 열지 않은 URL, 하지 않은 검색, 보지 않은 결과 수는 기록하지 않는다. 모든 열람·검색 기록에 `method`와 `evidence`(화면에서 본 문구, 결과 제목, 오류 메시지 원문)를 남긴다.
4. **정확한 방법을 먼저 쓴다.** ① 등록된 채용 목록 주소 직접 열기(`browser`) → ② 사이트 내부 검색창(`platform_search`) → ③ 외부 검색엔진·`site:`(`web_search`) → ④ 가져오기 도구(`fetch`). ③·④는 ①·②가 불가능할 때만 쓴다. 브라우저를 조작할 수 있는 모드(에이전트·워크모드)가 있으면 그 모드에서 실행한다.
5. **로그인·우회 금지.** 로그인이 필요한 페이지는 사용자가 따로 허락하지 않는 한 열지 않는다. 차단(403 등)은 우회하지 않고 `access_blocked`와 오류 원문으로 기록한 뒤 대체 원문을 찾는다.
6. **모집 중 판정은 상세 원문 근거로만.** `open_verified`에는 `open_evidence`(상세 URL, 종류, 원문 문구)가 필요하다. 출처끼리 상태가 다르면 `unknown_conflict`.
7. **코드로 분류했으면 그렇다고 쓴다.** 검색 결과를 코드(정규식 등)로 분류했다면 `classified_by: "code"`. 그 유형의 코드 판정 중 3건(적으면 전부)을 원문으로 직접 대조해 `spotcheck`로 남긴다. 기업명 매칭 코드는 `ledger.py names --json`의 이름 목록을 그대로 쓴다(쏘카·모빈·타다·딜리처럼 짧은 이름을 빼지 않는다). 공식 채용 도메인은 실제로 확인한 URL만 쓴다.
8. `audit`가 COMPLETE가 아니면 "조사 완료"라고 쓰지 않는다.

## 1. 회차 시작 (첫 턴)

1. 입력 확인: 지난 회차 장부 JSON(권장) 또는 이전 조사표 xlsx. 없으면 `최초 기준선`.
2. `init 조사_YYYYMMDD.json --baseline <이전 파일>` — 법인 등록부, 이월 항목(미판정·상세 차단·재방문 차단·모집 중 공고), 신규 기업이 이어진다. 출력의 **턴 계획**을 사용자에게 보여준다.
3. `유형 미배정`이 나오면 `assign-baseline 장부 T0012=08 T0013=00:사유`로 모두 지정한다.
4. 이미 진행 중인 장부를 받았다면 init 하지 않고 `next 장부`로 이어간다.

## 2. 턴 진행

- 매 턴 시작에 `next 장부`를 실행한다. 이번 턴의 유형과 할 일만 보고 그 범위만 진행한다.
- 턴의 마지막 유형을 `finish-type`하면 도구가 "턴 n 종료"를 출력한다. 그때 **장부 파일을 저장해 다운로드 링크로 주고, 진행 요약(유형별 상태, 공고 수, 남은 턴)을 쓰고 멈춘다.** 사용자가 "계속"이라고 하면 같은 장부로 `next`부터 이어간다.
- 턴당 작업량 기준은 500건(페이지 열기+검색)이다. 사용자가 바꾸라고 하면 첫 유형 시작 전에 `plan 장부 --budget N`.

## 3. 유형 하나의 절차 (start-type → A~F → finish-type)

`start-type 장부 NN`이 이 유형의 할 일 목록을 보여준다. `todo 장부`로 언제든 남은 일을 본다.

**A. 법인 확인** — 상태가 `verified_cached`(등록부 180일 이내)인 후보는 건너뛴다. 나머지(미확정·만료·신규)는 `E-<후보ID>` 검색 한 번으로 실제 채용 법인과 채용 경로(공식 ATS, 플랫폼 기업 페이지, 그룹 채용, 공식 SNS)를 함께 찾는다.
`add 장부 candidate --json '{"id":"01-01","relation_status":"verified","resolved_company_id":"nine2one","relation_evidence_url":"https://...","queries":["일레클 운영사"],"note":"..."}'`
`add 장부 search --json '{"task_id":"E-01-01","channel_id":"web","query":"...","method":"web_search","evidence":"상위 결과: ...","classified_by":"manual","results_reviewed":10,"relevant_found":1}'`
기간 안이라도 **등록 경로가 사라졌거나(`route_status:"gone"`) 다른 도메인으로 바뀌었거나(`moved`), 공고의 게시 법인명이 등록부와 다르거나, 합병·종료 소식이 보이면** `candidate`에 `recheck_reason`을 적고 다시 확인한다.

**B. 재방문** — `todo`의 `재방문 누락` URL을 모두 연다(이전 회차 미판정·차단 이월 포함). `result`(ok/redirected/closed/gone/blocked), `final_url`, `relevant_found`(그 페이지에서 본 관련 공고 수), `method`, `evidence`. 공고 상세였다면 C의 발견 목록에 반드시 올린다.

**C. 채널 768칸** — 칸의 종류(`scope`)마다 채우는 방법이 다르다.

| scope | 채널 | 방법 |
|---|---|---|
| company | 공식, 원티드, 사람인, 잡코리아 | **기업별로** 채용 목록을 직접 연다. `route_hint`(등록 경로)가 있으면 그 주소부터. 없으면 사이트 내부 검색으로 기업 페이지를 찾는다. `page_checked`/`posting_checked`(url, relevant_found) 또는 `searched_no_match`·`access_blocked`(query, note). 같은 법인의 앞선 후보 칸을 이미 확인했다면 `{"status":"shared","shared_from":"03-01"}`. |
| entity | 그룹·모회사, 공식 SNS | A의 `E-` 검색이 끝나면 자동으로 채워진다(`covered_by_entity_search`, 등록부 재사용이면 `covered_by_registry`). 경로를 찾았으면 직접 열어 `page_checked`로 기록한다. |
| type | LinkedIn, 인크루트, 로켓펀치, 랠릿·점핏, 잡플래닛, 글로벌·기타(리멤버·직행) | D의 유형 키워드 검색이 끝나면 자동으로 채워진다(`covered_by_type_search`). 그 검색에서 특정 후보의 공고나 기업 페이지가 보이면 그 칸을 직접 기록한다. |

**D. 플랫폼 키워드 발굴** — `U-<유형>-<검색식>-<채널>` 작업 20개: 기업명 없이 `suggested_query`를 web·원티드·사람인·잡코리아·LinkedIn·인크루트·로켓펀치·랠릿·점핏·잡플래닛·글로벌기타에서 각각 검색한다. **가능하면 각 사이트의 내부 검색창**(`platform_search`)을 쓴다. `results_reviewed`는 실제로 훑어본 결과 수(기준 10개 또는 전체). 후보 밖 기업은 `candidate`(`discovered_by`=검색 ID)로 추가하고 채용 경로를 `channel`로 1개 이상 기록한다.

**E. 발견 공고 등록·판정** — B·C·D에서 본 관련 공고는 제목만 봤어도 모두 `discovered`로 등록한다(`found_via`: `revisit:T0002` / `search:S0007` / `channel:02-01/official`). 등록 수가 앞서 적은 `relevant_found`보다 적으면 FAIL. 각 공고에 `decision` 1건(`classified_by` 필수):
- 포함: 상세 원문을 열어 `job` 기록 → `{"outcome":"job","job_key":...}`
- 제외: `{"outcome":"excluded","reason_code":"duplicate|closed|condition_mismatch|irrelevant_jd|detail_blocked|out_of_scope","reason":"원문 근거"}` (duplicate는 `duplicate_of`)
- `job` 필수: 채용 법인(`hiring_entity`), 게시 주체(`poster_entity`, `poster_relation`=direct/parent/agency), 근무지, 경력, 고용형태, 마감(YYYY-MM-DD 또는 `상시`/`채용 시 마감`/`미표기`), `fit_score`, `fit_reason`(JD 인용), `condition_fit`(match/mismatch/check), 원문 URL, `sources[{url, platform, status_seen}]`, `status`. 같은 공고의 여러 게시처는 한 `job_key`의 `sources`로 합친다.
- 위탁·대행(`agency`)은 실제 채용 법인을 따로 적는다. 모르면 `"확인 불가"`.

**F. 표본 대조와 종료** — 코드 판정이 있으면 `spotcheck` `{"disc_id":"D0012","agrees":true,"evidence":"원문 문구"}`를 남긴다. `todo`가 0건이면 `finish-type 장부 NN`.
- 대체 원문 없는 차단만 남으면 `--partial-reason "사유"`로 종료하고 다음 유형으로 간다.
- 미실시가 남으면 종료가 거부된다. 처리가 원칙이며, 끝내 불가능하면 `--abandon "사유"`(그 유형 FAIL).
- 정상 조사 후 0건이면 완료(0건).

## 4. 마무리 (마지막 턴)

1. `audit 장부` (0=COMPLETE, 1=PARTIAL, 2=FAIL) → `report 장부 보고서.md`
2. 답변은 보고서 순서를 따른다: 판정 한 줄 → **휴대폰 요약(지원 우선순위 최대 5건 + 주요 제약)** → 유형별 상태표 → 공고 목록(근무지·경력·고용형태·마감·적합도·원문) → 미확인·부분·미실시 항목. 숫자를 바꾸거나 표를 빼지 않는다.
3. COMPLETE면 "10개 유형 조사 완료", PARTIAL이면 "부분 조사(유형·사유)", FAIL이면 "조사 미완료(미실시 항목)".
4. 장부 JSON과 보고서를 파일로 준다. **다음 회차에는 이 장부 JSON 하나만 첨부하면 된다**(법인 등록부·이월 항목 포함).

## 5. 적합도

운영 개선 직접성 40 + 데이터 분석 25 + KPI 20 + 운영 의사결정 15 = 100. 사용자 조건(경력·고용형태·지역·급여)은 대화나 확인 가능한 개인 맥락에 근거가 있을 때만 `condition_fit`에 반영하고, 없으면 `check`. 제목만 보고 점수를 매기지 않는다.

## 6. 코드 실행이 불가능하면

같은 절차를 표로 수동 기록하고 보고서 첫 줄에 `자동 감사 미실행`을 쓴다. "완료"라고 쓰지 않는다. 백그라운드 실행이나 나중 자동 완료를 약속하지 않는다.
