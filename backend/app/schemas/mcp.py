from pydantic import BaseModel


class MCPConnectorResponse(BaseModel):
    name: str
    status: str
    capabilities: list[str]
    auth_strategy: str

