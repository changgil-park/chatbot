# HELPDESK 대시보드(admin/)와 이미지를 서빙하고, HDK 테이블 현황을 읽기 전용 API 로 제공하는 웹 스킬 서버
import os
import time
from collections import Counter
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

try:
    from zio_ontology import Zio
except Exception as ex:  # SDK 가 없어도 정적 화면은 떠야 한다
    Zio, ZIO_ERR = None, repr(ex)

BASE = Path(__file__).parent
app = FastAPI(title="HELPDESK")

KINDS = ["화면", "기능", "필드", "주의사항", "연결", "용어", "한계", "강점", "비교", "예시", "주장"]
CACHE = {}


def cached(key, fn, ttl=30):
    hit = CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    CACHE[key] = (time.time(), val)
    return val


def need_sdk():
    if Zio is None:
        raise HTTPException(503, f"Zio SDK 를 불러오지 못했습니다: {ZIO_ERR}")


def ent(table):
    return Zio.entity(table)


@app.get("/api/health")
def health():
    return {"status": "ok", "skill": "HELPDESK", "sdk": Zio is not None}


@app.get("/api/overview")
def overview(refresh: int = 0):
    """문서별 조각·지식 건수와 kind 분포. refresh=1 이면 캐시를 버리고 다시 센다."""
    need_sdk()
    if refresh:
        CACHE.clear()

    def build():
        docs = ent("HDK_DocMST").columns("docID", "title", "fileNm", "fileTy", "docTy", "pageCnt", "charCnt", "procSt", "summary", "imgDir", "regDt").fetch().data
        out = []
        for d in sorted(docs, key=lambda r: r["docID"]):
            kinds = {k: ent("HDK_KnowMST").where(docID=d["docID"], kind=k).count() for k in KINDS}
            out.append({**d, "chunks": ent("HDK_ChunkMST").where(docID=d["docID"]).count(),
                        "know": ent("HDK_KnowMST").where(docID=d["docID"]).count(), "kinds": {k: v for k, v in kinds.items() if v}})
        totals = {t: ent(t).count() for t in ("HDK_DocMST", "HDK_ChunkMST", "HDK_KnowMST")}
        return {"totals": totals, "docs": out}

    return cached("overview", build)


@app.get("/api/modules")
def modules(docID: str):
    """문서의 모듈(장)·그룹별 화면 수. 화면 행의 attrJson 을 집계한다."""
    need_sdk()

    def build():
        rows = ent("HDK_KnowMST").where(docID=docID, kind="화면").columns("attrJson").fetch().data
        mods, groups = Counter(), {}
        for r in rows:
            a = r.get("attrJson") or {}
            m, g = a.get("module") or "(미분류)", a.get("group") or ""
            mods[m] += 1
            groups.setdefault(m, Counter())[g] += 1
        return [{"module": m, "count": c, "groups": [{"group": g, "count": n} for g, n in groups[m].items()]} for m, c in mods.items()]

    return cached(f"modules:{docID}", build)


@app.get("/api/know")
def know(docID: str = "", kind: str = "", q: str = "", limit: int = 40):
    """지식 행 검색. 값은 전부 where 의 값 자리로만 들어간다."""
    need_sdk()
    limit = max(1, min(limit, 100))
    f = ent("HDK_KnowMST").columns("knowID", "docID", "chunkID", "kind", "subject", "statement", "relType", "relTarget", "attrJson", "anaBy", "confidence")
    if docID:
        f = f.where(docID=docID)
    if kind:
        f = f.where(kind=kind)
    if q.strip():
        f = f.where_or(subject__contains=q.strip(), statement__contains=q.strip())
    rows = f.fetch().data
    rows.sort(key=lambda r: r["knowID"])
    return {"total": len(rows), "rows": rows[:limit]}


@app.get("/api/chunk/{chunk_id}")
def chunk(chunk_id: str):
    """조각 본문과 미리보기 이미지 위치."""
    need_sdk()
    rows = ent("HDK_ChunkMST").where(chunkID=chunk_id).fetch().data
    if not rows:
        raise HTTPException(404, "조각이 없습니다")
    c = rows[0]
    doc = ent("HDK_DocMST").where(docID=c["docID"]).columns("title", "imgDir").fetch().data
    stem = Path(doc[0]["imgDir"]).name if doc else ""
    return {k: c[k] for k in ("chunkID", "docID", "seqNo", "secNo", "title", "content", "pageNo", "pageEndNo", "imgFile")} | {"docTitle": doc[0]["title"] if doc else "", "imgStem": stem}


# 라우트를 먼저 등록하고, 루트 마운트는 맨 마지막에 둔다 (/docs, /api 가 가려지지 않도록)
app.mount("/images", StaticFiles(directory=str(BASE / "images")), name="images")
(BASE / "manual_images").mkdir(exist_ok=True)
app.mount("/manual_images", StaticFiles(directory=str(BASE / "manual_images")), name="manual_images")
app.mount("/", StaticFiles(directory=str(BASE / "admin"), html=True), name="admin")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
