from fastapi import APIRouter

from app.api.routes import auth, comparisons, documents, mcp, reports, research, search, workspaces


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(comparisons.router, prefix="/comparisons", tags=["comparisons"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])

