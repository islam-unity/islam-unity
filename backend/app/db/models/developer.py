import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class DeveloperAccount(Base):
    __tablename__ = "developer_accounts"

    id = Column(String(64), primary_key=True, index=True, default=lambda: f"dev_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    app_name = Column(String(128), nullable=False, default="پروژه معارفی من")
    description = Column(Text, nullable=True)
    tier = Column(String(32), default="STANDARD", nullable=False)  # FREE, STANDARD, ENTERPRISE
    
    monthly_quota_tokens = Column(Integer, default=5_000_000, nullable=False)
    used_tokens_this_month = Column(Integer, default=0, nullable=False)
    quota_reset_at = Column(DateTime, default=utc_now)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    api_keys = relationship("DeveloperApiKey", back_populates="account", cascade="all, delete-orphan")
    user = relationship("User")


class DeveloperApiKey(Base):
    __tablename__ = "developer_api_keys"

    id = Column(String(64), primary_key=True, index=True, default=lambda: f"key_{uuid.uuid4().hex[:12]}")
    account_id = Column(String(64), ForeignKey("developer_accounts.id", ondelete="CASCADE"), nullable=False)
    key_prefix = Column(String(16), nullable=False)  # e.g., 'ak_live_7a8b'
    key_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 of full key
    label = Column(String(64), default="کلید اصلی", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    account = relationship("DeveloperAccount", back_populates="api_keys")
