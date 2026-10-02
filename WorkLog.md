# 작업 로그

> **사람이 보는 문서입니다.** 한 건에 한 줄. 현재 상태를 훑어보는 용도입니다.
> 결정은 [Decisions.md](Decisions.md), 구현 상세·시행착오는 각 프로젝트 폴더의 `Agent_Context.md` 에 있습니다.
> 상태 표기: `진행중` · `완료` · `보류` · `중단`

| 날짜 | 프로젝트 | 담당 | 한 줄 요약 | 상태 |
|---|---|---|---|---|
| 2026-10-02 | HELPDESK | claude | 프로젝트 폴더 생성, 작업계획서(Plan.md)·KPI(KPI.md)·흐름도 작성 | 완료 |
| 2026-10-02 | HELPDESK | claude | 다크/라이트 대시보드 웹페이지(/skills/HELPDESK/) 작성 | 완료 |
| 2026-10-02 | HELPDESK_ingest | claude | RAG vs 온톨로지 PDF 분석, HDK_DocMST·ChunkMST·KnowMST 생성 및 적재(문서 1·조각 5·지식 19) | 완료 |
| 2026-10-02 | HELPDESK_ingest | claude | LZXP 매뉴얼 GEN·PRJ(743쪽) 목차 기준 자동 분할·추출, 조각 485·지식 1,714행 적재 (이미지 폴더 별도) | 완료 |
| 2026-10-02 | HELPDESK | claude | 대시보드에 DB 실시간 현황 연결 (데이터 탭: 적재 현황·지식 분포·모듈별 화면 수·지식 탐색·원문/이미지 보기), 작업 내역 카드 추가 | 완료 |
| 2026-10-02 | HELPDESK_ingest | claude | KPI 측정용 HDK_EvalQMST·ChatLogMST·ToolLogMST 생성(kpi_tables.py), 평가 질문 초안 15건 적재, 재실행 시 15행 유지 확인 | 완료 |
| 2026-10-02 | HELPDESK · HELPDESK_ingest | claude | Phase 3 챗봇 — 검색 스킬(search_manual)·에이전트 초안(app_id 1, 컴파일 확인)·대시보드 챗봇 패널(/api/chat) 연결. 평가 질문 15건 검색 단독 측정 통과 | 완료 (에이전트 활성화·화면 호출은 미검증) |
