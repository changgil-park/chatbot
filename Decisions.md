# 의사결정 로그

> **사람이 보는 문서입니다.** 결정만 한 줄로 남깁니다. 근거 칸은 한 문장으로 줄입니다.
> 작업 진행 상황은 [WorkLog.md](WorkLog.md).

## 확정된 결정

| ID | 날짜 | 주제 | 결정 | 근거 |
|---|---|---|---|---|
| D001 | 2026-10-02 | HDK 테이블 3종 생성 | usr 테이블 HDK_DocMST · HDK_ChunkMST · HDK_KnowMST 를 camelCase 필드(01_NWSOFT_Table 스타일)로 생성. 컬럼 추가·삭제 불가 | 도메인 접두 HDK 로 이름 충돌 방지, 날짜는 Date 타입이 없어 문자열로 저장, 확장 칸은 attrJson(JSONB) 한 곳에 둠 |
| D002 | 2026-10-02 | 스킬 폴더 분리 | 웹 대시보드는 HELPDESK, 적재 스킬은 HELPDESK_ingest 로 분리 | HELPDESK 의 main.py 를 직접 관리해야 해서 같은 폴더에 @zio_skill 함수를 두면 등록되지 않음 |
| D003 | 2026-10-02 | 대용량 이미지 git 제외 | HELPDESK/manual_images/LZXP* 와 .skill_stderr.log 를 .gitignore 에 추가, 이미지는 디스크에만 보관 | LZXP 매뉴얼 이미지가 416MB 라 저장소에 넣으면 이력이 되돌릴 수 없게 비대해짐 |
| D004 | 2026-10-02 | KPI 측정용 테이블 3종 생성 | usr 테이블 HDK_EvalQMST · HDK_ChatLogMST · HDK_ToolLogMST 생성 (KPI.md 4장 가안 기준, Fg 칸은 Y/N 문자열). 컬럼 추가·삭제 불가 | K6~K17 측정에 질문·답변·도구 호출 기록이 필요하고 usr 표는 칸을 못 바꿔 로그를 쌓기 전에 확정해야 함 |

## 보류 · 후속 과제

| ID | 주제 | 상태 | 메모 |
|---|---|---|---|

## 기록 규칙

- 결정이 바뀌면 행을 지우지 말고 새 ID 를 추가한 뒤 옛 행에 취소선 + `→ D0NN로 대체` 를 적습니다.
- 여기 적는 것은 **되돌리기 어려운 선택**뿐입니다. 구현 상세·시행착오는 프로젝트 폴더의 `Agent_Context.md` 로 갑니다.
