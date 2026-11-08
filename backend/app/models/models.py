import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, DateTime,
    UniqueConstraint, Index, Text, Enum, Boolean, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.database import Base
from app.engines.base import Severity

class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class FindingStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    clerk_org_id = Column(String, unique=True, nullable=False)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    organization = relationship("Organization", back_populates="users")


class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    default_branch = Column(String, default="main")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    # Módulo E: un repo privado se clona con el token de GitHub de quien lo conectó.
    is_private = Column(Boolean, nullable=False, default=False, server_default="false")
    connected_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    organization = relationship("Organization", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "url", name="uq_organization_url"),
    )


class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ScanStatus, values_callable=lambda e: [x.value for x in e]), nullable=False, default=ScanStatus.QUEUED, server_default='queued')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    commit_sha = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    grade = Column(String(1), nullable=True)
    engine_errors = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    repository = relationship("Repository", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scans_repo_created_desc", "repository_id", created_at.desc()),
    )


class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    fingerprint = Column(String, nullable=False)
    
    engine = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    severity = Column(Enum(Severity, values_callable=lambda e: [x.value for x in e]), nullable=False)
    file_path = Column(String, nullable=False)
    line = Column(Integer, nullable=True)
    snippet = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    cwe = Column(String, nullable=True)
    cve = Column(String, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)

    status = Column(Enum(FindingStatus, values_callable=lambda e: [x.value for x in e]), nullable=False, default=FindingStatus.OPEN, server_default='open')
    ai_is_false_positive = Column(Boolean, nullable=True)
    ai_adjusted_severity = Column(Enum(Severity, values_callable=lambda e: [x.value for x in e]), nullable=True)
    ai_explanation = Column(Text, nullable=True)
    ai_remediation = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")

    __table_args__ = (
        UniqueConstraint("scan_id", "fingerprint", name="uq_scan_fingerprint"),
        Index("ix_findings_scan_id", "scan_id"),
        Index("ix_findings_fingerprint", "fingerprint"),
    )