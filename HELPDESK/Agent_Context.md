# HELPDESK Agent Context

## 2026-10-02
- 폴더가 둘이다. `HELPDESK/` 는 웹 대시보드(직접 짠 `main.py` + `admin/index.html`), `HELPDESK_ingest/` 는 `@zio_skill` 스킬. 직접 짠 `main.py` 에는 자동 등록 표시가 없어 같은 폴더의 스킬 함수가 404 가 된다.
- `zio` CLI 는 api:8000 으로 부르는데 이 환경에서는 닿지 않는다. `curl http://api:8002/api/artifacts/skills/call/<폴더>/execute/<함수>` 를 쓴다.
- 이 환경에는 python·pdftoppm 이 없어 PDF 는 PyMuPDF 를 스킬로 돌려 읽었다. `HELPDESK_ingest/pdf_tools.py` 의 `extract_pdf`.
- 테이블 컬럼 타입은 Integer/String/Text/Boolean/Float/JSONB 만 쓴다(Date 없음). 날짜는 `YYYY-MM-DD HH:MM:SS` 문자열.
- `HDK_KnowMST` 의 분석은 사람이 아니라 Claude 가 했다(`anaBy=claude`). 검수 전. `relTarget` 일부(예 "RAG 한계")는 노드가 될 이름이 아직 정리되지 않았다.
- 조각(`HDK_ChunkMST.content`)은 PDF 줄바꿈이 단어 중간에서 끊겨 있어 섹션별로 정리해 넣었다. 단어는 원문 그대로.
- 미해결: 담당자 접미 미확정(온톨로지 라벨 만들기 전 필요), 챗봇 화면 형태, 원본 파일 대량 경로.
