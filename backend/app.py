"""
FastAPI Backend — main application entry point.
KMP_DUPLICATE_LIB_OK must be set BEFORE any torch/cv2 imports (SadTalker conflict).
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.api import router as api_router
from backend.websocket.handler import router as ws_router
from shared.config import OUTPUTS_DIR

app = FastAPI(title="AI Video Generator", version="1.0.0")

# CORS — allow Vite dev server (3000) and any other origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure output dir exists before mounting (avoids crash on first run)
outputs_path = str(OUTPUTS_DIR)
os.makedirs(outputs_path, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

# Routes
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Video Generator API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
