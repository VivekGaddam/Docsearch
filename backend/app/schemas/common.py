from datetime import datetime

from pydantic import BaseModel


class TimestampedSchema(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

