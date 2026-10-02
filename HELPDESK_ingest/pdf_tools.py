# PDF 도움말을 페이지별 텍스트(JSON)로 추출하고 이미지를 HELPDESK/manual_images 폴더에 저장하는 스킬
import json
from pathlib import Path

import fitz  # PyMuPDF
from zio_ontology import zio_skill

ROOT = Path("/agent_skills/HELPDESK")


@zio_skill
def extract_pdf(pdf_name: str = "RAG_vs_온톨로지_차별점.pdf", render_pages: bool = True, zoom: float = 1.5) -> dict:
    """HELPDESK 폴더의 PDF 를 읽어 페이지별 텍스트는 manual_data/<이름>.json 에, 내장 이미지와 페이지 미리보기는 manual_images/<이름>/ 에 저장하고 요약을 돌려줍니다."""
    pdf = (ROOT / pdf_name).resolve()
    if ROOT not in pdf.parents or pdf.suffix.lower() != ".pdf" or not pdf.exists():
        return {"error": f"HELPDESK 폴더 안의 PDF 만 읽을 수 있습니다: {pdf_name}"}

    stem = pdf.stem
    emb_dir = ROOT / "manual_images" / stem / "embedded"
    pg_dir = ROOT / "manual_images" / stem / "pages"
    emb_dir.mkdir(parents=True, exist_ok=True)
    pg_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf)
    pages = []
    for i, page in enumerate(doc, 1):
        embedded = []
        for j, info in enumerate(page.get_images(full=True), 1):
            pix = fitz.Pixmap(doc, info[0])
            if pix.n - pix.alpha >= 4:  # CMYK 등은 RGB 로 바꿔야 PNG 로 저장된다
                pix = fitz.Pixmap(fitz.csRGB, pix)
            name = f"p{i:03d}_{j:02d}.png"
            pix.save(str(emb_dir / name))
            embedded.append(name)
        preview = None
        if render_pages:
            preview = f"p{i:03d}.png"
            page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(str(pg_dir / preview))
        pages.append({"page": i, "text": page.get_text("text"), "embedded": embedded, "preview": preview})

    out = ROOT / "manual_data" / f"{stem}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"file": pdf.name, "meta": doc.metadata, "pages": pages}, ensure_ascii=False, indent=1), encoding="utf-8")
    return {
        "file": pdf.name, "page_count": len(pages), "data": str(out),
        "chars_per_page": [len(p["text"]) for p in pages],
        "embedded_images": sum(len(p["embedded"]) for p in pages),
    }
