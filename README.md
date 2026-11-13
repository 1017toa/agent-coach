# agent-coach

**Claude Code·Codex 대화 기록으로 받는 1:1 AI 지시 코칭.**

Anthropic과 OpenAI가 공개한 공식 사용 가이드를 채점표로 삼아, `~/.claude`와 `~/.codex`에 이미 쌓여 있는 **내 실제 대화**를 채점합니다. 어떤 습관을 자주 빠뜨리는지 그래프로 보여 주고, 내가 실제로 쓴 지시를 "이렇게 썼다면" 형태로 고쳐 줍니다. 주기적으로 다시 돌리면 그동안의 새 대화만 채점해서 얼마나 나아졌는지 추세로 보여 줍니다.

> English: a local coach that grades how you direct Claude Code and Codex against the vendors' official guides, using your own transcripts. It shows weak habits, rewrites your real prompts, and tracks progress run over run.

## 특징

- **공식 가이드에 근거**: 항목마다 가이드 원문 섹션 링크가 붙어 있습니다 ([채점표](agentcoach/rubric/default.json)).
- **내 대화로 받는 예시**: 일반론 대신 내가 실제로 쓴 지시를 고쳐 씁니다.
- **성장 기록**: 회차마다 `~/.agent-coach/history/`에 저장합니다. 원본 대화가 자동 삭제돼도 점수 추이는 남습니다.
- **Claude Code와 Codex를 같은 기준으로**: 두 도구의 기록을 한 리포트에서 봅니다.
- **API 키 불필요**: 이미 로그인해 둔 `claude` 또는 `codex` CLI로 채점합니다. 없으면 키워드 기반 오프라인 채점으로 동작합니다.
- **로컬 전용**: 비밀키·이메일·전화번호는 가려서 채점기에 보내고, 결과는 내 컴퓨터에만 남습니다. 의존성 없는 Python 표준 라이브러리만 씁니다.

## 리포트 화면

한 화면에 탭 네 개로 나눠 봅니다. 스크롤이 길게 늘어지지 않도록 각 칸이 따로 스크롤되고, 휴대폰에서는 목록과 상세가 위아래로 바뀝니다.

- **개요**: 종합 점수, 집중할 항목 3개, 레이더 차트, 약한 순서 막대
- **항목별 코칭**: 왼쪽 항목 목록, 오른쪽 내 대화 고쳐 쓰기 예시·공식 가이드 근거·빠뜨린 대화
- **놓친 응답**: 원하는 응답을 못 받은 곳을 원인별로 나눠 보여 줌(아래 설명). 여러 대화에서 반복되는 빈틈은 규칙 파일 후보로 묶음
- **대화별 결과**: 대화 검색·항목 필터, 대화별 판정과 고쳐 쓰기
- **회차별 변화**: 항목별 추세

## 놓친 응답 분석

대화에 맥락이 쌓이면 짧은 지시로도 원하는 결과를 받을 수 있습니다. 그래서 지시가 짧다는 이유만으로는 감점하지 않고, **실제로 원하는 응답을 못 받은 곳**만 찾습니다.

- **찾는 신호**: 다음 턴에서 결과를 바로잡음, 같은 말을 되풀이함, 다시 하거나 되돌리라고 함, 사고·손해를 알림, 답답함을 표현함, 에이전트가 되물음
- **원인 분류**: 내 지시의 빈틈(나만 아는 정보가 빠졌고 맥락으로도 알 수 없었음) / 에이전트 잘못(맥락이 충분했음) / 마음이 바뀜 / 외부 요인
- **코칭**: 내 지시의 빈틈에만 "이 한 조각만 더했다면" 형태로 고쳐 쓰기를 붙입니다. 여러 대화에서 반복되는 빈틈은 CLAUDE.md·AGENTS.md·메모리·스킬·훅 중 어디에 한 줄로 남기면 되는지 묶어서 제안합니다.
- 원인 분류는 LLM 채점에서만 됩니다. 키워드 채점은 신호만 찾고 원인은 "미분류"로 둡니다.

## 채점 항목 (11개, 채점표 v2)

| 항목 | 가이드가 권하는 것 |
|---|---|
| 구체적인 맥락 | 목표와 함께 파일·화면·증상을 처음부터 짚기 |
| 완료 기준과 검증 방법 | 테스트·빌드·스크린샷처럼 통과/실패로 확인할 수단 주기 |
| 제약과 선호 | 건드리면 안 되는 것, 원하는 방식 미리 말하기 |
| 자료 직접 건네기 | 설명 대신 @파일·스크린샷·에러 원문 붙이기 |
| 범위와 결과물 형태 | 최소한인지 넉넉하게인지, 결과물 형식·길이 알려 주기 |
| 계획·인터뷰 먼저 | 크거나 막연한 일은 계획이나 질문부터 |
| 멈출 지점과 진행 방식 | 어디까지 알아서 하고 어디서 멈춰 물어볼지 정하기 |
| 증거 요구와 결과 검토 | "다 됐어요" 대신 명령·출력·diff 보기, 새 세션에 검토 맡기기 |
| 방향 바로잡기 | 두 번 교정해도 안 되면 새로 시작해 더 나은 프롬프트 쓰기 |
| 반복 지시는 규칙 파일로 | 되풀이하는 규칙은 CLAUDE.md·AGENTS.md·스킬로 옮기기 |
| 한 대화에 한 가지 결과 | 다른 일은 새 대화로, 긴 대화는 정리하기 |

### 출처

- Anthropic: [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices), [Getting the most out of Opus 5.5](https://claude.dev/blog/getting-the-most-out-of-opus-5-5/)
- Claude Academy: [AI 역량: 프레임워크 및 기초](https://academy.claude.com/ko/courses/ai-fluency-framework-foundations), [Claude Code 101](https://academy.claude.com/ko/courses/claude-code-101), [Claude Code 실전 활용](https://academy.claude.com/ko/courses/claude-code-in-action), [Claude 101](https://academy.claude.com/ko/courses/claude-101)
- OpenAI: [Codex Best practices](https://learn.chatgpt.com/guides/best-practices), [Codex Prompting](https://learn.chatgpt.com/docs/prompting)
- OpenAI Academy: [Get Started with Codex](https://academy.openai.com/public/courses/get-started-with-codex-jkhsq), [Agents and Workflows](https://academy.openai.com/public/courses/agents-and-workflows-y0qoc), [Extend Codex Workflows](https://academy.openai.com/public/courses/extend-codex-workflows-4e61p) (강좌 본문은 로그인 필요, 공개 소개만 반영)

채점표가 바뀌면 이전 회차에는 새 항목 점수가 없고, 리포트에 버전이 다르다는 안내가 붙습니다.

## 설치와 실행

Python 3.9 이상이 필요합니다.

```bash
pip install git+https://github.com/1017toa/agent-coach.git
```

```bash
agent-coach scan        # 채점 대상 대화 미리 보기 (모델 호출 없음)
agent-coach run         # 채점 → 기록 저장 → 리포트 열기
agent-coach history     # 회차별 점수 표
agent-coach report      # 저장된 기록으로 리포트만 다시 만들기
```

설치 없이 저장소에서 바로 돌리려면 `python -m agentcoach run` 을 씁니다.

자주 쓰는 옵션:

- `--days 30` / `--all`: 채점 기간 (기본값은 지난 채점 이후, 첫 회는 최근 14일)
- `--judge claude|codex|heuristic`: 채점기 선택 (기본 auto)
- `--model sonnet`: 채점 모델
- `--max-sessions 20`: 채점할 최대 대화 수. 대화 하나에 모델 호출 한 번이 듭니다.
- `--source claude` / `--source codex`: 한쪽 도구만
- `--rubric my-rubric.json`: 강의·팀에 맞춘 채점표 사용

## 주기적으로 다시 채점하기

1~2주에 한 번 `agent-coach run`을 돌리면 그 사이 대화만 새로 채점해 추세에 더해집니다.
Claude Code는 기본 설정에서 30일이 지난 대화를 지우므로, 그보다 짧은 주기를 권합니다.

## 개인정보

- 대화 원문은 내 컴퓨터를 떠나지 않습니다. 단, LLM 채점을 쓰면 해당 대화의 사용자 지시(가린 뒤)와 에이전트 행동 요약이 내가 쓰는 Claude/Codex 계정으로 전송됩니다. 원하지 않으면 `--judge heuristic`을 쓰세요.
- 스크립트로 돌린 `claude -p` / `codex exec` 대화와 앱이 자동으로 보낸 메시지는 기본적으로 제외합니다.
- 키·토큰·이메일·전화번호·주민번호·카드번호·도로명 주소는 자동으로 가립니다. 이름은 자동으로 알아낼 수 없으니 `~/.agent-coach/redact.txt`에 한 줄에 하나씩 적어 두세요(이름, 영문 이름, 회사명 등).

## 개발

```bash
python -m unittest discover -s tests
```

로드맵: 강의용 익명 집계 내보내기, 영어 리포트, 맞춤 채점표 예시, Cursor·Gemini CLI 지원.
