from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.models import (
    Location, Sensor, WaterRecord, Consumption,
    FileUpload, AnomalyRecord, FileUploadStatus
)
from app.domain.entities.schemas import (
    LocationCreate, LocationUpdate,
    SensorCreate, SensorUpdate,
    WaterRecordCreate,
    ConsumptionCreate,
)


class LocationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: LocationCreate) -> Location:
        location = Location(**data.model_dump())
        self.session.add(location)
        await self.session.commit()
        await self.session.refresh(location)
        return location

    async def get_by_id(self, location_id: UUID) -> Optional[Location]:
        result = await self.session.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Location]:
        result = await self.session.execute(
            select(Location).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, location_id: UUID, data: LocationUpdate) -> Optional[Location]:
        location = await self.get_by_id(location_id)
        if not location:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(location, key, value)
        await self.session.commit()
        await self.session.refresh(location)
        return location

    async def delete(self, location_id: UUID) -> bool:
        location = await self.get_by_id(location_id)
        if not location:
            return False
        await self.session.delete(location)
        await self.session.commit()
        return True


class SensorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: SensorCreate) -> Sensor:
        sensor = Sensor(**data.model_dump())
        self.session.add(sensor)
        await self.session.commit()
        await self.session.refresh(sensor)
        return sensor

    async def get_by_id(self, sensor_id: UUID) -> Optional[Sensor]:
        result = await self.session.execute(
            select(Sensor).options(selectinload(Sensor.location)).where(Sensor.id == sensor_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, sensor_code: str) -> Optional[Sensor]:
        result = await self.session.execute(
            select(Sensor).where(Sensor.sensor_code == sensor_code)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100, location_id: Optional[UUID] = None) -> List[Sensor]:
        query = select(Sensor)
        if location_id:
            query = query.where(Sensor.location_id == location_id)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, sensor_id: UUID, data: SensorUpdate) -> Optional[Sensor]:
        sensor = await self.get_by_id(sensor_id)
        if not sensor:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(sensor, key, value)
        await self.session.commit()
        await self.session.refresh(sensor)
        return sensor


class WaterRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: WaterRecordCreate) -> WaterRecord:
        record = WaterRecord(**data.model_dump())
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def create_batch(self, records: List[WaterRecordCreate]) -> int:
        water_records = [WaterRecord(**r.model_dump()) for r in records]
        self.session.add_all(water_records)
        await self.session.commit()
        return len(water_records)

    async def get_by_id(self, record_id: UUID) -> Optional[WaterRecord]:
        result = await self.session.execute(
            select(WaterRecord).where(WaterRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        sensor_ids: Optional[List[UUID]] = None,
        skip: int = 0,
        limit: int = 1000
    ) -> List[WaterRecord]:
        query = select(WaterRecord).where(
            and_(
                WaterRecord.timestamp >= start_date,
                WaterRecord.timestamp <= end_date
            )
        )
        if sensor_ids:
            query = query.where(WaterRecord.sensor_id.in_(sensor_ids))
        query = query.order_by(WaterRecord.timestamp.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_anomalies(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WaterRecord]:
        query = select(WaterRecord).where(WaterRecord.is_anomaly == True)
        if start_date:
            query = query.where(WaterRecord.timestamp >= start_date)
        if end_date:
            query = query.where(WaterRecord.timestamp <= end_date)
        query = query.order_by(WaterRecord.timestamp.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ConsumptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: ConsumptionCreate) -> Consumption:
        consumption = Consumption(**data.model_dump())
        self.session.add(consumption)
        await self.session.commit()
        await self.session.refresh(consumption)
        return consumption

    async def create_batch(self, consumptions: List[ConsumptionCreate]) -> int:
        records = [Consumption(**c.model_dump()) for c in consumptions]
        self.session.add_all(records)
        await self.session.commit()
        return len(records)

    async def get_by_location(
        self,
        location_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Consumption]:
        query = select(Consumption).where(Consumption.location_id == location_id)
        if start_date:
            query = query.where(Consumption.period_start >= start_date)
        if end_date:
            query = query.where(Consumption.period_end <= end_date)
        query = query.order_by(Consumption.period_start.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_aggregated_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day"
    ) -> List[dict]:
        if group_by == "day":
            date_trunc = func.date_trunc("day", Consumption.period_start)
        elif group_by == "month":
            date_trunc = func.date_trunc("month", Consumption.period_start)
        else:
            date_trunc = func.date_trunc("week", Consumption.period_start)

        result = await self.session.execute(
            select(
                date_trunc.label("period"),
                func.sum(Consumption.volume_m3).label("total_volume"),
                func.count(Consumption.id).label("record_count")
            )
            .where(
                and_(
                    Consumption.period_start >= start_date,
                    Consumption.period_end <= end_date
                )
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        return [{"period": str(row.period), "total_volume": float(row.total_volume), "record_count": row.record_count} for row in result.all()]


class FileUploadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, filename: str, file_size: int, file_path: str) -> FileUpload:
        upload = FileUpload(
            filename=filename,
            file_size=file_size,
            file_path=file_path,
            status=FileUploadStatus.PENDING
        )
        self.session.add(upload)
        await self.session.commit()
        await self.session.refresh(upload)
        return upload

    async def get_by_id(self, upload_id: UUID) -> Optional[FileUpload]:
        result = await self.session.execute(
            select(FileUpload).where(FileUpload.id == upload_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        upload_id: UUID,
        status: FileUploadStatus,
        error_message: Optional[str] = None,
        rows_processed: Optional[int] = None
    ) -> Optional[FileUpload]:
        upload = await self.get_by_id(upload_id)
        if not upload:
            return None
        upload.status = status
        if error_message:
            upload.error_message = error_message
        if rows_processed is not None:
            upload.rows_processed = rows_processed
        await self.session.commit()
        await self.session.refresh(upload)
        return upload

    async def get_recent(self, limit: int = 10) -> List[FileUpload]:
        result = await self.session.execute(
            select(FileUpload)
            .order_by(FileUpload.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
