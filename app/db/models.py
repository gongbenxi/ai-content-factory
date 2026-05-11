"""SQLAlchemy ORM 模型 — 与 schema.sql 对应"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Style(Base):
    __tablename__ = "styles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    fingerprint = Column(JSONB, default={})
    sample_count = Column(Integer, default=0)
    total_generated = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_request = Column(Text)
    style_id = Column(String, ForeignKey("styles.id"))
    target_platform = Column(String, nullable=False)
    config = Column(JSONB, default={})
    topic = Column(JSONB)
    outline = Column(JSONB)
    final_outline = Column(JSONB)
    draft_md = Column(Text)
    final_md = Column(Text)
    images = Column(JSONB, default=[])
    review = Column(JSONB)
    revise_count = Column(Integer, default=0)
    status = Column(String, nullable=False, default="drafting")
    current_agent = Column(String)
    error = Column(Text)
    cost_cents = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    usage_by_agent = Column(JSONB, default={})
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    ts_offset = Column(Float, nullable=False)
    event_type = Column(String, nullable=False)
    data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    content = Column(Text)
    excerpt = Column(Text)
    credibility = Column(Float)
    angle = Column(String)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class StyleSample(Base):
    __tablename__ = "style_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    style_id = Column(String, ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    source_url = Column(String)
    title = Column(String)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ImageCache(Base):
    __tablename__ = "image_cache"

    prompt_hash = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    local_path = Column(String)
    model = Column(String, nullable=False)
    size = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    agent = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cache_read_tokens = Column(Integer, default=0)
    cost_cents = Column(Integer, nullable=False)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
