from sqlalchemy import Column, DateTime, Float, Integer, String, func


from app.database import Base

class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone_no = Column(String)
    email = Column(String)
    location = Column(String)
    subscription_type = Column(String)
    contract_amount = Column(Float)
    date_entered = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    added_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
