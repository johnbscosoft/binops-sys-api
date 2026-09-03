import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CollectionArea(Base):
    __tablename__ = "collection_areas"
    __table_args__ = (
        UniqueConstraint("company_id", "area_code", name="uq_collection_areas_company_code"),
        UniqueConstraint("company_id", "id", "area_code", name="uq_collection_areas_company_id_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    area_code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String(255), nullable=True)
    service_model = Column(String(20), default="DIRECT", server_default="DIRECT", nullable=False)
    contracting_organisation_id = Column(UUID(as_uuid=True), ForeignKey("contracting_organisations.id"), nullable=True)
    status = Column(String(20), default="Active", server_default="Active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    routes = relationship("CollectionRoute", back_populates="area")


class ContractingOrganisation(Base):
    __tablename__ = "contracting_organisations"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_contracting_organisations_company_name"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    commission_type = Column(String(30), nullable=False)
    commission_rate = Column(Numeric(14, 2), nullable=False)
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CollectionRoute(Base):
    __tablename__ = "collection_routes"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_collection_routes_company_name"),
        UniqueConstraint("company_id", "route_code", name="uq_collection_routes_company_code"),
        ForeignKeyConstraint(
            ["company_id", "area_id", "area_code"],
            ["collection_areas.company_id", "collection_areas.id", "collection_areas.area_code"],
            name="fk_collection_routes_company_area_code",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    area_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    area_code = Column(String(40), nullable=False, index=True)
    route_code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    # Fleet is introduced separately; keep this nullable reference ready for it.
    vehicle_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    status = Column(String(20), default="Active", server_default="Active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    area = relationship("CollectionArea", back_populates="routes")
