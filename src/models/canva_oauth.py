from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.sql import func

from src.db.session import Base


class CanvaOAuthState(Base):
    __tablename__ = "canva_oauth_states"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    state = Column(Text, nullable=False, unique=True)
    code_verifier = Column(Text, nullable=False)
    redirect_after = Column(Text, nullable=True)
    scopes = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_canva_oauth_states_state", state),
        Index("idx_canva_oauth_states_expires_at", expires_at),
    )


class CanvaOAuthToken(Base):
    __tablename__ = "canva_oauth_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider = Column(Text, nullable=False, server_default="canva")
    # TODO: encrypt tokens at rest with an environment-managed key before production use.
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(Text, nullable=False, server_default="Bearer")
    scopes = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider", name="uq_canva_oauth_tokens_provider"),
        CheckConstraint("provider = 'canva'", name="check_canva_oauth_tokens_provider"),
        Index("idx_canva_oauth_tokens_provider", provider),
    )
