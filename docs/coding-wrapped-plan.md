# 코딩 Wrapped 기획서

> 2026 컴퓨터학부 해커톤 · 주제: 컴퓨터학부 학생에게 필요한 서비스
> 개발 기간: 11/11(수) 14:00 ~ 11/24(화) 12:00

---

## 1. 한 줄 소개

GitHub와 백준 계정만 연결하면, 1년 동안의 코딩 활동을 스포티파이 Wrapped처럼 넘겨보는 카드로 만들어주는 서비스.

> **분석 기간: 올해 (2026-01-01 ~ 현재)** — 처음엔 이번 학기(9월~)였지만, 학기 데이터만으로는 카드가 비어 보여서 1년 단위로 변경.

> **백준 연동: 11/23 보류** — solved.ac 가 외부 요청을 막고 있어(403) 이번 버전에서는 제외. 공식 협의 후 다시 추가 예정. 아래 백준 관련 내용은 참고용.

## 2. 왜 필요한가

- **회고**: 컴퓨터학부 학생은 코딩을 많이 하지만 "올해 뭘 했는지" 돌아보지 않는다. 자동으로 회고를 만들어준다.
- **동기부여**: 공유하고 싶은 결과물이 생기면 꾸준히 코딩할 이유가 생긴다.
- **내년 가이드**: 약한 알고리즘 유형, 개선할 습관을 처방전으로 제시해서 재미로 끝나지 않게 한다.

---

## 3. 카드 구성

| # | 카드 | 내용 | 데이터 출처 |
|---|---|---|---|
| 0 | 인트로 | "올해, 당신은 어떤 개발자였을까요?" | - |
| 1 | 올해의 숫자 | 총 커밋, 기여 레포, 백준 해결 수, 최장 연속 커밋, 주력 언어 | GitHub, solved.ac |
| 2 | 코딩 시간대 | 요일 × 시간대 히트맵, 새벽 커밋 비율 | GitHub 커밋 시각 |
| 3 | 커밋 메시지 | 자주 쓴 메시지 순위, 가장 짧은 메시지, 가장 많이 갈아엎은 파일 | GitHub 커밋 |
| 4 | 백준 성장 | 티어 변화, 월별 해결 수, 많이 푼 유형, 오래 붙잡은 문제 | solved.ac |
| 5 | 코딩 유형 | 4개 축으로 분류한 유형 이름 + 설명 | 위 데이터 종합 |
| 6 | 공유 카드 | 요약 이미지 + 내년 처방전 | 위 데이터 종합 |

### 코딩 유형 4개 축

- 아침형 / 야행성 — 커밋 시간대
- 꾸준형 / 몰아치기형 — 커밋 날짜 분포
- 잘게 커밋 / 크게 커밋 — 커밋 수 ÷ 푸시 수, 커밋당 변경 줄 수
- 솔로 / 협업 — 다른 사람과 함께 쓰는 레포 비율

결과 예시: **"야행성 몰아치기 솔로 리팩토러"**

### 추가 카드 아이디어

- **몰아넣기 지수**: 커밋 수 ÷ 푸시 수 ("한 번 푸시할 때 평균 4.1개씩 몰아서 올렸어요")
- **force push 횟수**: "올해 강제로 덮어쓴 횟수: 7번"
- **로딩 화면**: "당신의 새벽 커밋을 세는 중…" 문구가 순서대로 바뀌는 화면

### 디자인 시안

- 모바일 카드 7장 (390×844)
- 색: 검정 `#111111`, 연두 `#D4FF3A`, 보라 `#5B3DE8`, 아이보리 `#F4F1EA`
- 폰트: Noto Sans KR + Space Grotesk(숫자)
- 시안 링크: https://claude.ai/artifact/BMMStEwhbL3dUmGDfBTTE1

> ⚠️ "학부 평균보다 2.3배", "상위 8%" 같은 학부 비교 문구는 다른 사용자 데이터가 쌓여야 계산 가능. 데모에서는 빼거나 팀원 데이터로만 비교한다.

---

## 4. 기술 구조

```
[사용자] → GitHub로 시작하기
   ↓
[GitHub App 설치 화면] → 레포 선택 → Install
   ↓
[백엔드 콜백] code → 사용자 토큰
   ↓
[데이터 수집] GitHub API (동시 요청) + solved.ac API
   ↓
[통계 계산] 시간대 변환, 히트맵, 메시지 집계, 유형 판정, LLM 코멘트
   ↓
[결과 캐싱] → 프론트 카드 렌더링 → 공유 이미지 생성
```

- **백엔드**: OAuth 콜백, 데이터 수집, 통계 계산, 캐싱
- **프론트**: 세로 스와이프 카드, 숫자 카운트업 애니메이션, html2canvas로 공유 이미지
- **LLM**: 코딩 유형 설명, 처방전 문구 생성

---

## 5. GitHub 연동: GitHub App 사용

### 왜 OAuth App이 아니라 GitHub App인가

| 방식 | 비공개 레포 | 사용자 입장 | 난이도 |
|---|---|---|---|
| 공개 레포만 | ✗ | 부담 없음 | 쉬움 |
| OAuth App + `repo` 권한 | ✓ 전부 | 모든 비공개 레포 **읽기·쓰기** 권한을 넘겨야 함 | 쉬움 |
| **GitHub App** | ✓ 고른 레포만 | 레포를 직접 고르고, **읽기 전용** | 중간 |
| 잔디 숫자만 (GraphQL) | 개수만 | 부담 없음 | 쉬움 |

→ **GitHub App**: 사용자가 레포를 고르고, 읽기 권한만 준다. 발표에서 "읽기 권한만, 고른 레포만 받습니다"라고 말할 수 있다.

### 앱 등록 (한 번만, 10~20분)

GitHub → Settings → Developer settings → GitHub Apps → New GitHub App

- Callback URL: `http://localhost:8000/auth/callback` (개발용)
- **Request user authorization (OAuth) during installation**: ✅ 체크
- Webhook: Active 체크 해제
- Repository permissions
  - Contents: **Read-only**
  - Metadata: Read-only (기본)
  - 나머지: No access
- Client ID, Client Secret 발급 → 백엔드 환경변수에 저장

### 불러오는 순서

1. 사용자가 "GitHub로 시작하기" 클릭 → `https://github.com/apps/{앱이름}/installations/new`
2. 사용자가 레포 선택 후 Install
3. 콜백으로 `?code=...&installation_id=...` 도착
4. `POST https://github.com/login/oauth/access_token` 으로 code → 사용자 토큰(`ghu_...`)
5. `GET /user` 로 로그인 아이디 확인
6. `GET /user/installations/{installation_id}/repositories` 로 허용된 레포 목록
7. 레포마다 동시에:
   - `GET /repos/{owner}/{repo}/commits?since=2026-01-01T00:00:00Z` → 받은 뒤 코드에서 `author.login == 내 아이디`로 필터 (⚠️ `author=` 파라미터는 이메일이 다른 커밋을 빠뜨림, 11/21 실측)
   - `GET /repos/{owner}/{repo}/activity?activity_type=push&actor={login}`
   - `GET /repos/{owner}/{repo}/activity?activity_type=force_push&actor={login}`
8. 통계 계산 → 캐싱 → 카드 표시

> 토큰은 **앱에 허용된 레포 ∩ 사용자가 원래 접근 가능한 레포**에만 쓸 수 있다.

### 푸시 횟수 가져오기

- **Activity API** (`/repos/{owner}/{repo}/activity`): `activity_type=push`, `actor=아이디`로 필터. 레포마다 호출. **← 사용**
- Events API (`/users/{username}/events`의 PushEvent): 최근 90일(일부 문서는 30일), 최대 300개 제한. 1년 통계에는 쓸 수 없음.
- 주의: GitHub에 **성공한 푸시만** 기록됨. 실패한 `git push`는 안 세짐.

---

## 6. 비공개 레포 데이터 처리 원칙

1. **코드 내용은 안 읽는다.** 커밋 시간, 메시지, 파일 이름, 변경 줄 수만 사용.
2. **원본은 저장하지 않는다.** 분석 후 집계 결과만 남긴다.
3. **공유 카드에서는 가린다.** 비공개 레포 이름, 커밋 메시지 원문은 본인 화면에서만. 공유 이미지엔 숫자와 흔한 단어만.
4. **토큰은 백엔드에만.** 암호화 저장, "연결 해제" 시 즉시 삭제.

→ 화면에 **"읽는 것 / 읽지 않는 것"**으로 정리해서 보여주기.

---

## 7. 속도 목표: 결과 1분 안에 (목표 10~20초)

- **동시 요청**: 레포를 하나씩이 아니라 한꺼번에 호출 (가장 효과 큼)
- **건너뛰기**: `pushed_at`이 올해 이전인 레포, 포크 레포는 호출하지 않음
- **기간 제한**: `since=2026-01-01` (올해 1월 1일부터)
- **먼저 보여주기**: 첫 카드(올해의 숫자)는 GraphQL `contributionsCollection` 한 번으로 1~2초 안에. 나머지는 사용자가 카드 보는 동안 뒤에서 계산
- **캐싱**: 한 번 계산한 결과는 저장해서 재방문 시 바로 표시

```python
import asyncio, httpx

API = "https://api.github.com"

async def fetch_repo(c, full, login, h):
    commits, pushes = await asyncio.gather(
        c.get(f"{API}/repos/{full}/commits",
              params={"since": "2026-01-01T00:00:00Z", "per_page": 100}, headers=h),
        c.get(f"{API}/repos/{full}/activity",
              params={"activity_type": "push", "actor": login, "per_page": 100}, headers=h),
    )
    mine = [x for x in commits.json() if (x.get("author") or {}).get("login") == login]
    return {"repo": full, "commits": mine, "pushes": pushes.json()}

async def fetch_all(repos, login, h):
    targets = [r["full_name"] for r in repos
               if not r["fork"] and r["pushed_at"] >= "2026-01-01"]
    async with httpx.AsyncClient(timeout=20) as c:
        return await asyncio.gather(*[fetch_repo(c, f, login, h) for f in targets])
```

---

## 8. 로그인 목표: 클릭 3번, 20초 안

1. 우리 사이트: **"GitHub로 시작하기"** 버튼 하나 (회원가입 양식 없음)
2. GitHub 로그인 (이미 로그인돼 있으면 생략)
3. 설치 화면: **초록색 Install** 버튼 (기본값 "All repositories" 그대로 넘어가도 됨)
4. 콜백 → 바로 로딩 화면 + 분석 시작

### 이탈 줄이는 장치

- 버튼 아래 안내: *"다음 화면에서 초록색 Install 버튼만 누르면 돼요. 코드는 읽지 않고, 읽기 권한만 받아요."*
- 재방문자: 설치 화면 대신 `github.com/login/oauth/authorize?client_id=...`로 보내서 클릭 없이 통과
- 백준: solved.ac는 공개 데이터라 **아이디만 입력**. 로딩 중에 입력받기

---

## 9. 개발 일정

| 날짜 | 할 일 |
|---|---|
| 11/19(목) 밤 | 카드 목록 확정, GitHub App 등록, solved.ac API 테스트 |
| 11/20(금) | 백엔드: GitHub App 로그인, 데이터 수집(동시 요청), 통계 계산 |
| 11/21(토) | 프론트: 카드 UI, 스와이프, 애니메이션, 로딩 화면 |
| 11/22(일) | 코딩 유형 판정, LLM 코멘트, 공유 이미지 |
| 11/23(월) | 팀원 실제 계정으로 테스트, 배포, 발표자료 |
| 11/24(화) 오전 | 최종 점검 후 12:00 전 제출 |

### 예상 소요 시간 (GitHub 연동)

| 작업 | 해본 사람 | 처음 하는 사람 |
|---|---|---|
| GitHub App 등록 | 10분 | 20분 |
| 로그인·콜백·토큰 교환 | 30분 | 1~2시간 |
| 레포 목록 + 커밋·푸시 가져오기 | 30분 | 1시간 |
| 권한 에러, 페이지네이션 | 0~30분 | 1~2시간 |
| **합계** | **1~2시간** | **3~5시간** |

통계 계산까지 포함하면 하루.

---

## 10. 주의사항 체크리스트

- [ ] **시간대**: GitHub 커밋 시각은 UTC → **+9시간** 변환 필수
- [ ] **내 커밋만**: 팀 레포는 `author`로 필터. git 이메일이 GitHub 계정과 다르면 커밋이 빠질 수 있음
- [ ] **페이지네이션**: 한 번에 최대 100개. 넘으면 응답 헤더 `Link` 따라 다음 페이지
- [ ] **`state` 파라미터**: CSRF 방지용으로 OAuth 요청에 포함
- [ ] **토큰 만료**: 사용자 토큰 기본 8시간. 로그인 직후 분석하면 문제없음
- [ ] **`installation_id` 누락**: 재로그인 시 안 올 수 있음 → `GET /user/installations`로 조회
- [ ] **Activity API 권한**: Contents 읽기만으로 호출되는지 **먼저 본인 비공개 레포로 테스트**. 403이면 권한 추가
- [ ] **Activity API 보관 기간**: **1월 기록까지** 나오는지 확인 (안 남으면 푸시 카드는 "최근 N개월"로 표시)
- [ ] **학교 조직 레포**: GitHub Classroom 등 조직 레포는 관리자 승인 없이 앱 설치가 안 될 수 있음. 팀원 과제 레포 위치 확인
- [ ] **호출 제한**: 토큰당 시간당 5,000번. 결과 캐싱으로 대응
- [ ] **커밋 적은 계정**: 신입생은 데이터가 적을 수 있음. "이제 시작이에요" 카드 준비
- [ ] **데모 계정**: 활동 많은 **공개 레포** 계정으로 준비해서 발표 중 권한 문제 방지
- [ ] **Client Secret**: 백엔드에만. 프론트·깃허브에 절대 올리지 않기
