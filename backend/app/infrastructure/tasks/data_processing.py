import uuid
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

from celery import Task, chain, group
from celery.result import AsyncResult

from app.celery_app import celery_app
from app.domain.entities.models import (
    FileUpload, FileUploadStatus, Location, Sensor, 
    WaterRecord, Consumption, SensorType
)
from app.domain.services.data_processor import FileProcessor, ExcelProcessingError, SYSTEM_CODE_MAP
import logging
logger = logging.getLogger(__name__)
from app.infrastructure.db import AsyncSessionLocal


class DatabaseTask(Task):
    _db_session = None

    @property
    def db_session(self):
        if self._db_session is None:
            self._db_session = AsyncSessionLocal()
        return self._db_session

    def after_return(self, *args, **kwargs):
        if self._db_session:
            pass


def update_file_status(
    file_upload_id: uuid.UUID,
    status: FileUploadStatus,
    error_message: str = None,
    rows_processed: int = None,
    extra_data: dict = None
):
    import asyncio
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _update():
        async with AsyncSessionLocal() as session:
            stmt = (
                update(FileUpload)
                .where(FileUpload.id == file_upload_id)
                .values(
                    status=status,
                    error_message=error_message,
                    rows_processed=rows_processed,
                    extra_data=extra_data
                )
            )
            await session.execute(stmt)
            await session.commit()
    
    asyncio.run(_update())


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.process_excel_file")
def process_excel_file(self: DatabaseTask, file_upload_id: str, file_path: str) -> Dict[str, Any]:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert
    
    file_id = uuid.UUID(file_upload_id)
    processor = FileProcessor()
    
    try:
        update_file_status(file_id, FileUploadStatus.PROCESSING)
        
        result = processor.process_file(file_path, file_id)
        
        total_rows = 0
        
        async def _save_data():
            nonlocal total_rows
            async with AsyncSessionLocal() as session:
                locations_map = {}
                if "ubicaciones" in result and result["ubicaciones"]["data"]:
                    for loc_data in result["ubicaciones"]["data"]:
                        # Manejar tanto el formato antiguo como el nuevo
                        name = loc_data.get("nombre", loc_data.get("name", "unknown"))
                        description = loc_data.get("descripcion", loc_data.get("description", ""))
                        latitude = loc_data.get("latitud", loc_data.get("latitude"))
                        longitude = loc_data.get("longitud", loc_data.get("longitude"))
                        region = loc_data.get("region", "Comunidad Valenciana")
                        province = loc_data.get("provincia", loc_data.get("province", ""))
                        municipality = loc_data.get("municipio", loc_data.get("municipality", ""))
                        
                        location = Location(
                            name=name,
                            description=description,
                            latitude=latitude,
                            longitude=longitude,
                            region=region,
                            province=province,
                            municipality=municipality
                        )
                        session.add(location)
                        await session.flush()
                        
                        # Guardar mapeo por nombre
                        locations_map[name.lower()] = location.id
                        
                        # También guardar mapeo por código de ubicación si existe
                        location_code = loc_data.get("location_code", "").lower()
                        if location_code:
                            locations_map[location_code] = location.id
                        
                        # Añadir mapeo inverso: códigos NAV_DIM1_ID → location.id
                        for nav_code, system_name in SYSTEM_CODE_MAP.items():
                            if system_name.lower() == name.lower():
                                locations_map[nav_code] = location.id
                    
                    await session.commit()
                
                sensors_map = {}
                if "sensores" in result and result["sensores"]["data"]:
                    for sensor_data in result["sensores"]["data"]:
                        sensor_code = sensor_data.get("codigo_sensor", "")
                        location_name = sensor_data.get("ubicacion", "").lower()
                        location_id = locations_map.get(location_name)
                        
                        if not location_id:
                            existing_loc = await session.execute(
                                select(Location).limit(1)
                            )
                            loc = existing_loc.scalar_one_or_none()
                            location_id = loc.id if loc else None
                        
                        sensor = Sensor(
                            sensor_code=sensor_code,
                            name=sensor_data.get("nombre", sensor_code),
                            sensor_type=SensorType(sensor_data.get("tipo", "caudalimetro")),
                            location_id=location_id,
                            unit=sensor_data.get("unidad", "m3/h"),
                            installation_date=sensor_data.get("fecha_instalacion")
                        )
                        session.add(sensor)
                        await session.flush()
                        sensors_map[sensor_code.lower()] = sensor.id
                    
                    await session.commit()
                
                if "consumos" in result and result["consumos"]["data"]:
                    consumptions = []
                    import pandas as pd
                    def clean_nans(obj):
                        import math
                        import numpy as np
                        import datetime as dt
                        if isinstance(obj, dict):
                            return {k: clean_nans(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [clean_nans(v) for v in obj]
                        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                            return None
                        elif isinstance(obj, (np.floating, np.integer)):
                            if np.isnan(obj):
                                return None
                            return obj.item()
                        elif pd.isna(obj):
                            return None
                        elif isinstance(obj, pd.Timestamp):
                            return obj.to_pydatetime().isoformat()
                        elif isinstance(obj, (dt.datetime, dt.date, dt.time)):
                            return obj.isoformat()
                        else:
                            return obj
                    for cons_data in result["consumos"]["data"]:
                        cons_data = clean_nans(cons_data)
                        location_id = None
                        
                        # Prioridad 1: buscar por location_name (generado por SYSTEM_CODE_MAP)
                        location_name = cons_data.get("location_name", "")
                        if location_name:
                            location_id = locations_map.get(location_name.lower())
                        
                        # Prioridad 2: buscar por código NAV_DIM1_ID directamente
                        if not location_id:
                            location_code = cons_data.get("location_code", "").lower()
                            location_id = locations_map.get(location_code)
                        
                        # Prioridad 3: buscar por substring en nombres de ubicaciones
                        if not location_id and location_name:
                            base_name = location_name.lower()
                            for prefix in ["(d+d)", "(d)", "(d+ d)"]:
                                base_name = base_name.replace(prefix, "")
                            base_name = base_name.strip()
                            for loc_key, loc_id in locations_map.items():
                                if base_name and base_name in loc_key.lower():
                                    location_id = loc_id
                                    break
                        
                        # Loggear warning si no se encuentra ubicación, NO usar fallback silencioso
                        if not location_id:
                            logger.warning(
                                f"Sin ubicación para: name={location_name}, "
                                f"code={cons_data.get('location_code', '')}. "
                                f"Registro ignorado."
                            )
                            continue
                        
                        # Obtener fechas (formato nuevo o antiguo)
                        period_start = cons_data.get("period_start")
                        if not period_start:
                            period_start = cons_data.get("fecha_inicio", datetime.now())
                        # Convertir string a datetime si es necesario
                        if isinstance(period_start, str):
                            period_start = datetime.fromisoformat(period_start.replace('T', ' ').replace('Z', ''))
                        
                        period_end = cons_data.get("period_end")
                        if not period_end:
                            period_end = cons_data.get("fecha_fin", datetime.now())
                        # Convertir string a datetime si es necesario
                        if isinstance(period_end, str):
                            period_end = datetime.fromisoformat(period_end.replace('T', ' ').replace('Z', ''))
                        
                        # Obtener volumen
                        volume_m3 = cons_data.get("volume_m3", 0)
                        if not volume_m3:
                            volume_m3 = cons_data.get("volumen_m3", 0)
                        
                        # Obtener tipo de consumo
                        consumption_type = cons_data.get("consumption_type", "")
                        if not consumption_type or consumption_type == "unknown":
                            consumption_type = cons_data.get("subactuacion", "")
                        if not consumption_type or consumption_type == "unknown":
                            consumption_type = cons_data.get("tipo_consumo", "explotacion")
                        # Limpiar el tipo de consumo
                        if consumption_type:
                            consumption_type = consumption_type.lower().strip()
                        
                        # Obtener código de suscriptor
                        subscriber_code = cons_data.get("subscriber_code", "")
                        if not subscriber_code:
                            subscriber_code = cons_data.get("codigo_suscriptor", "")
                        
                        consumption = Consumption(
                            file_upload_id=file_id,
                            location_id=location_id,
                            period_start=period_start,
                            period_end=period_end,
                            volume_m3=Decimal(str(volume_m3)),
                            consumption_type=consumption_type,
                            subscriber_code=subscriber_code,
                            is_estimated=cons_data.get("is_estimated", cons_data.get("es_estimado", False)),
                            raw_data=cons_data
                        )
                        consumptions.append(consumption)
                        total_rows += 1
                    
                    session.add_all(consumptions)
                    await session.commit()
                
                if "sensores" in result and result["sensores"]["data"]:
                    water_records = []
                    for rec_data in result["sensores"]["data"]:
                        sensor_code = rec_data.get("codigo_sensor", "").lower()
                        sensor_id = sensors_map.get(sensor_code)
                        
                        if sensor_id and rec_data.get("timestamp"):
                            record = WaterRecord(
                                sensor_id=sensor_id,
                                file_upload_id=file_id,
                                timestamp=rec_data.get("timestamp"),
                                value=Decimal(str(rec_data.get("value", 0))),
                                quality_flag=rec_data.get("calidad"),
                                raw_data=rec_data
                            )
                            water_records.append(record)
                            total_rows += 1
                    
                    if water_records:
                        session.add_all(water_records)
                        await session.commit()
                
                return total_rows
        
        import asyncio
        total_rows = asyncio.run(_save_data())
        
        update_file_status(
            file_id,
            FileUploadStatus.COMPLETED,
            rows_processed=total_rows,
            extra_data=result.get("metadata")
        )
        
        return {
            "status": "success",
            "file_upload_id": str(file_id),
            "rows_processed": total_rows,
            "metadata": result.get("metadata")
        }
        
    except ExcelProcessingError as e:
        update_file_status(
            file_id,
            FileUploadStatus.FAILED,
            error_message=str(e)
        )
        raise
        
    except Exception as e:
        update_file_status(
            file_id,
            FileUploadStatus.FAILED,
            error_message=f"Error inesperado: {str(e)}"
        )
        raise


@celery_app.task(bind=True, name="tasks.validate_file")
def validate_file(self: DatabaseTask, file_path: str) -> Dict[str, Any]:
    from app.domain.services.data_processor import ExcelParser
    
    parser = ExcelParser(file_path)
    valid, message = parser.parse_all()
    
    return {
        "valid": valid,
        "message": message,
        "sheets_found": list(valid.keys()) if isinstance(valid, dict) else []
    }


@celery_app.task(name="tasks.cleanup_temp_file")
def cleanup_temp_file(file_path: str) -> Dict[str, Any]:
    import os
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"status": "cleaned", "path": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.process_file_chain")
def process_file_chain(file_upload_id: str, file_path: str):
    return chain(
        validate_file.s(file_path),
        process_excel_file.s(file_upload_id, file_path),
        cleanup_temp_file.s(file_path)
    )()
