# backend

GitHub App 로그인 → 올해 커밋·푸시 수집 → 카드용 통계 JSON을 만드는 FastAPI 서버예요.
`prototype/` 프론트도 이 서버가 같이 서빙해서, 쿠키·CORS 설정이 필요 없어요.

## 1. GitHub App 등록 (한 번만)

GitHub → Settings → Developer settings → **GitHub Apps → New GitHub App**

| 항목 | 값 |
|---|---|
| GitHub App name | 아무거나 (예: `knu-code-wrapped`) → 주소의 이 이름이 `GH_APP_SLUG` |
| Homepage URL | `http://localhost:8000` (배포 후 실제 주소로) |
| Callback URL | `http://localhost:8000/auth/callback` |
| Request user authorization (OAuth) during installation | ✅ 체크 |
| Webhook → Active | ❌ 체크 해제 |
| Repository permissions → **Contents** | Read-only |
| Repository permissions → Metadata | Read-only (기본) |
| Where can this GitHub App be installed? | **Any account** |

만든 뒤 **Client ID** 복사, **Generate a new client secret** 으로 Secret 발급.
Private key 는 필요 없어요.

> ⚠️ Client Secret 은 `.env` 에만 넣고 채팅·코드·커밋에 붙여넣지 마세요.

## 2. 로컬 실행 (맥)

**처음 한 번만**
1. 터미널(⌘+Space → "터미널")에서 `python3 --version` 입력.
   설치 창이 뜨면 **설치**를 누르세요(개발자 도구가 깔리면서 `git`도 같이 생겨요).
2. 레포 받기
   ```bash
   cd ~/Documents
   git clone https://github.com/Aiden-Park11/Coding-Wrapped.git
   ```
3. GitHub App 설정 → Credentials → **New secret** 으로 비밀값 발급 (한 번만 보이니 바로 복사)

**실행 (매번)**
```bash
cd ~/Documents/Coding-Wrapped
./backend/run_mac.sh
```
- 처음 실행하면 `.env` 를 만들고 **텍스트 편집기**를 열어줘요 → `GH_CLIENT_SECRET=` 뒤에 붙여넣고 저장 → 다시 `./backend/run_mac.sh`
- `✅ 준비 완료!` 가 뜨면 브라우저에서 http://localhost:8000/auth/start
- 끄려면 터미널에서 `Ctrl + C`

> Windows 메모: 스마트 앱 컨트롤(애플리케이션 제어 정책)이 켜진 PC에서는 `pydantic_core` DLL 이 차단돼 FastAPI 가 실행되지 않아요(11/21 확인). 맥에서 실행하세요.

## 3. API

| 주소 | 설명 |
|---|---|
| `GET /auth/start` | 로그인 시작. 첫 방문은 앱 설치 화면, 재방문은 바로 승인 화면 |
| `GET /auth/callback` | GitHub 가 돌려보내는 주소. `state`·설치 정보 검증 후 분석 시작 |
| `GET /api/wrapped` | 분석 결과. `status`: `pending` → `done` / `error` (1초마다 폴링) |
| `GET /api/boj?handle=아이디` | 백준 티어·해결 수·많이 푼 유형 (solved.ac 공식 API v4, 앱 키 필요, 로그인 세션 전용) |
| `POST /auth/logout` | 세션 즉시 삭제 (카드 마지막의 "내 기록 지우고 나가기") |
| `GET /health` | 서버 상태 (잠자기 방지 핑용) |

## 4. 동작 원칙

- **올해 레포만**: `pushed_at` 이 올해 이전이거나 포크인 레포는 호출하지 않음
- **내 커밋 판별**: commits API 의 `author=` 파라미터는 git 이메일이 다른 커밋을 빠뜨려서(11/21 실측),
  전부 받은 뒤 `author.login` 으로 거름
- **속도**: 레포별 요청을 동시에(최대 8개) 보내고, 레포당 커밋 1,000개·상세 조회 60개로 제한
- **보안**: `state` 쿠키로 CSRF 방지, 콜백의 `installation_id` 는 실제 설치 목록과 대조,
  토큰은 분석이 끝나면 버리고 결과만 메모리에 2시간 보관
- **푸시 횟수**: Activity API 를 못 쓰면(권한·보관 기간) `null` 로 내려줌 → 프론트에서 카드 숨기기

## 5. 테스트

```bash
pip install pytest
python -m pytest -q
```

가짜 GitHub API 로 로그인 → 수집 → 통계 전체 흐름을 검증해요 (네트워크 불필요).

## 6. 배포 메모

레포 루트의 `render.yaml`(Blueprint)로 Render 에 올려요.

1. Render 대시보드 → **New → Blueprint** → 이 레포 선택
2. 비밀값 입력 칸이 뜨면 채우기
   - `GH_CLIENT_SECRET`: GitHub App 의 Client secret
   - `BASE_URL`: `https://coding-wrapped.onrender.com` (실제 서비스 주소, 끝에 `/` 없이)
   - `SOLVEDAC_CLIENT_ID` / `SOLVEDAC_CLIENT_SECRET`: 없으면 비워 두기 (백준 카드만 꺼짐)
3. GitHub App 설정에서 **Homepage URL** = `BASE_URL`, **Callback URL** = `BASE_URL/auth/callback` 추가
4. `https://.../health` 가 `github_configured: true` 인지 확인 → `/` 접속 → 로그인

주의
- **Root Directory 는 비워 두기.** `backend` 로 잡으면 `prototype/` 이 빠져서 `/` 가 404 예요.
- **워커 1개 유지.** 세션이 메모리에 있어서 워커를 늘리면 401 이 나요. 재배포·재시작하면 진행 중인 세션은 사라져요.
- 무료 플랜은 15분 동안 요청이 없으면 잠들어서 첫 접속이 30~60초 걸려요 → cron-job.org 등으로 `/health` 를 10분마다 호출.
- `/api/boj` 는 GitHub 로그인한 세션에서만, 세션당 1분 5회까지 응답해요 (solved.ac 개발자 약관 제6·7조).

## 아직 확인할 것

- [ ] 실제 GitHub App 토큰으로 Activity API(push) 가 Contents 읽기 권한만으로 되는지
- [ ] Activity API 에 올해 1월 기록까지 남아 있는지
- [x] 프론트(prototype)에 `/api/wrapped` 연결

> 백준: solved.ac 공식 API v4 사용. Backstage 에서 발급한 앱 키를 `.env` 의 `SOLVEDAC_CLIENT_ID` / `SOLVEDAC_CLIENT_SECRET` 에 넣으면 켜짐 (v3 는 지원 종료 예정)
