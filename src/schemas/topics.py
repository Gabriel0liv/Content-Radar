from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


TopicType = Literal["topic", "subtopic", "format", "series"]
TopicStatus = Literal["active", "hidden", "archived"]


def normalize_topic_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


class TopicCreate(BaseModel):
    name: str = Field(min_length=1)
    type: TopicType
    parent_id: Optional[int] = None
    status: TopicStatus = "active"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Nome do tópico não pode ser vazio")
        return cleaned


class TopicRead(BaseModel):
    id: int
    name: str
    normalized_name: str
    type: str
    parent_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TopicSignal(BaseModel):
    source: str
    signal: str
    weight: float
    metadata: Optional[Dict[str, Any]] = None


class ContentItemTopicRead(BaseModel):
    id: int
    content_item_id: int
    topic_id: int
    confidence: float
    source: str
    signals_json: List[Dict[str, Any]] = []
    classifier_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
