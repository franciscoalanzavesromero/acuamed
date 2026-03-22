from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    region: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    municipality: Optional[str] = Field(None, max_length=100)


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    region: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=100)
    municipality: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime


class SensorBase(BaseModel):
    sensor_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    sensor_type: str
    location_id: UUID
    unit: str = Field(..., min_length=1, max_length=20)
    installation_date: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    metadata: Optional[dict] = None


class SensorCreate(SensorBase):
    @field_validator("sensor_type")
    @classmethod
    def validate_sensor_type(cls, v):
        valid_types = ["caudalimetro", "presion", "temperatura", "turbidez", "ph", "conductividad", "nivel"]
        if v.lower() not in valid_types:
            raise ValueError(f"Tipo de sensor debe ser uno de: {valid_types}")
        return v.lower()


class SensorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    last_maintenance: Optional[datetime] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class SensorResponse(SensorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    location: Optional[LocationResponse] = None


class WaterRecordBase(BaseModel):
    sensor_id: UUID
    timestamp: datetime
    value: float
    quality_flag: Optional[str] = None
    is_anomaly: bool = False
    anomaly_score: Optional[float] = Field(None, ge=0, le=1)
    anomaly_reason: Optional[str] = None
    raw_data: Optional[dict] = None


class WaterRecordCreate(WaterRecordBase):
    pass


class WaterRecordResponse(WaterRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_upload_id: UUID
    created_at: datetime


class WaterRecordBatch(BaseModel):
    records: List[WaterRecordCreate]


class ConsumptionBase(BaseModel):
    location_id: Optional[UUID] = None
    period_start: datetime
    period_end: datetime
    volume_m3: float = Field(..., ge=0)
    consumption_type: str = Field(..., min_length=1, max_length=50)
    subscriber_code: Optional[str] = Field(None, max_length=50)
    is_estimated: bool = False
    raw_data: Optional[dict] = None


class ConsumptionCreate(ConsumptionBase):
    pass


class ConsumptionResponse(ConsumptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_upload_id: UUID
    created_at: datetime


class ConsumptionBatch(BaseModel):
    consumptions: List[ConsumptionCreate]


class FileUploadBase(BaseModel):
    filename: str
    file_size: int = Field(..., ge=0)


class FileUploadResponse(FileUploadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    error_message: Optional[str] = None
    rows_processed: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class FileUploadCreate(FileUploadBase):
    file_path: str


class AnomalyRecordBase(BaseModel):
    record_id: UUID
    anomaly_type: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    description: str
    llm_analysis: Optional[str] = None


class AnomalyRecordCreate(AnomalyRecordBase):
    pass


class AnomalyRecordResponse(AnomalyRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detected_by: str
    created_at: datetime


class AnalyticsQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    sensor_ids: Optional[List[UUID]] = None
    location_ids: Optional[List[UUID]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AnalyticsResponse(BaseModel):
    query: str
    sql_generated: Optional[str] = None
    result: Any
    visualization_type: Optional[str] = None
    llm_explanation: Optional[str] = None


class WhatIfScenario(BaseModel):
    scenario_name: str = Field(..., min_length=1, max_length=255)
    location_id: Optional[UUID] = None
    drought_level: float = Field(0, ge=0, le=1)
    demand_increase: float = Field(0, ge=-0.5, le=1)
    population_change: float = Field(0, ge=-0.5, le=1)
    projected_months: int = Field(12, ge=1, le=60)


class WhatIfResult(BaseModel):
    scenario_name: str
    projections: List[dict]
    summary: str
    recommendations: List[str]
