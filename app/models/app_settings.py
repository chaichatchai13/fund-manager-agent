"""App-wide key/value settings persisted in the database."""
from sqlalchemy import Column, String
from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=True)
