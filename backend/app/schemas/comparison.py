from pydantic import BaseModel


class ComparisonRequest(BaseModel):
    workspace_id: str
    left_document_id: str
    right_document_id: str


class ComparisonResponse(BaseModel):
    summary: str
    added_sections: list[str]
    removed_sections: list[str]
    modified_sections: list[str]

