"""
FastAPI Backend — main application entry point.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.api import router as api_router
from backend.websocket.handler import router as ws_router
from shared.config import OUTPUTS_DIR
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _prefetch_bgm():
    """Pre-download all BGM tracks in background at startup so pipeline doesn't wait."""
    try:
        from mcp.tools.audio_tools.bgm_tool import BGM_SOURCES, _download_bgm_sync, _DOWNLOAD_TIMEOUT
        from shared.config import BGM_DIR
        from pathlib import Path
        import asyncio

        loop = asyncio.get_event_loop()
        missing = [s for s in BGM_SOURCES if not (Path(BGM_DIR) / f"{s}.mp3").exists()]

        if not missing:
            logger.info("[BGM] All tracks already cached.")
            return

        logger.info(f"[BGM] Pre-fetching {len(missing)} missing track(s): {missing}")
        for stem in missing:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, _download_bgm_sync, stem, str(BGM_DIR)),
                    timeout=_DOWNLOAD_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"[BGM] Pre-fetch timed out for '{stem}'")
            except Exception as e:
                logger.warning(f"[BGM] Pre-fetch failed for '{stem}': {e}")
        logger.info("[BGM] Pre-fetch complete.")
    except Exception as e:
        logger.warning(f"[BGM] Pre-fetch startup task failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kick off BGM pre-download without blocking startup
    asyncio.create_task(_prefetch_bgm())
    yield


app = FastAPI(title="AI Video Generator", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure output dir exists before mounting
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
