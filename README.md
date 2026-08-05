# AI Go/No-Go Review Committee

매일 새벽 올라오는 공공 입찰공고 20건을 자동 스크리닝하여 **적극추천 / 검토 / 패스**로
분류하고, 살아남은 공고는 **영업 · 기술 · 재무 · 법무** 네 관점으로 병렬 심의한 뒤
위원장이 가중 투표로 최종 **GO / REVIEW / NO-GO**를 결정한다.

사람이 20건을 일일이 열어보면 2시간이 걸린다. 놓치면 기회 손실이고, 자격이 안 되는데
넣으면 입찰보증금을 날린다. 이 시스템은 그 판단 과정을 그대로 모델링한다.

문서를 요약하는 것이 목적이 아니라, 실제 기업의 Go/No-Go Committee 업무 프로세스를
AI 워크플로우로 구현하는 것이 목적이다.

---

## 아키텍처

```
공고 20건 (PDF / Markdown + 메타데이터 JSON)
        │
   Prefilter ── 자격미달 · 예산미달 · 마감경과   ← LLM 호출 없이 결정론적으로 제외
        │
   (통과한 공고만)
        │
   Supervisor Agent ── 워크플로우 제어
        │
   Parsing → RAG Indexing
        │
   ┌────────┬─────────┬─────────┬────────┐
   ▼        ▼         ▼         ▼
 Sales   Technical  Finance   Legal        ← 역할별 프롬프트 / 검색쿼리 / 평가기준
   └────────┴─────────┴─────────┴────────┘
        │
   Guardrails ── 인용 검증 · 근거 검증 · 신뢰도 임계값
        │
   Committee Chair ── 가중 투표 + 법무 거부권
        │
   추천 스코어링 → 한 페이지 스크리닝 리포트
```

**사전 필터가 먼저 도는 것이 핵심이다.** 마감이 지났거나 업종코드가 없어 애초에 참여할
수 없는 공고에 LLM 비용을 쓰지 않는다. 판단이 필요한 건만 위원회로 넘어간다.

### 왜 Multi-Agent인가

단일 프롬프트로 모든 판단을 내리면 책임을 분리할 수 없고, 오류 원인을 추적할 수 없다.
각 에이전트는 서로 다른 **역할 · 검색 쿼리 · 평가 기준 · 금지 주제**를 가지므로
"LLM을 여러 번 호출"하는 것이 아니라 역할 기반 의사결정(Role-Based Decision Making)이 된다.

| 위원 | 관점 | 평가 기준 | 가중치 |
| --- | --- | --- | --- |
| 영업 | Business | 사업 적합성 · 시장성 · 고객 적합성 · 전략적 가치 | 0.25 |
| 기술 | Engineering | 요구사항 충족 · 수행 가능성 · 보유 역량 · 기간 적절성 | 0.25 |
| 재무 | Financial | 예산 규모 · 수익성 · ROI · 대금 지급 조건 | 0.25 |
| 법무 | Compliance | 자격 충족 · 계약 위험 · 법적 제약 · 필수 인증 | 0.25 (**거부권**) |

### Context Engineering

모든 에이전트가 같은 문서를 읽지 않는다. 역할마다 검색 쿼리와 섹션 가중치가 다르므로
법무 위원은 자격요건·계약조항 청크를, 재무 위원은 예산·지급조건 청크를 받는다.
(`backend/app/agents/profiles.py`의 `queries` / `section_boost`)

### 가중 투표와 거부권

```
효과 가중치 = 역할 가중치 × (0.5 + 0.5 × 신뢰도)   ← 확신 없는 표는 영향력이 줄어든다
위원회 점수 = Σ(효과 가중치 × 판정 점수) / Σ(효과 가중치)
```

`≥0.70 → GO`, `≥0.45 → REVIEW`, 그 외 `NO-GO`.
단, **법무 위원이 신뢰도 0.7 이상으로 NO-GO를 내면 다수결과 무관하게 NO-GO**로 확정된다.
(지역제한 미충족처럼 다른 관점으로 상쇄할 수 없는 요건이 존재하기 때문)

### 사전 필터 (Prefilter)

에이전트가 돌기 전에 적용되는 결정론적 규칙. **확인 가능한 사실만** 공고를 차단하고,
판단이 필요한 것은 전부 위원회로 넘긴다.

| 조건 | 결과 |
| --- | --- |
| 마감일이 지남 | 차단 — `마감경과` |
| 예산 < 최소 수주 기준 | 차단 — `예산미달` |
| 요구 업종코드 미보유 | 차단 — `자격미달` |
| 지역제한 + 소재지 불일치 | 차단 — `자격미달` |
| 마감까지 남은 기간 < 최소 준비기간 | 경고 — `마감임박`, 차단하지 않고 우선순위 상승 |
| 마감일/예산 확인 불가 | 경고, 위원회로 넘김 |

마감임박을 차단하지 않는 이유는, 급하다고 참여 가치가 사라지는 것이 아니기 때문이다.
대신 같은 등급 안에서 마감이 가까운 순으로 정렬되어 리포트 맨 위에 올라온다.

### Guardrails

| # | 규칙 | 동작 |
| --- | --- | --- |
| 1 | Citation Validation | 검색되지 않은 `chunk_id`를 인용하면 해당 인용을 폐기하고 플래그 |
| 2 | Grounding Validation | 인용문이 원문과 토큰 60% 미만 일치하면 원문 스니펫으로 교체 |
| 3 | 근거 부족 | 유효 인용이 없으면 GO/NO-GO를 **REVIEW로 강등** |
| 4 | Confidence Threshold | 신뢰도가 임계값(기본 0.65) 미만이면 REVIEW로 강등 |
| 5 | Human-in-the-loop | 신뢰도 미달 · 검색 실패 · GO/NO-GO 정면 충돌 시 담당자 검토 요구 |

강등은 감추지 않고 `downgraded_from:GO` 같은 플래그로 UI에 그대로 노출된다.

### Evaluation Metrics

`/api/review` 응답의 `metrics`에 워크플로우 실행마다 산출된다.

- Citation Validity Rate — 유효 인용 / 전체 인용
- Grounding Rate — 인용으로 뒷받침된 주장 비율
- Mean Confidence, Total Latency, Chunk Count, LLM Provider

---

## 데이터셋

`projects/raw/` 레이아웃을 그대로 읽는다. 디렉터리만 놓으면 자동으로 인식된다.

```
projects/raw/
  bids/            입찰공고 원본 (PDF, MD)
  bids_md/         Markdown 변환본        ← 있으면 우선 사용
  bid_meta/
    <공고>.json    공고번호·발주처·마감일·예산·업종코드·지역
    company_profile.json   자사 자격·실적·인력
```

- **조인 키**: `bids_md/세종셔틀.md` ↔ `bid_meta/세종셔틀.json` (파일명 기준).
  메타 안의 `공고번호`로도 조인되므로 둘 중 어느 쪽이든 맞춰진다.
- **메타데이터 우선**: 메타에 있는 값이 문서 파싱 결과를 덮어쓴다. 메타는 정제된
  데이터이고, 정규식 파싱은 빈 칸을 메우는 역할만 한다.
- **키 이름 관용**: `발주처` / `발주기관` / `agency` / `organization` 을 모두 같은 필드로
  인식한다 (`app/screening/normalize.py`). 컬럼명이 바뀌면 크래시가 아니라 값이 비는
  것으로 degrade 된다.
- 깨진 JSON, 메타 없는 문서, 문서 없는 메타 모두 로딩을 중단시키지 않고 경고만 남긴다.

경로를 바꾸려면 `BIDCOM_CORPUS_DIR` 환경변수를 쓴다. `projects/raw` 가 없으면 번들된
데모 코퍼스(`data/demo_corpus`, 8건)로 폴백하므로 데이터 없이도 전체 기능이 돌아간다.

---

## LLM 연동

기본은 **오프라인 휴리스틱 모드**로 동작한다. API 키 없이도 파싱 · RAG · 4개 에이전트 ·
가드레일 · 가중 투표 · 보고서까지 전체 워크플로우가 그대로 실행된다.

`BIDCOM_GLM_API_KEY`를 설정하면 동일한 워크플로우가 GLM 호출로 전환되고,
호출이 실패하면 자동으로 휴리스틱 결과로 폴백하면서 `llm_fallback` 플래그를 남긴다.
즉 키 유무와 무관하게 시스템은 항상 검증 가능한 결과를 낸다.

```bash
BIDCOM_GLM_API_KEY=...            # 비우면 오프라인 모드
BIDCOM_GLM_MODEL=glm-5.2
BIDCOM_CONFIDENCE_THRESHOLD=0.65
```

전체 목록은 `.env.example` 참고.

---

## 로컬 실행

```bash
# 백엔드
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev          # http://localhost:5173
```

테스트:

```bash
cd backend && .venv/bin/python -m pytest
```

---

## Vercel 배포

리포지토리를 Vercel 프로젝트로 연결하면 `vercel.json` 설정으로 바로 배포된다.

- 프론트엔드: `frontend/` 를 빌드해 정적 호스팅 (`frontend/dist`)
- 백엔드: `api/index.py` 가 FastAPI 앱을 서버리스 함수로 노출하고 `/api/*` 요청이 라우팅됨
- 루트 `requirements.txt` 가 파이썬 의존성을 정의

**API 키 설정**: Vercel 대시보드 → Settings → Environment Variables 에서
`BIDCOM_GLM_API_KEY` 를 추가하고 재배포하면 GLM 모드로 전환된다.
키를 넣기 전까지는 오프라인 휴리스틱 모드로 정상 동작한다.

> 서버리스 환경 제약: 요청 바디 4.5MB 제한(업로드는 4MB로 제한), 함수 실행 60초 제한.
> SSE 스트리밍이 플랫폼에서 버퍼링되면 프론트엔드가 자동으로 단발성 `/api/review`
> 엔드포인트로 폴백한다.

---

## API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/health` | 상태 및 현재 LLM 프로바이더 |
| GET | `/api/config` | 회사 프로필 · 에이전트 정의 · 임계값 |
| GET | `/api/corpus` | 코퍼스 경로 · 공고 목록 · 자사 프로필 |
| POST | `/api/screen` | **배치 스크리닝 — 전 공고 필터링 + 심의 + 랭킹** |
| GET | `/api/samples` | 코퍼스 공고 목록 (단건 심의용) |
| POST | `/api/upload` | PDF/Markdown/TXT → 마크다운 변환 |
| POST | `/api/review` | 단건 심의 실행 |
| POST | `/api/review/stream` | 단건 심의 (SSE 진행 이벤트 스트리밍) |

---

## 프로젝트 구조

```
backend/app/
  supervisor.py        단건 심의 오케스트레이션 + 이벤트 스트림
  guardrails.py        인용/근거/신뢰도 검증
  screening/
    dataset.py         projects/raw 코퍼스 로딩 · 문서↔메타 조인
    normalize.py       메타데이터 키/날짜/금액 관용 파싱
    filters.py         사전 필터 (자격·예산·마감)
    screener.py        배치 실행 · 추천 스코어링 · 랭킹
  agents/
    profiles.py        역할별 프롬프트 · 검색쿼리 · 평가기준 · 가중치
    base.py            에이전트 실행 루프 및 응답 정규화
    heuristics.py      결정론적 역할 추론 (오프라인 모드 · 폴백)
    chair.py           가중 투표 · 거부권 · 경영진 보고서
  rag/                 파싱 · 청킹 · 임베딩 · 벡터 검색 · 리트리버
  llm/                 GLM 클라이언트 · 오프라인 프로바이더
frontend/src/          React 대시보드 (스크리닝 리포트 · 에이전트 카드 · 투표)
data/demo_corpus/      데모 코퍼스 8건 (projects/raw 와 동일 레이아웃)
api/index.py           Vercel 서버리스 진입점
```

### 데모 코퍼스 시나리오

사전 필터와 위원회 판단이 각각 어떤 경우에 작동하는지 보여주는 8건.

| 공고 | 결과 | 이유 |
| --- | --- | --- |
| 부산 DRT 운영 플랫폼 | **적극추천** | 역량 일치 · D-5 마감임박으로 최상단 정렬 |
| 인천 AI CCTV 관제 | **적극추천** | 영상분석·관제 역량 일치, 기술 중심 평가 |
| 세종 자율주행 셔틀 | **적극추천** | 자율주행 실적 보유, 선금/기성 지급 |
| 경기 정밀도로지도 | **적극추천** | 측량업 등록 요건은 법무 위원이 리스크로 지적 |
| 울산 교통데이터 분석 | 패스 | 사전 필터 — 마감경과 |
| 안양 단말기 유지관리 | 패스 | 사전 필터 — 예산미달 (1.2억) |
| 대구 스마트시티 | 패스 | 사전 필터 — 지역제한 소재지 불일치 |
| 제주 충전인프라 | 패스 | 사전 필터 — 업종코드 4290 미보유 |

8건 중 4건이 LLM 호출 없이 걸러진다.
