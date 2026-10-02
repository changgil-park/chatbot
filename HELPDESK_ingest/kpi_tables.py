# KPI 측정용 HDK_ChatLogMST · HDK_ToolLogMST · HDK_EvalQMST 를 만들고 평가 질문 초안을 적재하는 스킬
from datetime import datetime

from zio_ontology import Zio, zio_skill

WHO = "HELPDESK_ingest"

AUDIT = [
    {"name": "regUid", "type": "String", "nullable": True},
    {"name": "regDt", "type": "String", "nullable": True},
    {"name": "modUid", "type": "String", "nullable": True},
    {"name": "modDt", "type": "String", "nullable": True},
]


def _c(name, typ="String", pk=False):
    col = {"name": name, "type": typ}
    if pk:
        col["pk"] = True
    else:
        col["nullable"] = True
    return col


# usr 테이블은 칸을 못 바꾼다. Fg 칸은 01_NWSOFT_Table 스타일대로 'Y'/'N' 한 글자 문자열이다.
KPI_TABLES = {
    "HDK_EvalQMST": ("평가 질문셋", "K6~K9 측정용 평가 질문과 정답 요지·근거 위치. 문서가 갱신될 때마다 같은 질문으로 회귀 측정한다", [
        _c("qID", pk=True), _c("qTy"), _c("question", "Text"), _c("expectedAns", "Text"),
        _c("expectedDoc"), _c("expectedKnow"), _c("hasAnsFg"), _c("reviewSt"), _c("Rmk"),
    ] + AUDIT),
    "HDK_ChatLogMST": ("질문 답변 기록", "챗봇 질문·답변 1건. K6~K12(정확도·출처·응답시간·해결·피드백) 측정용", [
        _c("chatID", pk=True), _c("sessionID"), _c("qID"), _c("question", "Text"), _c("answer", "Text"),
        _c("srcList", "JSONB"), _c("respMs", "Integer"), _c("feedback"), _c("resolvedFg"), _c("judgeSt"), _c("Rmk"),
    ] + AUDIT),
    "HDK_ToolLogMST": ("도구 호출 기록", "챗봇의 도구 호출 1건. K15~K17(자동 해결·오류·의도 외 변경) 측정용", [
        _c("callID", pk=True), _c("chatID"), _c("toolID"), _c("argJson", "JSONB"), _c("resultSt"),
        _c("errMsg", "Text"), _c("confirmFg"), _c("Rmk"),
    ] + AUDIT),
}

# 평가 질문 초안 — Claude 가 이미 적재된 지식 행을 보고 쓴 것이다. 사람 검수 전(reviewSt=초안).
# (qID, qTy, 질문, 정답 요지, 근거 docID, 근거 knowID, 문서에 답이 있는가)
EVALQ = [
    ("Q001", "개념", "RAG 의 '맥락의 단절' 한계는 무엇인가요?", "유사도에만 의존해 인과관계·소속관계 같은 관계형 팩트를 정확히 잡지 못한다.", "DOC000001", "DOC000001-K003", "Y"),
    ("Q002", "개념", "RAG 가 여러 단계를 건너야 하는 질문에 약한 이유는?", "조합형 질문에 엉뚱한 문서를 섞어 돌려주고, 그 결과 AI 가 환각에 빠진다.", "DOC000001", "DOC000001-K004", "Y"),
    ("Q003", "개념", "정보를 갱신하면 RAG 에서 어떤 문제가 생기나요?", "과거 청크와 새 청크가 충돌해 정확한 팩트 하나를 도출해야 하는 환경에서 논리적 결함이 생긴다.", "DOC000001", "DOC000001-K005", "Y"),
    ("Q004", "개념", "온톨로지는 어떻게 단어를 유추하지 않고 팩트를 가져오나요?", "데이터를 (이메일)-[작성됨]->(직원)-[소속됨]->(부서) 처럼 관계로 엮어 관계망을 따라가 팩트만 가져온다.", "DOC000001", "DOC000001-K009", "Y"),
    ("Q005", "개념", "온톨로지의 다단계 질문 처리 방식과 속도는?", "LLM 이 Cypher 쿼리를 직접 작성해 3~4중 다단계 질문도 쿼리 한 줄, 약 0.1초에 처리한다.", "DOC000001", "DOC000001-K010", "Y"),
    ("Q006", "개념", "새 문서를 읽으면 온톨로지는 어떻게 달라지나요?", "에이전트가 분석해 새 노드를 만들고 기존 노드와 엣지로 연결해 지식 밀도를 높인다.", "DOC000001", "DOC000001-K012", "Y"),
    ("Q007", "사용법", "품목코드 등록에서 검사방법을 선택하지 않으면 어떤 값이 저장되나요?", "무검사가 기본값으로 저장된다. 선택지는 전수검사·샘플링검사·무검사·일괄검사이다.", "DOC000002", "DOC000002-K00033", "Y"),
    ("Q008", "사용법", "QuickMenu 에 등록한 메뉴가 보이지 않으면 어디를 확인하나요?", "해당 메뉴에 대한 메뉴권한 설정을 확인한다. 권한이 없는 메뉴는 등록은 되지만 QuickMenu 대분류에 보이지 않는다.", "DOC000002", "DOC000002-K00107", "Y"),
    ("Q009", "사용법", "발주서 등록에서 분할납기를 쓰면 대표 납기일은 어떻게 표시되나요?", "분할납기일 경우 가장 마지막(최종) 납기일이 대표로 표시된다.", "DOC000002", "DOC000002-K00330", "Y"),
    ("Q010", "사용법", "품목분류 등록 화면에서는 무엇을 하나요?", "품목에 관한 분류 기준을 대분류·중분류·소분류로 세부 설정한다.", "DOC000002", "DOC000002-K00017", "Y"),
    ("Q011", "사용법", "수출/수입 제비용코드 등록에서 상대계정코드는 어떻게 입력하나요?", "입력란을 더블클릭해 [회계 - 기준정보 - 계정코드등록] 에 등록된 계정코드 목록에서 선택한다.", "DOC000003", "DOC000003-K00762", "Y"),
    ("Q012", "사용법", "사용자별 메뉴권한 설정 화면은 어떤 용도인가요?", "사용자 개개인의 메뉴 권한을 설정해, 개인별로 필요한 메뉴만 쓰게 한다.", "DOC000002", "DOC000002-K00117", "Y"),
    ("Q013", "문서밖", "사내 VPN 접속 비밀번호를 초기화하려면 어떻게 하나요?", "적재된 문서에 없는 내용이다. 모른다고 답해야 한다.", None, None, "N"),
    ("Q014", "문서밖", "LZXP 모바일 앱의 푸시 알림은 어떻게 켜나요?", "적재된 문서에 없는 내용으로 보인다(검색으로 확인하지 않음). 모른다고 답해야 한다.", None, None, "N"),
    ("Q015", "문서밖", "오늘 점심 구내식당 메뉴가 뭔가요?", "도움말 범위 밖의 질문이다. 모른다고 답해야 한다.", None, None, "N"),
]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _exists(table):
    try:
        Zio.entity(table).count()
        return True
    except Exception:
        return False


@zio_skill
def build_kpi_tables() -> dict:
    """HDK_EvalQMST · HDK_ChatLogMST · HDK_ToolLogMST 를 (없으면) 만들고 평가 질문 초안 15건을 넣습니다. 다시 돌려도 행이 늘지 않고 같은 qID 는 갱신됩니다. 대화·도구 로그는 챗봇이 쌓는 표라 비어 있는 것이 정상입니다."""
    created = []
    for name, (disp, desc, cols) in KPI_TABLES.items():
        if not _exists(name):
            Zio.entity(name).create_table(columns=cols, display_name=disp, description=desc)
            created.append(name)

    now = _now()
    inserted = updated = 0
    for qid, qty, q, ans, doc, know, has in EVALQ:
        props = {"qTy": qty, "question": q, "expectedAns": ans, "expectedDoc": doc, "expectedKnow": know,
                 "hasAnsFg": has, "reviewSt": "초안", "Rmk": "Claude 초안. 사람이 질문·정답 요지를 검수해야 한다."}
        if Zio.entity("HDK_EvalQMST").where(qID=qid).count():
            Zio.entity("HDK_EvalQMST").where(qID=qid).update({**props, "modUid": WHO, "modDt": now})
            updated += 1
        else:
            Zio.entity("HDK_EvalQMST").create({"qID": qid, **props, "regUid": WHO, "regDt": now, "modUid": WHO, "modDt": now})
            inserted += 1

    return {"created_tables": created, "evalq": {"inserted": inserted, "updated": updated},
            "counts": {t: Zio.entity(t).count() for t in KPI_TABLES}}


@zio_skill
def peek_kpi(table: str = "HDK_EvalQMST", limit: int = 20) -> dict:
    """KPI 측정용 표의 앞쪽 행을 돌려줍니다(읽기 전용). table 은 HDK_EvalQMST · HDK_ChatLogMST · HDK_ToolLogMST 중 하나."""
    if table not in KPI_TABLES:
        return {"error": f"알 수 없는 테이블입니다. 가능한 값: {list(KPI_TABLES)}"}
    return {"count": Zio.entity(table).count(), "rows": Zio.entity(table).fetch().data[:limit]}
