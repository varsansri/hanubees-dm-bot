import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


def gen_id():
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=gen_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free, pro, business
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ig_accounts: Mapped[list["IGAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class IGAccount(Base):
    __tablename__ = "ig_accounts"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String(24), ForeignKey("users.id"), nullable=False)
    ig_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ig_username: Mapped[str] = mapped_column(String(100), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    long_lived_token: Mapped[str] = mapped_column(Text, default="")
    long_lived_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="ig_accounts")
    rules: Mapped[list["AutomationRule"]] = relationship(back_populates="ig_account", cascade="all, delete-orphan")
    dm_logs: Mapped[list["DMLog"]] = relationship(back_populates="ig_account", cascade="all, delete-orphan")


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=gen_id)
    ig_account_id: Mapped[str] = mapped_column(String(24), ForeignKey("ig_accounts.id"), nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    reply_message: Mapped[str] = mapped_column(Text, nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), default="exact")  # exact, contains, starts_with
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    dm_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ig_account: Mapped["IGAccount"] = relationship(back_populates="rules")


class DMLog(Base):
    __tablename__ = "dm_logs"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=gen_id)
    ig_account_id: Mapped[str] = mapped_column(String(24), ForeignKey("ig_accounts.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(24), nullable=True)
    from_username: Mapped[str] = mapped_column(String(100), nullable=False)
    from_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    dm_text: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ig_account: Mapped["IGAccount"] = relationship(back_populates="dm_logs")
