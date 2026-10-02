# 검색 스킬(search_manual)과 답변 모델을 잇는 HELPDESK 챗봇 에이전트 초안을 만들고 확인하는 스킬
from zio_ontology import Zio, zio_skill

TITLE = "HELPDESK 챗봇"

PROMPT = (
    "당신은 LZXP 도움말 헬프데스크 챗봇입니다. 아래 '근거'에 적힌 내용만으로 질문에 답하세요.\n\n"
    "## 규칙\n"
    "- 근거에 없는 내용은 지어내지 마세요. 근거가 없거나 질문과 맞지 않으면 \"문서에서 찾을 수 없습니다.\"라고만 답하세요.\n"
    "- 답변 끝에 사용한 근거의 출처(문서명·쪽)를 \"출처: 문서명 p.쪽\" 형태로 항상 적으세요.\n"
    "- 화면 이름과 메뉴 경로는 근거에 적힌 그대로 쓰세요.\n"
    "- 짧고 순서가 있는 안내로 답하세요.\n\n"
    "## 질문\n{{search.question}}\n\n"
    "## 검색 결과 (found={{search.found}})\n{{search.context}}"
)


@zio_skill
def build_chat_agent(replace_app_id: str = "") -> dict:
    """HELPDESK 챗봇 에이전트(검색 skill → 답변 model)를 초안으로 만듭니다. 활성화는 웹 에이전트빌더에서 사람이 합니다. replace_app_id 를 주면 그 초안의 설계를 교체합니다."""
    nodes = [
        {"kind": "skill", "name": "search", "skill": "HELPDESK_ingest/search_manual"},
        {"kind": "model", "name": "answer", "prompt": PROMPT, "output_schema": {"answer": "str", "found": "bool"}},
    ]
    if replace_app_id:
        Zio.agent.update(replace_app_id, nodes=nodes)
        app_id, warnings = replace_app_id, []
    else:
        got = Zio.agent.create(title=TITLE, nodes=nodes)
        app_id, warnings = got["app_id"], got.get("warnings")
    try:
        compiled = Zio.agent.compile(app_id)
    except Exception as ex:
        compiled = f"compile 실패: {ex!r}"
    return {"app_id": app_id, "warnings": warnings, "compile": compiled}


@zio_skill
def show_chat_agent(app_id: str = "") -> dict:
    """에이전트 목록(또는 app_id 한 건의 노드·엣지)을 돌려줍니다(읽기 전용). 검색 스킬이 에이전트 쪽에 어떤 입력·출력으로 보이는지도 함께 봅니다."""
    skill = Zio.agent.skills(query="search_manual")
    if app_id:
        return {"agent": Zio.agent.get(app_id), "skill": skill}
    return {"agents": Zio.agent.list(), "skill": skill}
