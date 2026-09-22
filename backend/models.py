from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base, engine

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    request_id = Column(String, index=True)
    pnr = Column(String, index=True)
    action_type = Column(String)  # 'auto-execute', 'approve', 'escalate'
    ai_decision = Column(Text)
    human_approver = Column(String, nullable=True) # None if auto-executed
    outcome = Column(Text, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)
