# 🚀 Fleet Data & AI Operations Portfolio

모빌리티/물류 도메인의 현장 비효율을 데이터와 AI 기술로 타개하는 시스템 구축 포트폴리오입니다.
**Next.js + Django REST Framework 기반의 풀스택 웹 플랫폼을 사내 공식 서비스로 런칭**했고, 강화학습 기반 노선 최적화와 RPA 자동화 파이프라인을 직접 구축했습니다.

> 일부 프로젝트의 소스 코드는 사내 보안 정책상 비공개입니다. 화면, 아키텍처 다이어그램, 시퀀스 다이어그램을 통해 작업 범위를 보여드립니다.

---

## 1. 📊 풀스택 웹 기반 DRT 운영 데이터 분석 플랫폼 — **사내 공식 서비스 배포**

비개발 직군 팀원들이 수동으로 데이터를 추출하고 엑셀로 가공하던 병목을 완전히 제거하기 위해, Next.js + Django REST Framework 기반의 풀스택 웹 플랫폼을 설계·구축하여 사내 공식 서비스로 배포했습니다.

* **Key Achievements:** 팀원 전체의 수동 데이터 추출·가공 소요 시간 **Zero화**, 나주·청주 멀티 리전 데이터 실시간 통합 조회 환경 구축
* **Tech Stack:** `Next.js + React`, `Zustand`, `TanStack Table`, `Django REST Framework`, `Celery`, `MySQL (멀티 리전)`
* **Core Logic:**
  * 드래그앤드롭으로 행/열/값을 구성하는 **동적 피벗 엔진** 구현 (SUM · AVG · DAY_AVG · COUNT 집계, Celery 비동기 처리)
  * **나주·청주 멀티 리전 MySQL DB** 동시 조회 아키텍처 설계 — 지역 코드 기반 자동 라우팅 및 결과 통합
  * MapLibre + DeckGL 기반 **공간 O-D 흐름 인터랙티브 지도** 시각화
  * 프리셋 스튜디오(분석 설정 저장·공유), 멀티 헤더 **Excel 내보내기**, 자체 에러 로그 시스템
  * CI/CD 하네스 구축 및 **Mutation Testing 56% kill rate** 달성

📂 **아키텍처 상세:** [`docs/architecture/`](./docs/architecture/) — 시스템 구성도, 데이터 흐름, 멀티 리전 라우팅 다이어그램

*(▲ 스크린샷 추가 예정 — 피벗 분석 화면 및 공간 O-D 지도)*

---

## 2. ⚡ Full-Pipeline RPA 기반 운영 보고서 자동화

매주 반복되던 데이터 취합 및 보고서 작성의 휴먼 에러를 방지하고 업무 시간을 극적으로 단축한 자동화 파이프라인입니다.

* **Key Achievements:** 주당 40분 이상 소요되던 업무를 **3분 이내로 단축 (92.5% 개선)** 및 휴먼 에러 0%
* **Tech Stack:** `Selenium`, `Pandas`, `xlwings`, `hwpWings`, `PyAutoGUI`
* **Core Logic:**
  * Selenium 웹 스크래핑 ➡️ Pandas 전처리(중복 제거, 시간 맵핑) 파이프라인 구축
  * 정규표현식과 xlwings를 활용한 구글 스프레드시트 GID 동적 연동 및 파워쿼리 업데이트
  * hwpWings를 통한 한글(HWP) 보고서 지정 필드 텍스트 자동 삽입 및 서식화

<img width="713" height="428" alt="제주 보고서 자동화_메인화면 및 주말추가" src="https://github.com/user-attachments/assets/c4399aa3-eddc-4757-bfd4-b68feb04465f" />
<img width="450" height="426" alt="제주 보고서 자동화_구글시트GUI추출" src="https://github.com/user-attachments/assets/f132d81b-0f4a-40d2-9112-07dbb98bf3b6" />

---

## 3. 🤖 강화학습(RL) 기반 최적 이동 노선 자동 생성 알고리즘

사람의 직관에 의존하던 버스/차량 노선 설계 방식을 데이터 기반의 시뮬레이션으로 전환하여 30개의 고효율 노선을 성공적으로 도출한 프로젝트입니다.

* **Key Achievements:** 기존 이동 거리를 유지하면서 **전체 잠재 수요의 20%를 커버**하는 최적 노선 도출
* **Tech Stack:** `Python`, `Stable Baselines3 (PPO)`, `Gymnasium`, `DBSCAN`, `OSRM API`
* **Core Logic:**
  * O-D(출발-도착) 패턴의 불명확성을 해결하기 위해 정류장 밀도 기반 **DBSCAN 군집화(Clustering)** 적용
  * OSRM 이동 거리, 잠재 수요, 노선 굴곡도(Cosine Similarity) 패널티를 종합한 **Reward Function을 DRT 운영 맥락에 맞춰 직접 설계**

<img width="3600" height="3000" alt="강화학습_노선결과1" src="https://github.com/user-attachments/assets/6f336ae6-5ce2-4952-ab5c-dc4f1bd9ae8a" />
*(▲ AI가 학습을 통해 도출한 최적 이동 노선 시각화)*
