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


class NavigationRequest(Base):
    __tablename__ = "navigation_requests"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), index=True, nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    heading = Column(Float, nullable=True)  # compass heading in degrees
    transcript = Column(Text, nullable=True)
    detected_language = Column(String(16), nullable=True)
    translated_text = Column(Text, nullable=True)
    destination_place = Column(String(512), nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)
    audio_path = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def init_db():
    Base.metadata.create_all(bind=engine)
