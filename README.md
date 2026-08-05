# KIA 공공입찰 공고 자동 스크리너

매일 새벽 올라오는 나라장터·지자체 입찰공고 20건을 자동으로 분석하여 KIA 참여 가능 여부를 판단하고, **적극추천/검토/패스**로 분류하는 스크리닝 시스템입니다.

## 주요 기능

- **데이터 로드**: `projects/raw/` 구조의 마크다운 + JSON 메타데이터 자동 로드
- **사전 필터**: 마감경과/예산미달/업종미보유/지역제한 → 결정론적 차단 (LLM 비용 절약)
- **자격요건 매칭**: 규칙기반 1차 + LLM 2차 + 휴리스틱 폴백 (API 키 없어도 동작)
- **가중치 스코어링**: 자격적합도 35% + 예산적정성 20% + 실적매칭 20% + 평가유리도 15% - 리스크 10%
- **리포트 생성**: HTML(정렬/필터/상세펼침/CSV내보내기) + Markdown

## 설치 및 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (LLM 사용 시)
cp .env.example .env
# .env 에 Elice API 키 입력

# 3. 로컬 실행
python -m src.main screen --date 2025-08-05 --output ./reports/report --format html,md

# 4. 헬스 체크
python -m src.main check_env
```

## CLI 옵션

```bash
python -m src.main screen \
  --date 2025-08-05 \      # 기준일 (기본: 오늘)
  --output ./reports/report \  # 출력 경로 (확장자 제외)
  --format html,md \       # 출력 포맷
  --category 정보화사업,용역 \  # 카테고리 필터
  --verbose                # 상세 로그
```

## 출력 결과

- `reports/report.html` - 인터랙티브 웹 리포트 (정렬, 필터, 상세 펼침, CSV 내보내기)
- `reports/report.md` - 마크다운 리포트 (GitHub/콘솔용)

## Vercel 배포

이 프로젝트는 Vercel 서버리스 함수로 배포 가능합니다:

1. GitHub에 푸시
2. Vercel에서 프로젝트 임포트
3. 환경변수 설정:
   - `OPENAI_API_KEY`: Elice 발급 키
   - `OPENAI_BASE_URL`: `https://kia-ai.elice.io/v1`
   - `OPENAI_MODEL`: `openai/gpt-5.6-luna`
   - `OPENAI_EMBEDDING_MODEL`: `openai/text-embedding-3-small`
4. 배포 완료

### API 엔드포인트

- `GET /api/health` - 상태 확인
- `GET /api/config` - 설정 조회
- `GET /api/corpus` - 공고 목록
- `POST /api/screen` - 배치 스크리닝 실행

## 데이터 구조

```
projects/raw/
├── bids_md/           # 마크다운 변환본 (우선 사용)
├── bids/              # 원본 PDF
└── bid_meta/
    ├── *.json         # 각 공고 메타데이터
    └── company_profile.json  # KIA 프로필
```

## 아키텍처

참고: [Multi-Agent-Decision-Support-System-for-Public-Bidding](https://github.com/jhjung03eee/Multi-Agent-Decision-Support-System-for-Public-Bidding)

- **Prefilter First**: LLM 호출 전 결정론적 차단
- **Metadata Wins**: 메타데이터가 문서 파싱 결과보다 우선
- **Graceful Degradation**: 에러 발생해도 전체 중단 안 함
- **Offline Fallback**: API 키 없어도 휴리스틱으로 전체 동작