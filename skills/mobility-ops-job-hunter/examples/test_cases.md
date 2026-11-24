# 테스트 케이스와 기대 판정 (v1.2.1)

자동 테스트: 스킬 폴더에서 `python -m unittest discover -s tests` (임시 데이터만 사용).

| 상황 | 기대 판정 | 테스트 |
|---|---|---|
| 정상 실행(유형마다 5분 이상, 기록 3회 이상) | COMPLETE | `test_0_complete` |
| 768칸이 scope별로 채워짐 | company 256 직접 기록, entity 128·type 384 자동 | `test_768_cells_filled_by_scope` |
| A. 이전 URL 재방문 0 / 이전 회차 날짜 복사 | 해당 유형 미실시 | `test_A_no_revisit`, `test_A_stale_dates` |
| B. 유형 키워드 검색 생략 / 법인 검색 생략 | 그 유형만 미실시, type 칸도 미실시 | `test_B_skip_keyword_search`, `test_B_skip_entity` |
| C. 위탁사를 채용 법인으로 기재 / 검색 결과 3개만 검토 | 미실시 / 과대보고 FAIL | `test_C_agency_as_hiring_entity`, `test_C_shallow_results` |
| D. 본 공고 미등록 / 등록 후 미판정 / 재확인 공고 미판정 | 미실시 | `test_D_*` |
| E. 중복 키 / 출처 충돌 / 근거 없는 모집 중 / 마감일 지남 | FAIL·미실시, 충돌을 `unknown_conflict`로 두면 완료+미확인 | `test_E_*` |
| F. 차단+대체 원문 / 대체 없음+partial / 대체 없음+complete | 완료 / PARTIAL / FAIL | `test_F_blocked` |
| G. 정상 조사 후 0건 | 완료(0건) | `test_G_zero_found` |
| H. 한 칸 미실시 | 그 유형만 미실시 | `test_H_one_channel_unsearched` |
| I. 유형 구간 겹침 | 순서 위반 FAIL | `test_I_overlap_order` |
| 사후 일괄 기록(30초에 전부 기록) | 미실시 | `test_batch_recording_detected` |
| method·evidence 누락 | 미실시 | `test_evidence_required` |
| 코드 판정 표본 대조 없음 / 불일치 | 미실시 / 미확인 항목 | `test_code_decisions_need_spotcheck` |
| 같은 법인 결과 공유 / 다른 법인 공유 | 완료 / 미실시 | `test_shared_channel` |
| 짧은 기업명(쏘카·모빈·타다) 매칭 목록 | 포함 | `test_names_keep_short` |
| 두 번째 회차: 등록부 64건 재사용, 법인 검색 0건, 경로 소멸 시 재확인 요구 | COMPLETE, 재확인 누락 시 미실시 | `test_second_run_reuses_registry` |
| 등록부 180일 경과 | 재사용 안 함, 법인 검색 64건 | `test_registry_expiry` |
| v1.2 장부에서 미판정·상세 차단·재방문 차단 이월, 마감 제외 | 이월 3건, 등록부·경로 생성 | `test_carryover_from_v12_ledger` |
| 턴 계획·next·턴 종료 안내 | 유형 순서대로 분할, 종료 메시지 | `test_plan_turns`, `test_next_and_turn_stop_message` |
| 순서 위반·다른 유형 기록·미실시 종료·사유 없는 부분 조사·덮어쓰기 | 도구가 거부 | `TestFlow` |
| xlsx 가져오기, 미배정 시 시작 거부 | 지정 후 시작 | `test_xlsx_import` |

## 사람이 확인할 케이스

1. 쏘카·모빈 등 짧은 이름 기업의 company 채널이 실제 기업 페이지로 확인됐는가.
2. `evidence` 문구를 3건 골라 실제 화면과 대조.
3. 원티드·LinkedIn 동일 JD가 한 `job_key`의 `sources`로 합쳐졌는가.
4. 등록부 재사용 후보 중 하나의 등록 경로를 열어 아직 유효한가.
5. 이전 회차 미판정 공고가 이번 회차에 판정됐는가.
