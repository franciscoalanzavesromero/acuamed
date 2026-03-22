from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, DateTime, ForeignKey, Text, 
    Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func
import uuid
import enum

from app.infrastructure.db import Base


class FileUploadStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SensorType(str, enum.Enum):
    CAUDALIMETRO = "caudalimetro"
    PRESION = "presion"
    TEMPERATURA = "temperatura"
    TURBIDEZ = "turbidez"
    PH = "ph"
    CONDUCTIVIDAD = "conductividad"
    NIVEL = "nivel"


class FileUpload(Base):
    __tablename__ = "file_uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[FileUploadStatus] = mapped_column(
        SQLEnum(FileUploadStatus), default=FileUploadStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rows_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    records: Mapped[List["WaterRecord"]] = relationship(
        "WaterRecord", back_populates="file_upload", cascade="all, delete-orphan"
    )
    consumptions: Mapped[List["Consumption"]] = relationship(
        "Consumption", back_populates="file_upload", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_file_uploads_status", "status"),)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Float, nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Float, nullable=True
    )
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sensors: Mapped[List["Sensor"]] = relationship(
        "Sensor", back_populates="location", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_location_name"),
        Index("idx_locations_region", "region"),
    )


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sensor_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(SQLEnum(SensorType), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    installation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_maintenance: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    location: Mapped["Location"] = relationship("Location", back_populates="sensors")
    records: Mapped[List["WaterRecord"]] = relationship(
        "WaterRecord", back_populates="sensor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sensors_type", "sensor_type"),
        Index("idx_sensors_location", "location_id"),
    )


class WaterRecord(Base):
    __tablename__ = "water_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False
    )
    file_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[Decimal] = mapped_column(nullable=False)
    quality_flag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="records")
    file_upload: Mapped["FileUpload"] = relationship(
        "FileUpload", back_populates="records"
    )

    __table_args__ = (
        Index("idx_water_records_timestamp", "timestamp"),
        Index("idx_water_records_sensor", "sensor_id"),
        Index("idx_water_records_anomaly", "is_anomaly"),
        Index(
            "idx_water_records_sensor_timestamp",
            "sensor_id",
            "timestamp",
        ),
    )


class Consumption(Base):
    __tablename__ = "consumptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    volume_m3: Mapped[Decimal] = mapped_column(nullable=False)
    consumption_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subscriber_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_estimated: Mapped[bool] = mapped_column(default=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    file_upload: Mapped["FileUpload"] = relationship(
        "FileUpload", back_populates="consumptions"
    )

    __table_args__ = (
        Index("idx_consumptions_period", "period_start", "period_end"),
        Index("idx_consumptions_location", "location_id"),
    )


class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("water_records.id"), nullable=False
    )
    anomaly_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_by: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_anomaly_records_severity", "severity"),)


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    embedding: Mapped[list] = mapped_column(ARRAY(Float), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_embedding_cache_content", "content_type", "content_id"),)
