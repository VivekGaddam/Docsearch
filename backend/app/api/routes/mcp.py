from fastapi import APIRouter

from app.schemas.mcp import MCPConnectorResponse
from app.services.mcp_service import list_connectors


router = APIRouter()


@router.get("/connectors", response_model=list[MCPConnectorResponse])
def get_connectors():
    return list_connectors()

