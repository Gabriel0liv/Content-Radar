from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

ACTIVE_IDEA_STATUSES = {"idea", "researching", "ready", "archived"}


class IdeaCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    niche: Optional[str] = None
    status: str = "idea"
    priority: int = 0

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O título da ideia não pode ser vazio")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ACTIVE_IDEA_STATUSES:
            raise ValueError("Status de ideia inválido")
        return value


class IdeaUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    niche: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O título da ideia não pode ser vazio")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ACTIVE_IDEA_STATUSES:
            raise ValueError("Status de ideia inválido")
        return value


class IdeaRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    niche: Optional[str] = None
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdeaListResponse(BaseModel):
    items: List[IdeaRead]
    total: int
    limit: int
    offset: int
