# HELPDESK 대시보드(admin/)와 흐름도 이미지를 정적으로 서빙하는 웹 스킬 서버
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
app = FastAPI(title="HELPDESK")


@app.get("/api/health")
def health():
    return {"status": "ok", "skill": "HELPDESK"}


# 라우트를 먼저 등록하고, 루트 마운트는 맨 마지막에 둔다 (/docs, /api 가 가려지지 않도록)
app.mount("/images", StaticFiles(directory=str(BASE / "images")), name="images")
app.mount("/", StaticFiles(directory=str(BASE / "admin"), html=True), name="admin")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
