# RAG vs 온톨로지 PDF 분석 결과를 HDK_DocMST · HDK_ChunkMST · HDK_KnowMST 테이블로 만들고 적재하는 스킬
import hashlib
from datetime import datetime
from pathlib import Path

from zio_ontology import Zio, zio_skill

ROOT = Path("/agent_skills/HELPDESK")
WHO = "HELPDESK_ingest"

# 공통 감사 컬럼 (01_NWSOFT_Table 스타일: regUid · regDt · modUid · modDt)
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


TABLES = {
    "HDK_DocMST": ("도움말 문서", "도움말 문서 1건(파일 1개)의 메타와 분석 요약", [
        _c("docID", pk=True), _c("fileNm"), _c("filePath"), _c("fileTy"), _c("fileHash"),
        _c("title"), _c("docTy"), _c("pageCnt", "Integer"), _c("charCnt", "Integer"),
        _c("imgDir"), _c("dataPath"), _c("summary", "Text"), _c("procSt"), _c("Rmk"),
    ] + AUDIT),
    "HDK_ChunkMST": ("문서 조각", "문서를 섹션 단위로 쪼갠 조각. 검색·근거 표기의 단위", [
        _c("chunkID", pk=True), _c("docID"), _c("seqNo", "Integer"), _c("locTy"),
        _c("pageNo", "Integer"), _c("pageEndNo", "Integer"), _c("secNo"), _c("title"),
        _c("content", "Text"), _c("charCnt", "Integer"), _c("imgFile"), _c("anlSt"),
    ] + AUDIT),
    "HDK_KnowMST": ("분석 지식", "조각에서 추출한 지식 항목. (subject)-[relType]->(relTarget) 은 온톨로지 엣지 후보", [
        _c("knowID", pk=True), _c("docID"), _c("chunkID"), _c("seqNo", "Integer"), _c("kind"),
        _c("subject"), _c("statement", "Text"), _c("evidence", "Text"),
        _c("relType"), _c("relTarget"), _c("attrJson", "JSONB"), _c("confidence", "Float"), _c("anaBy"),
    ] + AUDIT),
}

# ───────── 문서 정보 ─────────
PDF_NAME = "RAG_vs_온톨로지_차별점.pdf"
DOC_TITLE = "기존 RAG 한계 극복: agent.zio의 온톨로지 기반 지식 모델링"
DOC_SUMMARY = (
    "기존 RAG(Vector DB 중심)는 맥락 단절·다단계 추론 불가·갱신 충돌이라는 한계가 있어 산업용 에이전트에 부적합하다. "
    "agent.zio 는 노드·관계로 이뤄진 지식 그래프(온톨로지)를 핵심 두뇌로 삼아 팩트 기반 답변, Cypher 다단계 탐색, "
    "문서 분석에 따른 지식 자기 수선을 구현한다. Vector DB 는 범용 텍스트 검색용 서브 수단으로 혼용한다."
)

# ───────── 조각 (원문을 섹션별로 나누고 줄바꿈을 정리한 것) ─────────
# (secNo, title, pageNo, pageEndNo, imgFile, content)
CHUNKS = [
    ("0", "머리말", 1, 1, "p001.png",
     "기존 RAG 한계 극복: agent.zio의 온톨로지 기반 지식 모델링\n"
     "본 문서는 단순 Q&A 챗봇 수준을 넘어선 행동형(Agentic) AI 구축을 위해, agent.zio 가 왜 지식 그래프(Ontology)를 "
     "핵심 두뇌로 채택했는지에 대한 설계 사상을 설명합니다."),
    ("1", "기존 RAG (Vector DB 중심)의 치명적 한계", 1, 1, "p001.png",
     "현재 대중적으로 쓰이는 RAG(Retrieval-Augmented Generation)는 문서를 쪼개어(Chunking) 벡터 공간에 흩뿌린 뒤, "
     "사용자의 질문과 \"의미적 유사도\"가 높은 조각을 긁어오는 방식입니다. 블로그나 매뉴얼 검색에는 좋지만, "
     "산업용 AI 에이전트로 쓰기에는 다음과 같은 치명적 단점이 있습니다.\n"
     "- 맥락의 단절 (Context Loss): 유사도에만 의존하기 때문에 \"A가 B의 원인이다\" 혹은 \"A가 B 부서의 책임자이다\" "
     "같은 인과관계나 소속 관계형 팩트를 정확히 잡지 못합니다.\n"
     "- 다단계 추론(Multi-hop Reasoning) 불가: \"Helpdesk 인스턴스에서 가장 많은 에러를 발생시킨 파일의 담당자 이메일 주소는?\" "
     "같이 여러 다리를 건너야 하는 조합형 질문을 던지면, 벡터 검색은 엉뚱한 문서들을 섞어 돌려주다가 AI가 환각(Hallucination)에 빠지게 만듭니다.\n"
     "- 데이터 파편화 및 갱신 충돌: 정보가 업데이트될 때 과거 텍스트 청크와 새로운 청크가 충돌하며, "
     "\"정확한 팩트\" 하나를 도출해야 하는 엔터프라이즈 환경에서 논리적 결함을 유발합니다."),
    ("2", "agent.zio의 핵심 무기: 온톨로지(지식 그래프)", 1, 1, "p001.png",
     "agent.zio 는 이 한계를 깨기 위해 지식 그래프(Knowledge Graph) 기반의 온톨로지를 뇌로 삼았습니다. "
     "데이터를 뭉툭한 텍스트 바위가 아니라, 정교한 노드(Node)와 관계(Relationship)라는 수학적 명제로 정의합니다.\n"
     "온톨로지 기반 에이전트의 강력함\n"
     "1. 점과 선으로 연결된 절대적 팩트 (Fact-based): (이메일)-[작성됨]->(직원)-[소속됨]->(부서) 처럼 데이터를 거미줄처럼 엮습니다. "
     "AI는 어설프게 단어를 유추하지 않고, 이 관계망 노선을 그대로 따라가서 100% 팩트만 가져옵니다.\n"
     "2. Cypher 기반의 무궁무진한 다단계 탐색: 에이전트는 LLM의 코딩 능력을 활용해 스스로 Cypher 쿼리를 짜낼 수 있습니다. "
     "이 능력 덕분에 앞서 말한 극악의 3중, 4중 다단계 복합 질문조차 DB 쿼리 한 줄로 0.1초 만에 깔끔하게 가져옵니다.\n"
     "3. 데이터 자기 수선과 진화 (Data Enrichment): 새로운 문서를 읽으면 RAG처럼 텍스트를 던져두는 게 아닙니다. "
     "에이전트가 문서를 분석하여 새로운 노드(키워드)를 만들고, 기존에 알던 지식 노드와 새로운 관계 선(Edge)을 직접 연결하여 지식의 밀도를 계속 높여갑니다."),
    ("3", "요약: 왜 온톨로지여야 하는가?", 1, 1, "p001.png",
     "agent.zio 는 \"단순히 지식을 찾는 봇\"이 아니라 \"상황을 진단하고, 계획을 짜서, 시스템을 제어하는 행동형 AI\"를 지향합니다. "
     "가짜 정보로 시스템을 끄거나 제어하는 위험을 막으려면, 확률에 의존하는 Vector 유사도보다 수학적으로 증명된 명제(그래프) 형태의 지식 저장소가 필수적입니다.\n"
     "(물론 방대한 범용 텍스트 검색을 위해 ChromaDB 같은 Vector DB도 서브 무기로 혼용(Hybrid)하지만, "
     "시스템 행동을 결정짓는 척추 역할은 오직 온톨로지가 담당합니다.)"),
    ("4", "핵심 요약 (비교 표)", 1, 2, "p002.png",
     "구분 | Text 일방 전달 (RAG) | 온톨로지 (Ontology)\n"
     "데이터 크기 제한 | 토큰 한계에 걸림 | 필요한 것만 쿼리\n"
     "관계 이해 | AI가 추론 (실수/환각 가능) | 구조로 확정 (정확)\n"
     "재사용 체계 | 매번 전체 전달 (1회성) | 누적 & 갱신 (지속적 활용)\n"
     "복잡한 질문(Multi-hop) | \"RS0138-MM을 쓰는 모든 품목은?\" -> 문서를 처음부터 다시 읽어야 함 | "
     "MATCH (i)-[:BASED_ON]->(item {item_code:\"RS0138-MM\"}) -> 단 한 줄의 쿼리로 정확히 해결"),
]

# ───────── 분석 지식 ─────────
# (chunk secNo, kind, subject, statement, evidence, relType, relTarget, attrJson, confidence)
KNOW = [
    ("1", "용어", "RAG", "Retrieval-Augmented Generation. 문서를 쪼개 벡터 공간에 저장하고, 질문과 의미적 유사도가 높은 조각을 가져와 답하는 방식.",
     "문서를 쪼개어(Chunking) 벡터 공간에 흩뿌린 뒤, 사용자의 질문과 \"의미적 유사도\"가 높은 조각을 긁어오는 방식", "USES", "Vector DB", None, 1.0),
    ("1", "주장", "RAG 적합 영역", "RAG 는 블로그·매뉴얼 검색에는 좋지만 산업용 AI 에이전트로 쓰기에는 치명적 단점이 있다.",
     "블로그나 매뉴얼 검색에는 좋지만, 산업용 AI 에이전트로 쓰기에는 다음과 같은 치명적 단점이 있습니다", None, None, None, 1.0),
    ("1", "한계", "맥락의 단절 (Context Loss)", "유사도에만 의존해 인과관계·소속관계 같은 관계형 팩트를 정확히 잡지 못한다.",
     "유사도에만 의존하기 때문에 \"A가 B의 원인이다\" 혹은 \"A가 B 부서의 책임자이다\" 같은 인과관계나 소속 관계형 팩트를 정확히 잡지 못합니다", "HAS_LIMIT", "RAG", None, 1.0),
    ("1", "한계", "다단계 추론 불가 (Multi-hop)", "여러 다리를 건너야 하는 조합형 질문에 엉뚱한 문서를 섞어 돌려주고, 그 결과 AI 가 환각에 빠진다.",
     "벡터 검색은 엉뚱한 문서들을 섞어 돌려주다가 AI가 환각(Hallucination)에 빠지게 만듭니다", "HAS_LIMIT", "RAG", None, 1.0),
    ("1", "한계", "데이터 파편화 및 갱신 충돌", "정보 갱신 시 과거 청크와 새 청크가 충돌해, 정확한 팩트 하나를 도출해야 하는 환경에서 논리적 결함을 만든다.",
     "정보가 업데이트될 때 과거 텍스트 청크와 새로운 청크가 충돌하며", "HAS_LIMIT", "RAG", None, 1.0),
    ("1", "예시", "다단계 질문 예", "\"Helpdesk 인스턴스에서 가장 많은 에러를 발생시킨 파일의 담당자 이메일 주소는?\" 는 RAG 가 풀기 어려운 다단계 질문의 예.",
     "\"Helpdesk 인스턴스에서 가장 많은 에러를 발생시킨 파일의 담당자 이메일 주소는?\"", "EXAMPLE_OF", "다단계 추론 불가 (Multi-hop)", None, 1.0),
    ("0", "용어", "행동형(Agentic) AI", "단순 Q&A 챗봇을 넘어 상황을 진단하고 계획을 세워 시스템을 제어하는 AI.",
     "단순 Q&A 챗봇 수준을 넘어선 행동형(Agentic) AI", None, None, None, 1.0),
    ("2", "용어", "온톨로지 (지식 그래프)", "데이터를 텍스트 덩어리가 아니라 노드(Node)와 관계(Relationship)라는 명제로 정의한 지식 저장소.",
     "정교한 노드(Node)와 관계(Relationship)라는 수학적 명제로 정의합니다", "SOLVES", "RAG 한계", None, 1.0),
    ("2", "강점", "절대적 팩트 (Fact-based)", "(이메일)-[작성됨]->(직원)-[소속됨]->(부서) 처럼 데이터를 엮어, AI 가 단어를 유추하지 않고 관계망을 따라가 팩트만 가져온다.",
     "AI는 어설프게 단어를 유추하지 않고, 이 관계망 노선을 그대로 따라가서 100% 팩트만 가져옵니다", "HAS_STRENGTH", "온톨로지 (지식 그래프)",
     {"example": "(이메일)-[작성됨]->(직원)-[소속됨]->(부서)"}, 1.0),
    ("2", "강점", "Cypher 다단계 탐색", "LLM 이 스스로 Cypher 쿼리를 작성해 3~4중 다단계 질문도 쿼리 한 줄, 약 0.1초에 처리한다.",
     "3중, 4중 다단계 복합 질문조차 DB 쿼리 한 줄로 0.1초 만에 깔끔하게 가져옵니다", "HAS_STRENGTH", "온톨로지 (지식 그래프)", {"latency": "0.1초"}, 1.0),
    ("2", "용어", "Cypher", "그래프 DB(Neo4j)의 질의 언어. 에이전트가 LLM 의 코딩 능력으로 직접 작성한다.",
     "에이전트는 LLM의 코딩 능력을 활용해 스스로 Cypher 쿼리를 짜낼 수 있습니다", None, None, None, 1.0),
    ("2", "강점", "데이터 자기 수선과 진화 (Data Enrichment)", "새 문서를 읽으면 에이전트가 분석해 새 노드를 만들고 기존 노드와 엣지로 연결해 지식 밀도를 높인다.",
     "새로운 노드(키워드)를 만들고, 기존에 알던 지식 노드와 새로운 관계 선(Edge)을 직접 연결하여 지식의 밀도를 계속 높여갑니다", "HAS_STRENGTH", "온톨로지 (지식 그래프)", None, 1.0),
    ("3", "주장", "온톨로지가 필요한 이유", "가짜 정보로 시스템을 끄거나 제어하는 위험을 막으려면 확률 기반 Vector 유사도보다 명제(그래프) 형태의 지식 저장소가 필수적이다.",
     "확률에 의존하는 Vector 유사도보다 수학적으로 증명된 명제(그래프) 형태의 지식 저장소가 필수적입니다", "REQUIRED_FOR", "행동형(Agentic) AI", None, 1.0),
    ("3", "용어", "Hybrid 구성", "범용 텍스트 검색용으로 ChromaDB 같은 Vector DB 를 서브로 혼용하되, 시스템 행동을 결정하는 척추는 온톨로지가 맡는다.",
     "ChromaDB 같은 Vector DB도 서브 무기로 혼용(Hybrid)하지만, 시스템 행동을 결정짓는 척추 역할은 오직 온톨로지가 담당합니다", "COMPLEMENTS", "온톨로지 (지식 그래프)", {"subTool": "ChromaDB"}, 1.0),
    ("4", "비교", "데이터 크기 제한", "RAG 는 토큰 한계에 걸리고, 온톨로지는 필요한 것만 쿼리한다.", "데이터 크기 제한 | 토큰 한계에 걸림 | 필요한 것만 쿼리",
     None, None, {"rag": "토큰 한계에 걸림", "ontology": "필요한 것만 쿼리"}, 1.0),
    ("4", "비교", "관계 이해", "RAG 는 AI 가 추론해 실수·환각이 가능하고, 온톨로지는 구조로 확정해 정확하다.", "관계 이해 | AI가 추론 (실수/환각 가능) | 구조로 확정 (정확)",
     None, None, {"rag": "AI가 추론 (실수/환각 가능)", "ontology": "구조로 확정 (정확)"}, 1.0),
    ("4", "비교", "재사용 체계", "RAG 는 매번 전체를 전달하는 1회성이고, 온톨로지는 누적·갱신되어 지속 활용된다.", "재사용 체계 | 매번 전체 전달 (1회성) | 누적 & 갱신 (지속적 활용)",
     None, None, {"rag": "매번 전체 전달 (1회성)", "ontology": "누적 & 갱신 (지속적 활용)"}, 1.0),
    ("4", "비교", "복잡한 질문 (Multi-hop)", "RAG 는 문서를 처음부터 다시 읽어야 하지만, 온톨로지는 쿼리 한 줄로 정확히 해결한다.", "복잡한 질문(Multi-hop) | ... 문서를 처음부터 다시 읽어야 함 | ... 단 한 줄의 쿼리로 정확히 해결",
     None, None, {"rag": "문서를 처음부터 다시 읽어야 함", "ontology": "단 한 줄의 쿼리로 정확히 해결"}, 1.0),
    ("4", "예시", "Cypher 예시: 품목 역추적", "\"RS0138-MM을 쓰는 모든 품목은?\" 질문을 Cypher 한 줄로 해결하는 예.",
     "MATCH (i)-[:BASED_ON]->(item {item_code:\"RS0138-MM\"})", "EXAMPLE_OF", "Cypher 다단계 탐색",
     {"question": "RS0138-MM을 쓰는 모든 품목은?", "cypher": "MATCH (i)-[:BASED_ON]->(item {item_code:\"RS0138-MM\"})"}, 1.0),
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
def build_rag_manual(reset: bool = False) -> dict:
    """HDK_DocMST · HDK_ChunkMST · HDK_KnowMST 를 (없으면) 만들고 RAG vs 온톨로지 PDF 분석 결과를 적재합니다. 같은 파일을 다시 돌려도 행이 늘지 않습니다. reset=True 면 이 문서의 조각·지식 행을 지우고 다시 넣습니다."""
    created = []
    for name, (disp, desc, cols) in TABLES.items():
        if not _exists(name):
            Zio.entity(name).create_table(columns=cols, display_name=disp, description=desc)
            created.append(name)

    pdf = ROOT / PDF_NAME
    fhash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    doc_rows = Zio.entity("HDK_DocMST").where(fileHash=fhash).fetch().data
    now = _now()
    stamp = {"regUid": WHO, "regDt": now, "modUid": WHO, "modDt": now}
    doc_props = {
        "fileNm": PDF_NAME, "filePath": f"HELPDESK/{PDF_NAME}", "fileTy": "PDF", "fileHash": fhash,
        "title": DOC_TITLE, "docTy": "개념·설계사상", "pageCnt": 2,
        "charCnt": sum(len(c[5]) for c in CHUNKS),
        "imgDir": "HELPDESK/manual_images/RAG_vs_온톨로지_차별점", "dataPath": "HELPDESK/manual_data/RAG_vs_온톨로지_차별점.json",
        "summary": DOC_SUMMARY, "procSt": "분석완료", "Rmk": "내장 이미지 없음. 페이지 미리보기는 pages/ 폴더.",
    }
    if doc_rows:
        doc_id = doc_rows[0]["docID"]
        Zio.entity("HDK_DocMST").where(docID=doc_id).update({**doc_props, "modUid": WHO, "modDt": now})
    else:
        doc_id = f"DOC{Zio.entity('HDK_DocMST').count() + 1:06d}"
        Zio.entity("HDK_DocMST").create({"docID": doc_id, **doc_props, **stamp})

    # 이 문서의 조각·지식은 매번 지우고 다시 넣는다 (같은 키로 두 번 들어가지 않게)
    Zio.entity("HDK_KnowMST").where(docID=doc_id).delete()
    Zio.entity("HDK_ChunkMST").where(docID=doc_id).delete()

    chunk_id = {}
    for seq, (sec, title, p1, p2, img, content) in enumerate(CHUNKS, 1):
        cid = f"{doc_id}-C{seq:03d}"
        chunk_id[sec] = cid
        Zio.entity("HDK_ChunkMST").create({
            "chunkID": cid, "docID": doc_id, "seqNo": seq, "locTy": "PAGE", "pageNo": p1, "pageEndNo": p2,
            "secNo": sec, "title": title, "content": content, "charCnt": len(content), "imgFile": img, "anlSt": "완료", **stamp,
        })
    for seq, (sec, kind, subj, stmt, evid, rtype, rtarget, attr, conf) in enumerate(KNOW, 1):
        Zio.entity("HDK_KnowMST").create({
            "knowID": f"{doc_id}-K{seq:03d}", "docID": doc_id, "chunkID": chunk_id[sec], "seqNo": seq, "kind": kind,
            "subject": subj, "statement": stmt, "evidence": evid, "relType": rtype, "relTarget": rtarget,
            "attrJson": attr, "confidence": conf, "anaBy": "claude", **stamp,
        })

    return {
        "created_tables": created, "docID": doc_id,
        "counts": {t: Zio.entity(t).count() for t in TABLES},
    }


@zio_skill
def peek_manual(table: str = "HDK_KnowMST", limit: int = 3) -> dict:
    """HDK_ 테이블의 앞쪽 행을 돌려주어 적재 결과를 확인합니다(읽기 전용). table 은 HDK_DocMST · HDK_ChunkMST · HDK_KnowMST 중 하나."""
    if table not in TABLES:
        return {"error": f"알 수 없는 테이블입니다. 가능한 값: {list(TABLES)}"}
    return {"count": Zio.entity(table).count(), "rows": Zio.entity(table).fetch().data[:limit]}
