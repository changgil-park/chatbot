# HELPDESK Agent Context

## 2026-10-02
- 폴더가 둘이다. `HELPDESK/` 는 웹 대시보드(직접 짠 `main.py` + `admin/index.html`), `HELPDESK_ingest/` 는 `@zio_skill` 스킬. 직접 짠 `main.py` 에는 자동 등록 표시가 없어 같은 폴더의 스킬 함수가 404 가 된다.
- `zio` CLI 는 api:8000 으로 부르는데 이 환경에서는 닿지 않는다. `curl http://api:8002/api/artifacts/skills/call/<폴더>/execute/<함수>` 를 쓴다.
- 이 환경에는 python·pdftoppm 이 없어 PDF 는 PyMuPDF 를 스킬로 돌려 읽었다. `HELPDESK_ingest/pdf_tools.py` 의 `extract_pdf`.
- 테이블 컬럼 타입은 Integer/String/Text/Boolean/Float/JSONB 만 쓴다(Date 없음). 날짜는 `YYYY-MM-DD HH:MM:SS` 문자열.
- `HDK_KnowMST` 의 분석은 사람이 아니라 Claude 가 했다(`anaBy=claude`). 검수 전. `relTarget` 일부(예 "RAG 한계")는 노드가 될 이름이 아직 정리되지 않았다.
- 조각(`HDK_ChunkMST.content`)은 PDF 줄바꿈이 단어 중간에서 끊겨 있어 섹션별로 정리해 넣었다. 단어는 원문 그대로.
- 미해결: 담당자 접미 미확정(온톨로지 라벨 만들기 전 필요), 챗봇 화면 형태, 원본 파일 대량 경로.

## 2026-10-02 (LZXP 매뉴얼 2건 적재)
- LZXP 매뉴얼_GEN(415쪽)·_PRJ(328쪽)은 ERP 화면별 사용법 문서. `lzxp_loader.py` 가 목차(`1.` `가.` `1)` 줄)를 읽고 본문에서 같은 제목 줄을 순서대로 찾아 잎 항목 단위로 쪼갠다(GEN 270 · PRJ 215조각). PRJ 목차는 쪽번호가 장마다 다시 시작해 쪽번호가 아니라 제목 검색을 쓴다. 목차 항목을 못 찾은 것은 0건.
- 지식 행은 규칙 기반이다(`anaBy=parser`, confidence 0.7). `화면`(조각당 1) · `기능`((1) 소제목, ￭ 불릿) · `필드`(용어설명·주요 입력 사항 아래) · `주의사항`(※ 긴 문장) · `연결`(본문의 `[다른 화면]` 언급). 줄이 단어 중간에서 끊겨 일부 문장에 어색한 띄어쓰기가 있고, PRJ 일부 쪽은 PDF 자체에 띄어쓰기가 없다.
- 화면 캡처는 텍스트에 없다. 이미지 목록은 `화면` 행 `attrJson.images`, 조각의 대표 이미지는 시작 쪽 미리보기(`imgFile`). 여러 항목이 한 쪽에 있으면 그 쪽의 이미지가 각 조각에 겹쳐 들어간다.
- 이미지 폴더(`manual_images/LZXP*`)는 GEN 231MB · PRJ 185MB 라 `.gitignore` 로 git 에서 뺐다. 디스크에만 있다.
- 적재는 `start_load`(백그라운드 스레드) → `load_status` 로 본다. 같은 문서를 다시 돌리면 그 문서의 조각·지식 행만 지우고 다시 넣는다(재실행으로 행 수 불변 확인).
- GEN/PRJ 의 의미(일반/프로젝트)는 파일명과 내용으로 추정한 것이다.
- 미해결: 분석 데이터 사람 검수, `연결` 행 `relTarget` 이 `가-2단가유형등록` 처럼 화면 제목과 정확히 일치하지 않는 것 정리, 증상·원인·해결 형태의 문서는 아직 없음.
