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

## 2026-10-02 (대시보드 데이터 탭)
- `HELPDESK/main.py` 가 `Zio` 를 직접 import 해 읽기 전용 API 를 낸다: `/api/overview` · `/api/modules` · `/api/know` · `/api/chunk/{id}`. 쓰기 API 는 없다. 사용자 입력은 `where`/`where_or` 의 값 자리로만 들어간다(이름 자리 금지 규칙). SDK import 가 실패해도 정적 화면은 뜨고 API 만 503.
- 결과는 30초 캐시한다(overview·modules). 화면의 새로고침 버튼은 `/api/overview?refresh=1` 로 캐시를 비우고 다시 센다.
- 이미지는 `/manual_images/<문서명>/{pages,embedded}/` 로 서빙한다(디스크 폴더 그대로). 이 폴더는 git 에 없으므로 다른 환경에서는 이미지가 안 뜬다.
- 데이터 품질로 보이는 것: 지식 행 중 `(이름 없음)` 소제목, 문장 전체가 subject 가 된 행이 있다(예: 소요량 산출 화면). `lzxp_loader.py` 의 소제목 판정 규칙 개선 거리.
- `PHASES` 체크 상태는 인덱스 기준(localStorage)이라 작업을 중간에 끼우면 저장된 체크가 어긋난다. 새 작업은 단계의 맨 끝에 추가한다.

## 2026-10-02 (KPI 측정용 테이블)
- `HELPDESK_ingest/kpi_tables.py` 의 `build_kpi_tables` 가 `HDK_EvalQMST`·`HDK_ChatLogMST`·`HDK_ToolLogMST` 를 만들고 평가 질문 15건(근거 있는 12 + 문서 밖 3)을 넣는다. 확인은 `peek_kpi`.
- 평가 질문과 정답 요지는 Claude 가 적재된 지식 행을 보고 쓴 **초안**이다(`reviewSt=초안`). KPI.md 가 요구하는 30~50개·사람 작성에는 못 미친다. 문서 밖 질문 Q014 는 검색으로 없음을 확인하지 않았다.
- `HDK_ChatLogMST`·`HDK_ToolLogMST` 는 챗봇이 쌓는 표라 0행이 정상이다. `qID` 칸으로 평가 질문과 연결한다.
- 미결: 질문 로그 보관 기간·마스킹 방침(KPI.md 4장).

## 2026-10-02 (Phase 3 챗봇)
- 검색은 `HELPDESK_ingest/helpdesk_search.py`. `HDK_KnowMST` 전체(1,733행)를 60초 메모리 캐시에 올려 파이썬에서 키워드 매칭한다(조사·어미 제거, 키워드의 절반 이상 맞아야 `found`). 행이 수만 건으로 늘면 DB 쪽 검색으로 바꿔야 한다. 온톨로지(Phase 2)가 없어 `Zio.node` 가 아니라 지식 표를 읽는다.
- `search_manual` 의 반환 키는 리터럴로 적어야 에이전트가 `{{search.found}}` 로 쓴다(`{**res}` 로 펼치면 `returns` 에 `context` 만 잡혔다).
- 에이전트 초안은 `chat_agent.py` 의 `build_chat_agent`(검색 skill → 답변 model). app_id 1, `compile` 통과, 경고 없음. **활성화와 `debug` 는 안 했다** — 입력이 어떻게 `question` 으로 들어오는지(트리거)는 웹 에이전트빌더에서 확인해야 한다. 고치려면 `build_chat_agent(replace_app_id=1)`.
- 대시보드 패널은 `HELPDESK/main.py` 의 `GET /api/chat` 이 같은 `search()` 를 sys.path 로 import 해 부른다. 모델 호출이 없어 문장 답변 대신 근거 3건과 출처를 보여준다.
- `eval_search` 결과: 답이 있는 질문 12/12, 문서 밖 3/3. 단, 평가 질문은 적재된 행을 보고 Claude 가 쓴 것이라 쉬운 편이다. KPI K6~K9 판정에 쓰려면 사람이 만든 30~50개로 다시 재야 한다.
- 알려진 한계: 매뉴얼과 다른 낱말로 물으면 못 찾는다(유의어 없음). 문서 밖 판정은 키워드 일치율이라, 매뉴얼에 있는 낱말이 섞인 문서 밖 질문은 걸릴 수 있다.
