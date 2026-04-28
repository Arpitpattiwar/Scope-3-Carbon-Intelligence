from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RecordAttachment(Base):
    __tablename__ = "record_attachments"

    id           = Column(Integer, primary_key=True, index=True)
    record_id    = Column(Integer, ForeignKey("emission_records.id"), nullable=False)
    uploaded_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename     = Column(String(255), nullable=False)
    file_path    = Column(String(512), nullable=False)   # stored on disk
    file_size    = Column(BigInteger)                    # bytes
    mime_type    = Column(String(100))
    description  = Column(String(255))
    uploaded_at  = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("EmissionRecord", backref="attachments")
    uploader = relationship("User")
