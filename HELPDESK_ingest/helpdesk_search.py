# 질문 문장에서 키워드를 뽑아 HDK_KnowMST 를 검색하고 근거(문서명·쪽)와 함께 돌려주는 챗봇용 검색 스킬
import math
import re
import time

from zio_ontology import Zio, zio_skill

# 조사·어미·질문 투의 말. 길이가 긴 것부터 떼어 낸다.
ENDINGS = sorted([
    "하는거", "하는법", "하는", "하려면", "하려고", "하나요", "할때", "하면", "해줘", "해주세요", "합니까", "하는지",
    "으로", "에서", "에게", "이란", "이며", "이고", "인가요", "인지", "한", "할", "해", "은", "는", "이", "가", "을", "를",
    "에", "의", "도", "로", "와", "과", "요", "야", "줘", "만",
], key=len, reverse=True)
STOP = {
    "알려줘", "알려주세요", "알려", "방법", "어떻게", "어떤", "무엇", "뭐야", "뭔가요", "무슨", "있나요", "있어", "되나요", "되는",
    "않으면", "안되면", "보이지", "경우", "관련", "대해", "대한", "때문", "정말", "혹시", "이거", "그거", "어디",
}
# 정보가 얇은 종류는 점수를 깎는다 (연결 행은 "상기 메뉴" 같은 조각 문장이 많다)
KIND_W = {"연결": 0.5}

_cache = {}


def _load(ttl=60):
    hit = _cache.get("all")
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    know = Zio.entity("HDK_KnowMST").columns("knowID", "docID", "chunkID", "kind", "subject", "statement").fetch().data
    docs = {d["docID"]: d["title"] for d in Zio.entity("HDK_DocMST").columns("docID", "title").fetch().data}
    chunks = {c["chunkID"]: c for c in Zio.entity("HDK_ChunkMST").columns("chunkID", "title", "pageNo", "pageEndNo").fetch().data}
    val = {"know": know, "docs": docs, "chunks": chunks}
    _cache["all"] = (time.time(), val)
    return val


def keywords(question: str) -> list:
    """질문에서 검색 키워드를 뽑는다. 조사·어미를 떼고 두 글자 미만과 질문 투의 말은 버린다."""
    out = []
    for w in re.findall(r"[0-9A-Za-z가-힣]+", question):
        for _ in range(2):
            for e in ENDINGS:
                if w.endswith(e) and len(w) - len(e) >= 2:
                    w = w[: -len(e)]
                    break
        if len(w) >= 2 and w not in STOP and w.lower() not in [o.lower() for o in out]:
            out.append(w)
    return out


def search(question: str, limit: int = 5) -> dict:
    """키워드가 절반 이상 맞는 지식 행을 점수순으로 돌려준다. 못 찾으면 found=False."""
    kws = keywords(question)
    if not kws:
        return {"found": False, "keywords": [], "items": [], "reason": "검색할 키워드가 없습니다."}
    data = _load()
    need = math.ceil(len(kws) / 2)
    scored = []
    for r in data["know"]:
        subj, stmt = (r["subject"] or "").lower(), (r["statement"] or "").lower()
        matched, score = [], 0.0
        for k in kws:
            kl = k.lower()
            if kl in subj:
                matched.append(k)
                score += 3
            elif kl in stmt:
                matched.append(k)
                score += 1.5
        if len(matched) >= need:
            scored.append(((score + 2 * len(matched)) * KIND_W.get(r["kind"], 1.0), matched, r))
    scored.sort(key=lambda x: (-x[0], x[2]["knowID"]))

    items, seen = [], set()
    for sc, matched, r in scored:
        sig = ((r["subject"] or "").strip(), (r["statement"] or "")[:80])
        if sig in seen:  # GEN·PRJ 매뉴얼에 같은 문장이 있으면 한 번만
            continue
        seen.add(sig)
        ch = data["chunks"].get(r["chunkID"], {})
        pg, pe = ch.get("pageNo"), ch.get("pageEndNo")
        items.append({
            "knowID": r["knowID"], "kind": r["kind"], "subject": r["subject"], "statement": (r["statement"] or "")[:500],
            "doc": data["docs"].get(r["docID"], r["docID"]), "docID": r["docID"], "section": ch.get("title"),
            "page": f"p.{pg}" + (f"~{pe}" if pe and pe != pg else "") if pg else None,
            "score": round(sc, 1), "matched": matched,
        })
        if len(items) >= limit:
            break
    return {"found": bool(items), "keywords": kws, "need": need, "items": items,
            "reason": "" if items else f"키워드 {len(kws)}개 중 {need}개 이상 맞는 항목이 없습니다."}


def render_context(res: dict) -> str:
    """모델 프롬프트에 넣을 근거 목록 글."""
    if not res["found"]:
        return "(검색된 근거 없음)"
    return "\n".join(
        f"[{i}] ({it['kind']}) {it['subject']}\n    {it['statement']}\n    출처: {it['doc']} {it['page'] or ''} {it['section'] or ''}".rstrip()
        for i, it in enumerate(res["items"], 1)
    )


@zio_skill
def search_manual(question: str = "", limit: int = 5, input: dict = None) -> dict:
    """사용자 질문으로 도움말 지식(HDK_KnowMST)을 검색해 근거 목록을 돌려줍니다. found=False 면 문서에 답이 없는 것이니 지어내지 말고 '문서에서 찾을 수 없다'고 답해야 합니다. context 는 모델 프롬프트에 그대로 넣을 근거 글입니다."""
    q = question or (input or {}).get("question") or (input or {}).get("message") or ""
    res = search(q, max(1, min(int(limit), 10)))
    # 에이전트가 {{search.필드}} 로 쓸 수 있게 반환 필드를 리터럴 키로 적는다
    return {"question": q, "found": res["found"], "keywords": res["keywords"], "items": res["items"],
            "reason": res["reason"], "context": render_context(res)}


@zio_skill
def eval_search(limit: int = 5) -> dict:
    """HDK_EvalQMST 평가 질문으로 검색만 단독 측정합니다(읽기 전용). 답이 있는 질문은 기대 근거가 상위 limit 건에 드는지, 문서 밖 질문은 found=False 인지 봅니다. 답변 문장의 품질이 아니라 검색이 근거를 가져오는지만 잽니다."""
    data = _load()
    by_id = {r["knowID"]: r for r in data["know"]}
    rows, hit_y, tot_y, ok_n, tot_n = [], 0, 0, 0, 0
    for q in sorted(Zio.entity("HDK_EvalQMST").fetch().data, key=lambda r: r["qID"]):
        res = search(q["question"], limit)
        ids = [it["knowID"] for it in res["items"]]
        if q["hasAnsFg"] == "Y":
            exp = by_id.get(q["expectedKnow"]) or {}
            subs = [(it["subject"], it["statement"][:80]) for it in res["items"]]
            ok = q["expectedKnow"] in ids or (exp.get("subject"), (exp.get("statement") or "")[:80]) in subs
            tot_y += 1
            hit_y += ok
        else:
            ok = not res["found"]
            tot_n += 1
            ok_n += ok
        rows.append({"qID": q["qID"], "ok": ok, "found": res["found"], "keywords": res["keywords"], "top": ids[:3], "expected": q["expectedKnow"]})
    return {"answerable": f"{hit_y}/{tot_y}", "out_of_scope": f"{ok_n}/{tot_n}", "rows": rows}
