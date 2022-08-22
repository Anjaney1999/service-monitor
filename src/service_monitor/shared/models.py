from sqlalchemy.ext.declarative import declarative_base
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum

Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    url = Column(String)
    status = Column(String)
    creation_date = Column(DateTime)