from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CanvaOAuthStatusRead(BaseModel):
    configured: bool
    connected: bool
    expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    using_dev_token_fallback: bool
    message: Optional[str] = None


class CanvaOAuthCallbackRead(BaseModel):
    connected: bool
    message: str
    expires_at: Optional[datetime] = None


class CanvaOAuthRefreshRead(BaseModel):
    refreshed: bool
    expires_at: datetime
    message: str
