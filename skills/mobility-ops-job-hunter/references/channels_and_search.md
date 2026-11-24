# 채용 채널·확인 방법 (v1.2.1)

기준 파일은 `coverage_contract.json`(채널 `scope`, 유형별 키워드, 실행 기준)이다.

## 1. 확인 방법 우선순위 (`method`)

| 순위 | method | 뜻 | 쓰는 경우 |
|---|---|---|---|
| 1 | `browser` | 브라우저로 채용 목록·공고를 직접 열어 화면을 읽음 | 주소를 알 때(등록 경로, 재방문, 상세) |
| 2 | `platform_search` | 사람인·원티드 등 사이트 내부 검색창에 입력 | 기업 페이지를 찾거나 플랫폼 키워드 발굴 |
| 3 | `web_search` | 외부 검색엔진(`site:` 포함) | 1·2가 막혔을 때 |
| 4 | `fetch` | 웹 가져오기 도구로 본문만 받음 | 브라우저 모드가 없을 때 |

외부 검색엔진 결과는 검색엔진이 예전에 저장해 둔 목록이라 새 공고가 빠지거나 마감 공고가 남는다. 결과에 없다는 것은 "공고 없음"이 아니다. `evidence`에는 화면에서 본 문구, 결과 제목, 오류 메시지 원문을 적는다.

## 2. 12개 채널과 scope (768칸 = 64 후보 × 12)

| 채널 ID | 대상 | scope | 칸을 채우는 방법 |
|---|---|---|---|
| official | 공식 채용 사이트·ATS | company | 기업별 직접 열기 |
| wanted | 원티드 | company | 기업별 직접 열기(기업 페이지) |
| saramin | 사람인 | company | 기업별 직접 열기(기업 채용 목록) |
| jobkorea | 잡코리아 | company | 기업별 직접 열기(기업 채용 목록) |
| group | 그룹·모회사 채용 | entity | 법인·경로 검색(E 작업) 결과로 |
| official_social | 공식 SNS·인재풀 | entity | 법인·경로 검색(E 작업) 결과로 |
| linkedin | LinkedIn Jobs | type | 유형 키워드 검색 결과로 |
| incruit | 인크루트 | type | 유형 키워드 검색 결과로 |
| rocketpunch | 로켓펀치 | type | 유형 키워드 검색 결과로 |
| rallit_jumpit | 랠릿·점핏 | type | 유형 키워드 검색 결과로 |
| jobplanet | 잡플래닛 | type | 유형 키워드 검색 결과로 |
| global_careers | 해외 Careers·기타(리멤버·직행 등) | type | 유형 키워드 검색 결과로 |

- **company**: 공고가 가장 많이 올라오는 곳이다. 기업마다 채용 목록을 직접 확인한다. 같은 법인의 앞선 후보 칸을 이미 확인했으면 `shared`로 결과를 공유한다(카카오모빌리티 5행, 티맵모빌리티 3행 등).
- **entity**: 특정 플랫폼이 아니라 키워드 검색을 할 수 없다. 기업별 법인·경로 검색에서 함께 확인한다.
- **type**: 기업별로 반복 검색하지 않고, 그 플랫폼에서 유형 키워드로 한 번에 훑는다. 후보 목록 밖 기업도 찾는다. 특정 후보의 공고가 보이면 그 칸을 직접 기록한다.
- 이전 v1.1 xlsx의 `랠릿`·`점핏`은 `rallit_jumpit`, `기타(리멤버·지행 등)`는 `global_careers`로 대응한다.

## 3. 채널 상태

| 상태 | 뜻 | 필수 |
|---|---|---|
| `posting_checked` / `page_checked` | 공고 상세 / 채용 목록을 직접 엶 | url, relevant_found, method, evidence, classified_by |
| `search_only` | 검색 결과에만 보임 | query, note, method, evidence, classified_by |
| `searched_no_match` | 찾았으나 경로 없음(공고 없음과 다름) | query, note, method, evidence, classified_by |
| `access_blocked` | 403·로그인 등 | query, note, evidence(오류 원문), 가능하면 alternative_url |
| `shared` | 같은 법인의 다른 후보 칸 결과 공유 | shared_from |
| `covered_by_type_search` / `covered_by_entity_search` / `covered_by_registry` | 도구가 실제 검색 기록·등록부로 채움 | 자동 |
| `not_applicable` | group·global_careers만, 사유와 함께 | note |
| `unsearched` | 하지 않음 → 그 유형 미실시 | — |

## 4. 누락 방지

- 짧은 이름 포함 매칭: 코드로 분류할 때 `ledger.py names --json` 목록을 그대로 쓴다(쏘카, 모빈, 타다, 딜리, 채비).
- 별칭: 일레클/나인투원/쏘카, 킥고잉·씽씽/피유엠피/올룰로, 투루카/피플카, 그린카/G car, KM파크/카카오 T 주차, 모두의주차장/쏘카, 딜리/우아한형제들, 셔클/현대자동차.
- 회사 존재, 채용 경로 존재, 현재 모집 중은 서로 다른 사실이다.
