# 채용 채널·검색 지침 (v1.2)

채널 ID·후보·유형 순서·기업명 비고정 검색식의 기준은 `coverage_contract.json`이다.

## 1. 12개 채널 (후보마다 전부 기록 → 64 × 12 = 768칸)

| 채널 ID | 점검 대상 | 검색 힌트 |
|---|---|---|
| official | 공식 채용 | 브랜드/법인 + 채용 careers |
| group | 그룹·모회사·운영법인 | 모회사/운영법인 + 채용 |
| linkedin | LinkedIn Jobs | `site:linkedin.com/jobs/view/` + 법인명 운영 |
| wanted | 원티드 | `site:wanted.co.kr` + 브랜드명 운영 |
| saramin | 사람인 | `site:saramin.co.kr` + 법인명 기획 |
| jobkorea | 잡코리아 | `site:jobkorea.co.kr` + 법인명 운영 |
| incruit | 인크루트 | `site:incruit.com` + 법인명 데이터 |
| rocketpunch | 로켓펀치 | `site:rocketpunch.com` + 법인명 채용 |
| rallit_jumpit | 랠릿·점핏 | `site:rallit.com OR site:jumpit.saramin.co.kr` + 브랜드명 |
| jobplanet | 잡플래닛 | `site:jobplanet.co.kr` + 법인명 |
| official_social | 공식 SNS·인재풀 | 법인명 + 공식 채용 SNS |
| global_careers | 해외/글로벌 Careers·기타(리멤버·직행 등) | 영문명 + careers Korea |

이전 조사표(v1.1 xlsx)의 `랠릿`·`점핏`은 `rallit_jumpit` 하나로, `기타(리멤버·지행 등)`는 `global_careers`로 대응한다.

## 2. 채널 상태

| 상태 | 뜻 | 필수 기록 |
|---|---|---|
| `posting_checked` | 공고 상세 URL을 직접 열었다 | url, relevant_found |
| `page_checked` | 기업 채용 목록·페이지를 직접 열었다 | url, relevant_found |
| `search_only` | 검색 결과에만 보였고 상세 확인 못 함 | query, note |
| `searched_no_match` | 검색했으나 관련 경로 없음(공고 없음과 다름) | query, note |
| `access_blocked` | 로그인·기술 제한 | query, note, 가능하면 alternative_url |
| `not_applicable` | group·global_careers에서만, 이유와 함께 | note |
| `unsearched` | 하지 않음 → 그 유형 미실시 | — |

## 3. 신규 발굴 검색

- **기업명 고정(E 작업)**: 후보마다 `브랜드 + 법인 후보 + 채용`, 필요하면 구법인·영문명·모회사 별칭도 검색. 목적은 새 채용 경로와 실제 채용 법인을 찾는 것이다.
- **기업명 비고정(U 작업)**: `coverage_contract.json`의 `types[].unanchored_queries`를 web·wanted·saramin·jobkorea에서 각각 실행한다. 회사 이름을 붙이지 않는다. 결과에 후보 목록 밖 기업이 나오면 `candidate`로 추가한다.
- 검색마다 `results_reviewed`를 기록한다. 기준은 상위 10개 또는 결과 전체다. 1페이지 상단의 브랜드명 결과만 보고 멈추지 않는다. 위탁사·대행사 게시가 나오면 하위 결과에서 실제 채용 법인 페이지를 찾는다.
- 최근 30일을 우선하고 90일까지 넓힌다. 그 이전 게시라도 현재 모집이 원문으로 확인되면 포함한다.

## 4. 누락 방지 별칭

일레클/나인투원/쏘카, 킥고잉·씽씽/피유엠피/올룰로, 투루카/피플카, 그린카/G car, KM파크/카카오 T 주차, 모두의주차장/쏘카, 딜리/우아한형제들, 셔클/현대자동차.

## 5. 원칙

- 회사 존재, 채용 경로 존재, 현재 모집 중은 서로 다른 사실이다.
- 검색 스니펫이나 결과 수만으로 모집 중이나 부재를 확정하지 않는다.
- 같은 법인의 여러 브랜드는 근거 URL을 공유할 수 있지만, 채널 기록은 후보 행마다 이번 회차에 남긴다.
