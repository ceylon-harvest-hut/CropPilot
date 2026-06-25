from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.infrastructure.repositories.db import (
    Base,
    CROP_BOTANICAL_NAME_MAX_LENGTH,
    CROP_NAME_MAX_LENGTH,
    KNOWLEDGE_SOURCE_ORIGIN_URL_MAX_LENGTH,
    KNOWLEDGE_SOURCE_STATUS_MAX_LENGTH,
    KNOWLEDGE_SOURCE_STATUS_PENDING,
)


class CropKnowledgeSource(Base):
    __tablename__ = "crop_knowledge_sources"

    crop_id = Column(
        Integer,
        ForeignKey("crops.id", ondelete="CASCADE"),
        primary_key=True,
    )
    knowledge_source_id = Column(
        Integer,
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        primary_key=True,
    )

    crop = relationship("Crop", back_populates="crop_links")
    knowledge_source = relationship("KnowledgeSource", back_populates="crop_links")


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(CROP_NAME_MAX_LENGTH), unique=True, nullable=False)
    botanical_name = Column(String(CROP_BOTANICAL_NAME_MAX_LENGTH), nullable=True)

    crop_links = relationship(
        "CropKnowledgeSource",
        back_populates="crop",
        cascade="all, delete-orphan",
    )


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_url = Column(String(KNOWLEDGE_SOURCE_ORIGIN_URL_MAX_LENGTH), unique=True, nullable=False)
    status = Column(
        String(KNOWLEDGE_SOURCE_STATUS_MAX_LENGTH),
        default=KNOWLEDGE_SOURCE_STATUS_PENDING,
        nullable=False,
    )

    crop_links = relationship(
        "CropKnowledgeSource",
        back_populates="knowledge_source",
        cascade="all, delete-orphan",
    )
