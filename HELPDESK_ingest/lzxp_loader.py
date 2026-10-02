# LZXP 매뉴얼 PDF(manual_data JSON)를 목차 기준으로 쪼개 HDK 테이블에 적재하는 스킬 (파싱 미리보기 포함)
import hashlib
import json
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from zio_ontology import Zio, zio_skill

from manual_tables import ROOT, TABLES, WHO, _exists, _now

TOC_RE = re.compile(r"^(\d+\.|[가-하]\.|\d+\))\s*(.+?)\s*[·…\.]{3,}\s*\d+\s*$")
PAGE_LINE = re.compile(r"^-\s*\d+\s*-$")
CAPTION = re.compile(r"^『.*』$")
H_SUB = re.compile(r"^\(([0-9]+|[가-하])\)\s*(.*)$")
H_SUB2 = re.compile(r"^([가-하])\)\s+(.*)$")
H_BUL = re.compile(r"^[￭∙•▪■◆●]\s*(.*)$")
H_DASH = re.compile(r"^-\s+(\S.{0,28})$")
H_NOTE = re.compile(r"^※\s*(.*)$")
BRACKET = re.compile(r"\[([^\]\n]{2,40})\]")
FIELD_WORDS = ("용어", "입력", "필드", "항목")

# 문서별 설명 (파일명에서 추정한 것은 Rmk 에 밝힌다)
DOC_META = {
    "LZXP 매뉴얼_GEN": (
        "LZXP ERP 사용자 매뉴얼(GEN). 사용하기 전에·기준정보·영업·개발·구매·자재·품질·생산·무역·경영정보 모듈의 화면별 사용법을 설명한다.",
        "파일명 GEN 은 일반 버전으로 추정. 화면 캡처 이미지는 manual_images/<문서>/embedded/ 에 있고 텍스트에는 없다. 쪼갬·추출은 규칙 기반(anaBy=parser).",
    ),
    "LZXP 매뉴얼_PRJ": (
        "LZXP ERP 사용자 매뉴얼(PRJ). GEN 과 같은 구성에 프로젝트 수주전표·프로젝트 예산관리·기성관리 등 프로젝트 기반 기능이 더해진 판본.",
        "파일명 PRJ 는 프로젝트 버전으로 추정. 목차 쪽번호가 장마다 다시 시작하는 등 불규칙해 제목 검색으로 쪼갰다. 쪼갬·추출은 규칙 기반(anaBy=parser).",
    ),
}

STATE = {"running": False, "stem": None, "phase": "idle", "done": 0, "total": 0, "errors": [], "result": None}


def _norm(s):
    return re.sub(r"\s+", "", s)


def _parse(stem):
    """manual_data JSON 을 목차로 쪼개 조각과 지식 행을 만든다. DB 는 건드리지 않는다."""
    data = json.loads((ROOT / "manual_data" / f"{stem}.json").read_text(encoding="utf-8"))
    pages = data["pages"]

    # 1) 목차 항목과, 목차가 끝나는 지점
    toc, toc_last = [], 0
    for pg in pages:
        for ln in pg["text"].splitlines():
            m = TOC_RE.match(ln.strip())
            if m:
                lab = m.group(1)
                lvl = 1 if lab.endswith(".") and lab[0].isdigit() else 2 if lab.endswith(".") else 3
                toc.append({"lvl": lvl, "label": lab, "title": m.group(2).strip(), "page": pg["page"]})
                toc_last = pg["page"]
    # 2) 본문 줄 목록 (목차가 끝난 쪽에서는 마지막 목차 줄 뒤부터)
    lines = []
    for pg in pages:
        if pg["page"] < toc_last:
            continue
        raw = pg["text"].splitlines()
        if pg["page"] == toc_last:
            last = max((i for i, ln in enumerate(raw) if TOC_RE.match(ln.strip())), default=-1)
            raw = raw[last + 1:]
        for ln in raw:
            s = ln.strip()
            if s:
                lines.append((pg["page"], s))

    # 3) 목차 순서대로 본문에서 제목 줄 위치를 찾는다
    warnings, cursor = [], 0
    for e in toc:
        tgt = _norm(e["label"] + e["title"])
        e["pos"] = None
        for i in range(cursor, len(lines)):
            n1 = _norm(lines[i][1])
            n2 = n1 + (_norm(lines[i + 1][1]) if i + 1 < len(lines) else "")
            if n1.startswith(tgt) or (n2.startswith(tgt) and len(n1) >= len(_norm(e["label"])) + 2):
                e["pos"] = i
                cursor = i + 1
                break
        if e["pos"] is None:
            warnings.append(f"본문에서 못 찾음: {e['label']} {e['title']}")

    # 4) 구조(모듈·그룹)와 잎 판정은 목차 전체 기준
    chap, grp = "", ""
    for k, e in enumerate(toc):
        if e["lvl"] == 1:
            chap, grp = f"{e['label']} {e['title']}", ""
        elif e["lvl"] == 2:
            grp = f"{e['label']} {e['title']}"
        e["chapter"], e["group"] = chap, grp
        nxt = toc[k + 1]["lvl"] if k + 1 < len(toc) else 0
        e["leaf"] = nxt <= e["lvl"]

    located = [e for e in toc if e["pos"] is not None]
    chunks = []
    for k, e in enumerate(located):
        if not e["leaf"]:
            continue
        end = located[k + 1]["pos"] if k + 1 < len(located) else len(lines)
        body = [(p, s) for p, s in lines[e["pos"] + 1:end] if not PAGE_LINE.match(s)]
        p1 = lines[e["pos"]][0]
        p2 = max([p for p, _ in body], default=p1)
        imgs = [f for pg in pages if p1 <= pg["page"] <= p2 for f in pg["embedded"]]
        chunks.append({"entry": e, "p1": p1, "p2": p2, "lines": [s for _, s in body], "images": imgs})
    return data, toc, chunks, warnings


def _extract(title, lines, entry, p1, p2, images):
    """한 조각의 줄들에서 화면·기능·필드·주의사항·연결 행을 뽑는다."""
    lines = [s for s in lines if not CAPTION.match(s)]
    menu_path, menu_idx = [], -1
    for i, s in enumerate(lines[:5]):
        if "메뉴" in s or "클릭" in s:
            toks = BRACKET.findall(s)
            if toks:
                menu_path = [x.strip() for t in toks for x in t.split("-") if x.strip()]
                menu_idx = i
                break

    rows, intro, block, mode = [], [], None, "normal"
    start = menu_idx + 1 if menu_idx >= 0 else 0

    def flush():
        nonlocal block
        if block and block["lines"]:
            text = " ".join(block["lines"]).strip()
            if text:
                rows.append({"kind": block["kind"], "subject": f"{title} > {block['name']}"[:200], "statement": text[:1500],
                             "evidence": text[:160], "relType": "FIELD_OF" if block["kind"] == "필드" else "PART_OF" if block["kind"] == "기능" else "NOTE_OF",
                             "relTarget": title, "attr": None})
        block = None

    i = start
    while i < len(lines):
        s = lines[i]
        m_sub, m_sub2, m_bul, m_dash, m_note = H_SUB.match(s), H_SUB2.match(s), H_BUL.match(s), H_DASH.match(s), H_NOTE.match(s)
        if m_sub or m_sub2:
            flush()
            mm = m_sub or m_sub2
            name, rest = mm.group(2).strip(), []
            if not name and i + 1 < len(lines):  # "(라)" 만 있는 줄 — 다음 줄이 "새로고침 : 설명" 꼴
                i += 1
                nxt = lines[i]
                name, _, tail = nxt.partition(":")
                name = name.strip()[:30]
                rest = [tail.strip()] if tail.strip() else []
            mode = "field" if any(w in name for w in FIELD_WORDS) else "normal"
            block = {"kind": "필드" if mode == "field" else "기능", "name": name or "(이름 없음)", "lines": rest}
        elif m_bul or m_dash:
            flush()
            name = (m_bul or m_dash).group(1).strip()
            block = {"kind": "필드" if mode == "field" else "기능", "name": name[:60] or "(이름 없음)", "lines": []}
        elif m_note:
            flush()
            txt = m_note.group(1).strip()
            if len(txt) <= 20:
                mode = "field" if any(w in txt for w in FIELD_WORDS) else mode
                block = None
            else:
                block = {"kind": "주의사항", "name": "주의", "lines": [txt]}
        elif block is not None:
            block["lines"].append(s)
        else:
            intro.append(s)
        i += 1
    flush()

    # 연결 (메뉴 경로 줄 밖에서 [다른 화면] 을 언급한 문장)
    seen = set()
    for idx, s in enumerate(lines):
        if idx == menu_idx:
            continue
        for ref in BRACKET.findall(s):
            ref = ref.strip()
            if ref not in seen and ref != title and not re.fullmatch(r"[A-Za-z0-9 +]+", ref):
                seen.add(ref)
                rows.append({"kind": "연결", "subject": title[:200], "statement": s[:300], "evidence": s[:160],
                             "relType": "REFERS_TO", "relTarget": ref[:100], "attr": None})

    desc = " ".join(intro).strip() or " ".join(lines[start:start + 3]).strip() or "(설명 텍스트 없음 — 화면 캡처 이미지 중심)"
    screen = {"kind": "화면", "subject": title[:200], "statement": desc[:1200], "evidence": desc[:160], "relType": "BELONGS_TO",
              "relTarget": (entry["chapter"] + " > " + entry["group"])[:200],
              "attr": {"itemNo": entry["label"], "module": entry["chapter"], "group": entry["group"], "menuPath": menu_path,
                       "pages": [p1, p2], "images": images}}
    return [screen] + rows


@zio_skill
def preview_parse(stem: str = "LZXP 매뉴얼_GEN", chunk_no: int = 1) -> dict:
    """DB 에 쓰지 않고 목차 쪼갬·지식 추출 결과를 미리 봅니다. stem 은 manual_data 의 JSON 이름(확장자 제외). chunk_no 번째 조각의 추출 행을 예시로 돌려줍니다."""
    data, toc, chunks, warnings = _parse(stem)
    kinds = Counter()
    sample = None
    for n, c in enumerate(chunks, 1):
        rows = _extract(c["entry"]["title"], c["lines"], c["entry"], c["p1"], c["p2"], c["images"])
        kinds.update(r["kind"] for r in rows)
        if n == chunk_no:
            sample = {"title": c["entry"]["title"], "pages": [c["p1"], c["p2"]], "text_lines": len(c["lines"]), "rows": rows}
    empty = [c["entry"]["title"] for c in chunks if not c["lines"]]
    return {"toc_entries": len(toc), "chunks": len(chunks), "unlocated": warnings[:20], "unlocated_count": len(warnings),
            "kind_counts": dict(kinds), "no_text_chunks": len(empty), "no_text_examples": empty[:5], "sample": sample}


def _load(stem, pdf_name):
    try:
        for name, (disp, desc, cols) in TABLES.items():
            if not _exists(name):
                Zio.entity(name).create_table(columns=cols, display_name=disp, description=desc)
        STATE["phase"] = "parsing"
        data, toc, chunks, warnings = _parse(stem)
        pdf = ROOT / pdf_name
        fhash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        now = _now()
        stamp = {"regUid": WHO, "regDt": now, "modUid": WHO, "modDt": now}
        summary, rmk = DOC_META.get(stem, (stem, ""))
        mods = [f"{e['label']} {e['title']}" for e in toc if e["lvl"] == 1]
        props = {"fileNm": pdf_name, "filePath": f"HELPDESK/{pdf_name}", "fileTy": "PDF", "fileHash": fhash, "title": stem,
                 "docTy": "사용자 매뉴얼", "pageCnt": len(data["pages"]), "charCnt": sum(len(p["text"]) for p in data["pages"]),
                 "imgDir": f"HELPDESK/manual_images/{stem}", "dataPath": f"HELPDESK/manual_data/{stem}.json",
                 "summary": summary + " 모듈: " + ", ".join(mods) + ".", "procSt": "분석완료", "Rmk": rmk}
        existing = Zio.entity("HDK_DocMST").where(fileHash=fhash).fetch().data
        if existing:
            doc_id = existing[0]["docID"]
            Zio.entity("HDK_DocMST").where(docID=doc_id).update({**props, "modUid": WHO, "modDt": now})
        else:
            doc_id = f"DOC{Zio.entity('HDK_DocMST').count() + 1:06d}"
            Zio.entity("HDK_DocMST").create({"docID": doc_id, **props, **stamp})
        STATE["phase"] = "clearing"
        Zio.entity("HDK_KnowMST").where(docID=doc_id).delete()
        Zio.entity("HDK_ChunkMST").where(docID=doc_id).delete()

        jobs, kseq = [], 0
        for n, c in enumerate(chunks, 1):
            e, cid = c["entry"], f"{doc_id}-C{n:04d}"
            content = "\n".join(c["lines"])
            jobs.append(("HDK_ChunkMST", {
                "chunkID": cid, "docID": doc_id, "seqNo": n, "locTy": "PAGE", "pageNo": c["p1"], "pageEndNo": c["p2"],
                "secNo": f"{e['chapter'].split('.')[0]}-{e['group'].split('.')[0]}-{e['label']}", "title": e["title"][:200],
                "content": content, "charCnt": len(content), "imgFile": f"p{c['p1']:03d}.png", "anlSt": "완료", **stamp}))
            for r in _extract(e["title"], c["lines"], e, c["p1"], c["p2"], c["images"]):
                kseq += 1
                jobs.append(("HDK_KnowMST", {
                    "knowID": f"{doc_id}-K{kseq:05d}", "docID": doc_id, "chunkID": cid, "seqNo": kseq, "kind": r["kind"],
                    "subject": r["subject"], "statement": r["statement"], "evidence": r["evidence"], "relType": r["relType"],
                    "relTarget": r["relTarget"], "attrJson": r["attr"], "confidence": 0.7, "anaBy": "parser", **stamp}))
        STATE.update(phase="inserting", total=len(jobs), done=0)

        def put(job):
            try:
                Zio.entity(job[0]).create(job[1])
            except Exception as ex:  # 한 건이 실패해도 나머지는 계속 넣는다
                STATE["errors"].append(f"{job[1].get('chunkID') or job[1].get('knowID')}: {str(ex)[:150]}")
            STATE["done"] += 1

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(put, jobs))
        STATE["result"] = {"docID": doc_id, "chunks": len(chunks), "know": kseq, "unlocated": len(warnings),
                           "counts": {t: Zio.entity(t).count() for t in TABLES}}
        STATE["phase"] = "done"
    except Exception as ex:
        STATE["phase"] = "failed"
        STATE["errors"].append(f"FATAL: {ex!r}"[:300])
    finally:
        STATE["running"] = False


@zio_skill
def start_load(stem: str = "LZXP 매뉴얼_GEN") -> dict:
    """stem 문서를 백그라운드로 HDK 테이블에 적재하기 시작합니다. 진행은 load_status 로 봅니다. 같은 문서를 다시 하면 그 문서의 조각·지식 행을 지우고 다시 넣습니다."""
    if STATE["running"]:
        return {"started": False, "reason": f"이미 {STATE['stem']} 적재 중입니다."}
    pdf_name = stem + ".pdf"
    if not (ROOT / "manual_data" / f"{stem}.json").exists() or not (ROOT / pdf_name).exists():
        return {"started": False, "reason": "manual_data JSON 또는 PDF 가 없습니다. 먼저 extract_pdf 를 돌리십시오."}
    STATE.update(running=True, stem=stem, phase="starting", done=0, total=0, errors=[], result=None)
    threading.Thread(target=_load, args=(stem, pdf_name), daemon=True).start()
    return {"started": True, "stem": stem}


@zio_skill
def load_status() -> dict:
    """start_load 의 진행 상황(단계·진행 건수·오류·결과)을 돌려줍니다."""
    return {**{k: v for k, v in STATE.items() if k != "errors"}, "error_count": len(STATE["errors"]), "errors": STATE["errors"][:10]}
