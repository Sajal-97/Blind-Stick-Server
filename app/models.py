from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, text, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL, connect_args


engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class GPSPoint(Base):
    __tablename__ = "gps_points"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), index=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    hdop = Column(Float, nullable=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def init_db():
    Base.metadata.create_all(bind=engine)
