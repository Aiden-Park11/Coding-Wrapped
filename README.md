# Coding-Wrapped

> 2026 경북대 컴퓨터학부 해커톤 · 주제: 컴퓨터학부 학생에게 필요한 서비스

GitHub 계정만 연결하면, 1년 동안의 코딩 활동을 스포티파이 Wrapped처럼 넘겨보는 카드로 만들어주는 서비스예요.

## 카드 구성

| # | 카드 | 내용 |
|---|---|---|
| 0 | 인트로 | 잔디 그래프 + "올해, 당신은 어떤 개발자였을까요?" |
| 1 | 올해의 숫자 | 커밋 수, 레포 수, 커밋한 날, 최장 연속 커밋, 주력 언어 |
| 2 | 코딩 시간대 | 요일 × 시간대 히트맵, 새벽 커밋 비율 |
| 3 | 커밋 메시지 | 자주 쓴 메시지 순위, 가장 많이 갈아엎은 파일 |
| 3½ | 백준 (선택) | 티어, 푼 문제 수, 많이 푼 유형 — 백준 아이디를 넣었을 때만 |
| 4 | DEVTI | 개발자 MBTI 16유형 (시간대·리듬·협업·커밋 크기) + 16유형 목록 |
| 5 | 팀플 궁합 | 찰떡/위험 유형, 친구 유형 골라서 궁합 보기 |
| 6 | RPG 스탯창 | 주력 언어 직업, 레벨, HP/MP/EXP, 스탯 |
| 7 | 공유 카드 | 요약 이미지 + 내년 처방전 |

## 폴더 구조

```
.
├── docs/
│   └── coding-wrapped-plan.md   # 기획서 (GitHub App 연동, 보안, 일정)
├── prototype/
│   ├── index.html               # 픽셀 테마 프로토타입 (예시 데이터)
│   └── fonts/                   # Galmuri 픽셀 폰트 (OFL)
└── backend/                     # GitHub App 연동 코드 (작업 예정)
```

## 프로토타입 실행

`prototype/index.html`을 브라우저로 열면 돼요. 폰트를 상대 경로로 불러오기 때문에 `fonts/` 폴더와 같이 있어야 해요.

- 탭 / 스와이프 / `←` `→` 키로 넘기기
- 꾹 누르거나 스페이스바로 일시정지
- 백엔드로 열어야 동작해요 (GitHub 로그인 후 실제 데이터만 사용, 데모 모드 없음)

배포 주소: https://coding-wrapped-00ej.onrender.com (GitHub Pages 같은 정적 호스팅에서는 서버가 없어서 동작하지 않아요)

## 백엔드 실행 (맥)

```bash
git clone https://github.com/Aiden-Park11/Coding-Wrapped.git
cd Coding-Wrapped
./backend/run_mac.sh      # 처음엔 .env 비밀값 입력 안내가 떠요
```
자세한 내용은 [`backend/README.md`](backend/README.md).

## 기술 스택 (예정)

- **Frontend**: HTML/CSS/JS 카드 UI, html2canvas(공유 이미지)
- **Backend**: GitHub App (읽기 전용) + GitHub REST/GraphQL API
- **AI**: 코딩 유형 설명·처방전 문구 생성 (집계 숫자만 전달)

## 보안 원칙

- 코드 본문은 읽지 않고 메타데이터(커밋 시각, 메시지, 파일명)만 사용
- 원본은 저장하지 않고 집계 결과만 보관
- 토큰은 백엔드에만, `.env`는 커밋 금지
