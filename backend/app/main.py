import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat as chat_router
from app.routers import codegen as codegen_router
from app.routers import export as export_router
from app.routers import input as input_router
from app.routers import llm_proxy as llm_proxy_router
from app.routers import mockup as mockup_router
from app.routers import session as session_router
from app.routers import spec as spec_router
from app.routers import validate as validate_router
from app.llm.codegen_context import get_workspace_class_map
from app.session import session_store

logger = logging.getLogger(__name__)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(600)
        session_store.cleanup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm workspace class map at startup so the first code generation
    # doesn't block on a full source tree scan.
    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    try:
        class_map = await loop.run_in_executor(None, get_workspace_class_map)
        logger.info("[STARTUP] Workspace class map loaded: %d classes indexed", len(class_map))
    except Exception as e:
        logger.warning("[STARTUP] Workspace class map scan failed (import healing disabled): %s", e)

    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router.router, prefix="/api")
app.include_router(input_router.router, prefix="/api")
app.include_router(spec_router.router, prefix="/api")
app.include_router(chat_router.router, prefix="/api")
app.include_router(validate_router.router, prefix="/api")
app.include_router(export_router.router, prefix="/api")
app.include_router(codegen_router.router, prefix="/api")
app.include_router(mockup_router.router, prefix="/api")
app.include_router(llm_proxy_router.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
