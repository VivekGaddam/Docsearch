from pydantic import BaseModel, EmailStr

from app.schemas.common import TimestampedSchema


class UserResponse(TimestampedSchema):
    email: EmailStr
    full_name: str
    role: str


class UserSummary(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str

    class Config:
        from_attributes = True

