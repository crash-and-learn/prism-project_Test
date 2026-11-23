# 장부 구조와 완료 기준 (v1.2)

장부는 `ledger.py init`이 만들고 `ledger.py add`로만 갱신한다. 모든 기록에는 도구가 `at`(KST, 시간대 포함)과 `type_id`를 자동으로 넣는다. 진행 중인 유형이 아닌 기록은 거부된다.

## 1. 구성

| 키 | 생성 | 내용 |
|---|---|---|
| `run_started_at` | init | 회차 시작 시각 |
| `types[]` | init / start-type / finish-type | `type_id, seq, category, status(not_started/in_progress/complete/partial/not_done), started_at, finished_at, partial_reason, abandon_reason` |
| `baseline.targets[]` | init --baseline, assign-baseline | 이전 조사표의 재방문 대상. `target_id, type_id(01~10, 00=유형 외), candidate_id, url, kind(company_page/job_posting/search_page), source_sheets, assign_reason` |
| `candidates[]` | init(64개) / add candidate | `id, type_id, brand_name, legal_hint, origin(contract/discovered), relation_status, resolved_company_id, relation_evidence_url, queries[], note, discovered_by` |
| `channels[]` | init(768개) / add channel | `candidate_id, channel_id, status, query, url, alternative_url, relevant_found, note` |
| `discovery_plan[]` | init | 신규 발굴 작업. 후보별 `E-<후보ID>`(64개) + 유형별 기업명 비고정 `U-<유형>-<검색식>-<채널>`(10×2×4=80개) |
| `revisits[]` | add revisit | `target_id, result(ok/redirected/closed/gone/blocked), final_url, alternative_url, relevant_found, note` |
| `searches[]` | add search | `search_id, task_id, candidate_id(비고정 작업은 비움), channel_id, query, results_reviewed, result_count_seen, relevant_found` |
| `discovered[]` | add discovered | 목록·검색에서 본 관련 공고. `disc_id, url, title, relevant(true/false), reason(무관 시), found_via(revisit:/search:/channel:)` |
| `decisions[]` | add decision | `disc_id, outcome(job/excluded), job_key, reason_code, reason, duplicate_of, evidence_url` |
| `jobs[]` | add job | `job_key, title, hiring_entity, poster_entity, poster_relation(direct/parent/agency), location, career, employment_type, deadline, fit_score, fit_reason, condition_fit(match/mismatch/check), url, sources[{url, platform, status_seen(open/always_open/closed/unknown)}], status(open_verified/closed_verified/unknown_conflict/unknown), open_evidence{url, kind(deadline_date/always_open_label/apply_open_label), quote}` |

## 2. 완료 기준 (audit가 유형마다 적용)

| # | 대조 | 필수 필드 | 미실시(FAIL) | 부분 조사 | 자동 검사 |
|---|---|---|---|---|---|
| 1 | `baseline.targets` ↔ `revisits` | result, at, relevant_found(ok·redirected) | 재방문 기록 없는 대상 1건 이상, 시각이 해당 유형 구간 밖 | `blocked`이고 대체 원문 없음 | 존재·시각 자동 / 실제 열람은 사람 |
| 2 | `discovery_plan` ↔ `searches` | query, results_reviewed, relevant_found | 실행 기록 없는 작업 1건 이상, 비고정 작업에 candidate_id | 검토 결과 수 < 10이고 결과 전체도 아님 | 자동 / 검색어 품질은 사람 |
| 3 | 계약 64후보·768칸 + 신규 후보 ↔ `candidates`·`channels` | 상태별 url·query·note | `unsearched` 1건, 이전 회차 날짜, 신규 후보의 발견 검색·채용 경로 없음 | 채널·법인 `access_blocked`이고 대체 원문 없음 | 자동 |
| 4 | `relevant_found` 합 ↔ `discovered` 등록 수 | found_via | 본 수보다 등록 수가 적음 | — | 자동 / 본 수의 진실성은 사람 |
| 5 | `discovered(relevant)` ↔ `decisions` | outcome + job_key 또는 reason_code·reason | 판정 0건 또는 2건 이상인 URL 1건 이상, 재확인 대상 공고가 발견 목록에 없음, 어떤 판정에도 연결되지 않은 job | `detail_blocked` 제외 | 자동 / 제외 사유 타당성은 사람 |
| 6 | `open_verified` ↔ 상세 원문 근거 | open_evidence.url(∈sources), kind, quote | 근거 없음, 마감일 지남, 출처 상태 충돌인데 `unknown_conflict` 아님 | — (충돌·불명은 미확인 항목으로 표시) | 자동 / 인용 문구 일치는 사람 |
| 7 | 게시 주체 | poster_relation, poster_entity, hiring_entity | agency인데 채용 법인 비어 있음 또는 게시 법인과 동일 | — (`확인 불가`는 미확인 항목) | 자동 / 법인 관계는 사람 |
| 8 | 공고 필수 항목 | 근무지·경력·고용형태·마감·fit_score·fit_reason·condition_fit·url | 1개라도 빈 값 | — | 자동 |
| 9 | 유형 순서 | types[].started_at/finished_at | 구간 겹침, 앞 유형 미착수 상태로 뒤 유형 진행, 자기보고 complete인데 산정은 다름 | — | 자동 / 시각의 진실성은 사람 |
| 10 | 중복 | job_key 고유 | 같은 키 2행 | — | 자동 / 병합 판단은 사람 |

**상태 구분**

- 실제 미실시: 1~10 중 하나라도 미실시 → 그 유형 `not_done`, 전체 `FAIL`(종료 코드 2).
- 접근 제한: 시도 기록과 사유가 있고 대체 원문이 없음 → 그 유형 `partial`(`partial_reason` 필수), 전체 `PARTIAL`(종료 코드 1). 다음 유형은 계속 진행.
- 정상 조사 후 0건: 1~3이 모두 통과하고 관련 공고 0건 → `complete` + `zero_found`.

## 3. 사람이 확인해야 하는 품질 (표본 대조)

검사 코드는 기록이 있고 서로 맞는지만 본다. 매 회차 유형마다 아래를 3건씩 무작위로 골라 원문과 대조한다.

1. 재방문·채널의 URL이 실제로 열리고 기록된 결과와 같은가
2. `open_evidence.quote`가 원문 문구와 같은가, 마감일이 맞는가
3. `poster_relation`과 `hiring_entity`가 원문 게시 정보와 맞는가
4. 제외 판정(`reason`)이 JD 내용과 맞는가
5. `relevant_found`가 실제 목록의 관련 공고 수보다 적게 적히지 않았는가
6. 기업명 비고정 검색식이 그 유형의 업무를 대표하는가

## 4. 보고서 (`ledger.py report`)

순서: 휴대폰 요약(지원 우선순위 최대 5건 + 주요 제약) → 유형별 상태표(재방문·신규 발굴·채널·발견→판정·신규 기업·공고·미확인) → 공고 목록(채용 법인·게시 주체·직무·근무지·경력·고용형태·마감·접수 상태·적합도·조건·원문) → 미확인·부분 조사·미실시 항목 전체.
