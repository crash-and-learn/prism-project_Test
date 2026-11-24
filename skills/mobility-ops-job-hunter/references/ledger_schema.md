# 장부 구조와 완료 기준 (v1.2.1)

장부는 `ledger.py init`이 만들고 `ledger.py add`로만 갱신한다. 모든 기록에 도구가 `at`(KST)과 `type_id`를 넣는다. 진행 중 유형이 아닌 기록은 거부된다.

## 1. 구성

| 키 | 내용 |
|---|---|
| `run_started_at`, `types[]` | 회차 시작, 유형별 `status/started_at/finished_at/partial_reason/abandon_reason` |
| `turn_plan[]`, `type_estimates` | 턴 분할(유형 경계, 턴당 예상 작업 500건 기준)과 유형별 예상 작업량 |
| `registry{후보ID: …}` | 법인 등록부. `status, resolved_company_id, legal_name, relation_evidence_url, verified_at, routes{채널: URL}, routes_checked_at, origin` |
| `baseline.targets[]` | 재방문·이월 대상. `source_sheets`에 출처(`carryover:undecided_or_blocked`, `carryover:baseline_ok`, `carryover:baseline_blocked`, `carryover:job`, xlsx 시트명) |
| `candidates[]` | `relation_status`: verified / verified_cached / excluded_verified / searched_unresolved / access_blocked / unsearched. `origin`: contract / discovered / carried. `recheck_reason` |
| `channels[]` (768 + 신규) | `scope`(company/entity/type), `status`, `method`, `evidence`, `classified_by`, `query`, `url`, `route_hint`, `route_status`(ok/gone/moved), `alternative_url`, `relevant_found`, `shared_from`, `covered_by` |
| `discovery_plan[]` | `E-<후보>`(법인·경로 검색, 등록부 재사용 후보는 없음) + `U-<유형>-<검색식>-<채널>`(유형당 20개) |
| `revisits[]` | `target_id, result, final_url, alternative_url, relevant_found, method, evidence` |
| `searches[]` | `search_id, task_id, candidate_id, channel_id, query, method, evidence, classified_by, results_reviewed, result_count_seen, relevant_found` |
| `discovered[]`, `decisions[]` | 발견 공고(`found_via`)와 판정(`outcome, reason_code, reason, duplicate_of, classified_by`) |
| `jobs[]` | `job_key, title, hiring_entity, poster_entity, poster_relation, location, career, employment_type, deadline, fit_score, fit_reason, condition_fit, url, sources[], status, open_evidence` |
| `spotchecks[]` | 코드 판정 표본 대조 `disc_id, agrees, evidence, note` |

## 2. 완료 기준 (audit가 유형마다 적용)

| # | 대조 | 미실시(FAIL) | 부분 조사 |
|---|---|---|---|
| 0 | 유형 작업 시간·기록 횟수 | 유형 작업 5분 미만 또는 서로 다른 기록 시각 3개 미만(사후 일괄 기록 의심) | — |
| 1 | 재방문·이월 대상 ↔ `revisits` | 기록 없음, 시각이 유형 구간 밖, method·evidence 없음 | 차단이고 대체 원문 없음 |
| 2 | `discovery_plan` ↔ `searches` | 실행 기록 없음, 비고정 작업에 candidate_id, method·evidence·classified_by·results_reviewed 없음 | 검토 결과 < 10개이고 전체도 아님 |
| 3 | 후보 관계 | 미조사, 등록부 기간 만료, 등록 경로가 사라졌는데 재확인 안 함 | 관계 확인 접근 제한 |
| 4 | 768칸 + 신규·이월 후보 | company 칸 미실시, entity·type 칸의 근거 검색 미실시, shared가 같은 법인이 아님, 신규·이월 후보의 채용 경로 기록 없음 | 차단이고 대체 원문 없음 |
| 5 | `relevant_found` ↔ `discovered` | 본 수보다 등록 수가 적음 | — |
| 6 | `discovered` ↔ `decisions` | 판정 0건 또는 2건 이상, classified_by 없음, 재확인 대상 공고 미등록, 판정과 연결되지 않은 job | `detail_blocked` |
| 7 | 코드 판정 ↔ `spotchecks` | 유형의 코드 판정 중 min(3, 전체)건 미만 대조 | — (불일치는 미확인 항목) |
| 8 | `open_verified` ↔ 원문 근거 | 근거 없음, 마감일 지남, 출처 상태 충돌인데 `unknown_conflict` 아님 | — (충돌·불명은 미확인 항목) |
| 9 | 게시 주체·필수 항목 | agency인데 채용 법인 미기재, 필수 항목 빈 값 | — |
| 10 | 순서·중복·자기보고 | 유형 구간 겹침, 앞 유형 미착수, job_key 중복, complete로 기록했는데 산정 결과 다름 | — |

- 접근 제한만 남음 → 그 유형 `partial`(사유 필수), 전체 PARTIAL(종료 코드 1), 다음 유형 계속.
- 정상 조사 후 0건 → `complete` + `zero_found`.
- 기록 누락 → 그 유형 `not_done`, 전체 FAIL(종료 코드 2).

## 3. 법인 등록부 규칙

- `finish-type` 때 그 유형에서 `verified`된 후보와, 직접 연 company·entity 채널 URL이 등록부에 저장된다.
- 다음 회차 `init --baseline 이전장부.json`이 등록부를 이어받는다. 확인일로부터 180일 이내면 `verified_cached`, 법인 검색 작업을 만들지 않는다.
- 180일 경과, 미확정, 신규 기업은 다시 확인한다. 기간 안이라도 등록 경로가 사라지거나 이동했거나(`route_status`), 게시 법인명이 다르거나, 합병·종료가 보이면 `recheck_reason`을 기록하고 다시 확인한다.

## 4. 사람이 확인할 품질 (자동 검사 밖)

1. 재방문·채널의 URL과 `evidence` 문구가 실제 화면과 같은가
2. `open_evidence.quote`와 마감일이 원문과 같은가
3. `poster_relation`·`hiring_entity`가 원문 게시 정보와 맞는가
4. 제외 사유가 JD 내용과 맞는가, 코드 판정 표본이 무작위로 골라졌는가
5. `relevant_found`가 실제 목록의 관련 공고 수보다 적게 적히지 않았는가
