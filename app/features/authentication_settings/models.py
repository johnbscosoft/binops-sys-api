import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AuthenticationSettings(Base):
    __tablename__ = "authentication_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    otp_enabled = Column(Boolean, default=True, nullable=False)
    email_otp_enabled = Column(Boolean, default=True, nullable=False)
    sms_otp_enabled = Column(Boolean, default=True, nullable=False)
    google_location_enabled = Column(Boolean, default=False, nullable=False)
    location_provider = Column(String(20), default="MANUAL", server_default="MANUAL", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company = relationship("Company", back_populates="authentication_settings")
