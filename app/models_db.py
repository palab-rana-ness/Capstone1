from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IncidentDB(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    platform_id = Column(String, nullable=False, index=True)
    pipeline = Column(String, nullable=False, default="")
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    problem = Column(String, nullable=False, default="")
    source = Column(String, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class IncidentPayloadDB(Base):
    __tablename__ = "incident_payloads"

    incident_id = Column(
        String,
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        primary_key=True,
    )
    failure_payload = Column(JSON, nullable=False, default=dict)
    agent_result_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
