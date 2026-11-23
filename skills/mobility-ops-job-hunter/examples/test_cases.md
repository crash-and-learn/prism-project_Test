# 테스트 케이스와 기대 판정 (v1.2)

자동 테스트: 스킬 폴더에서 `python -m unittest discover -s tests` (임시 데이터만 사용, 외부 조사 없음).

## 자동 검사 시나리오 (`tests/test_ledger.py`)

| 상황 | 기대 판정 | 테스트 |
|---|---|---|
| 모든 작업 기록, 이전 URL 재방문 포함 | COMPLETE (exit 0) | `test_0_complete` |
| A. 768칸은 채웠지만 이전 URL 재방문 0건 | 해당 유형 미실시 → FAIL | `test_A_no_revisit` |
| A'. 이전 회차 날짜를 그대로 복사 | 해당 유형 미실시 | `test_A_stale_dates` |
| B. 한 유형의 기업명 비고정 발굴 생략 | 그 유형만 미실시, 다른 유형은 완료 | `test_B_skip_unanchored` |
| B'. 한 후보의 법인 발굴 검색 생략 | 그 유형 미실시 | `test_B_skip_entity` |
| C. 위탁사 게시인데 채용 법인을 위탁사로 기재 | 미실시 | `test_C_agency_as_hiring_entity` |
| C'. 위탁 게시, 실제 채용 법인 기재 | 완료 | `test_C_agency_resolved` |
| C''. 검색 결과 3개만 검토하고 complete로 보고 | 과대보고 FAIL | `test_C_shallow_results` |
| D. 목록에서 관련 공고 1건을 봤으나 등록 안 함 | 미실시 | `test_D_seen_but_not_registered` |
| D'. 등록했으나 판정 없음 | 미실시 | `test_D_registered_not_decided` |
| D''. 재확인 대상 공고를 열었으나 판정 안 함 | 미실시 | `test_D_revisited_posting_not_judged` |
| E. 같은 공고 2행 | FAIL | `test_E_duplicate_rows` |
| E'. 공식 마감·외부 상시인데 모집 중 | 미실시 | `test_E_conflict_marked_open` |
| E''. 같은 상황을 `unknown_conflict`로 기록 | 완료 + 미확인 항목 | `test_E_conflict_marked_unknown` |
| E'''. 모집 중 근거 없음 / 마감일 지남 | 미실시 | `test_E_open_without_evidence`, `test_E_open_past_deadline` |
| F. 채널 차단, 대체 원문 있음 | 완료 | `test_F_blocked_with_alternative` |
| F'. 채널 차단, 대체 원문 없음, 부분 조사로 보고 | PARTIAL (exit 1) | `test_F_blocked_without_alternative_declared_partial` |
| F''. 같은 상황을 complete로 보고 | FAIL | `test_F_blocked_without_alternative_declared_complete` |
| G. 모든 작업 후 관련 공고 0건 | 완료(0건) | `test_G_zero_found` |
| H. 05유형 채널 1칸 미실시 | 05만 미실시, 9개 유형 완료 | `test_H_one_channel_unsearched` |
| H'. 공고 판정값 없음 | 미실시 | `test_H_undecided_job` |
| I. 01유형 종료 전에 02유형 시작 | 순서 위반 FAIL | `test_I_overlap_order` |
| 신규 기업에 채용 경로 기록 없음 | 미실시 | `test_X_new_company_without_route` |
| 02유형부터 시작 / 진행 중이 아닌 유형 기록 | 도구가 거부 | `test_order_enforced`, `test_wrong_type_record_refused` |
| 미실시 남은 채 종료 / 사유 없는 부분 조사 | 도구가 거부, `--abandon`이면 FAIL로 기록 | `test_finish_refused_then_abandon`, `test_partial_requires_reason` |
| 이전 조사표 xlsx 가져오기, 미배정 URL 있으면 시작 거부 | 거부 후 지정하면 시작 | `test_xlsx_import` |

## 사람이 확인할 케이스 (실제 실행 후 표본 대조)

1. 일레클 → 일레클·나인투원·쏘카 각각 검색했고, 채용 법인과 근거 URL이 맞는가.
2. 원티드·LinkedIn 동일 JD → 하나의 job_key, 두 링크가 sources에 남았는가.
3. LinkedIn 스니펫만 확인 → `search_only`, 공고는 `open_verified`가 아닌가.
4. Data Scientist 연구직처럼 운영 개선이 없는 공고 → 낮은 점수 또는 `irrelevant_jd` 제외인가.
5. 사용자 조건 불일치 → `condition_fit=mismatch`, 근거 없는 연봉 추정이 없는가.
6. 이전 스냅샷 없음 → 보고서에 `최초 기준선`, 신규·마감 표기가 없는가.
7. 기업명 비고정 검색 결과에서 후보 밖 기업이 나왔을 때 candidate로 추가됐는가.
