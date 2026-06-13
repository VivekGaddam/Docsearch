from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app import models  # noqa: F401
from app.mcp.server import mcp_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/llm-status")
async def llm_status() -> dict:
    """Debug endpoint — visit http://localhost:8000/llm-status after setting GEMINI_API_KEY."""
    from app.services.llm_service import llm_service

    gemini_key = settings.gemini_api_key or ""
    openai_key = settings.openai_api_key or ""

    return {
        "llm_available": llm_service.is_available(),
        "active_provider": llm_service.active_provider(),
        "model_in_use": llm_service._model,
        # Show first 8 chars so you can verify the key loaded correctly
        "gemini_key_loaded": f"{gemini_key[:8]}..." if gemini_key else "NOT SET",
        "openai_key_loaded": f"{openai_key[:8]}..." if openai_key else "NOT SET",
        "gemini_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "status": "✅ LLM active — AI synthesis enabled" if llm_service.is_available()
                  else "❌ No API key found — using smart fallback mode",
        "fix": None if llm_service.is_available() else (
            "1. Open backend/.env\n"
            "2. Set GEMINI_API_KEY=your_key_here\n"
            "3. Restart the backend server\n"
            "4. Get a free key at https://aistudio.google.com/apikey"
        ),
    }



app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(mcp_router, prefix="/mcp/v1", tags=["MCP"])


