"""
FastAPI Backend — main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.api import router as api_router
from backend.websocket.handler import router as ws_router
from shared.config import OUTPUTS_DIR
import os

app = FastAPI(title="AI Video Generator", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs directory for serving generated files
outputs_path = str(OUTPUTS_DIR)
if os.path.exists(outputs_path):
    app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

# Routes
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Video Generator API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
