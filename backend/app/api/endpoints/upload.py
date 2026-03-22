import os
import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db import get_db, AsyncSessionLocal
from app.domain.entities.models import FileUpload, FileUploadStatus, Location
from app.domain.services.data_processor import FileProcessor, ExcelProcessingError, sanitize_for_json

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/acuamed_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_file(file: UploadFile) -> tuple[str, int]:
    file_id = uuid.uuid4()
    extension = file.filename.split(".")[-1] if file.filename else "xlsx"
    stored_filename = f"{file_id}.{extension}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)
    
    content = await file.read()
    file_size = len(content)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path, file_size


async def process_file_background(upload_id: str, file_path: str):
    from app.domain.services.data_processor import FileProcessor
    from app.domain.entities.models import Sensor, Consumption, WaterRecord, SensorType
    
    logger.info(f"Iniciando procesamiento de archivo: {upload_id}, path: {file_path}")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FileUpload).where(FileUpload.id == uuid.UUID(upload_id))
        )
        file_upload = result.scalar_one_or_none()
        
        if file_upload:
            file_upload.status = FileUploadStatus.PROCESSING
            await session.commit()
            
            try:
                logger.info(f"Procesando archivo: {file_path}")
                processor = FileProcessor()
                result = processor.process_file(file_path, uuid.UUID(upload_id))
                logger.info(f"Resultado procesamiento: {result}")
                
                total_records = 0
                
                if "ubicaciones" in result and result["ubicaciones"] is not None:
                    ubicaciones = result["ubicaciones"].get("data", [])
                    added_locations = set()
                    for loc_data in ubicaciones:
                        name = str(loc_data.get("INSTALACIÓN", loc_data.get("DESALADORAS", loc_data.get("nombre", loc_data.get("name", "")))))
                        if not name or name == 'nan':
                            name = str(loc_data.get("PROVINCIA", loc_data.get("provincia", f"Location_{uuid.uuid4().hex[:8]}")))
                        if name and name != 'nan' and name not in added_locations:
                            existing = await session.execute(select(Location).where(Location.name == name))
                            if existing.scalar_one_or_none() is None:
                                location = Location(
                                    name=name,
                                    description=str(loc_data.get("INST. COMPUESTAS", loc_data.get("descripcion", ""))),
                                    region=str(loc_data.get("ZONA", loc_data.get("region", ""))),
                                    province=str(loc_data.get("PROVINCIA", loc_data.get("provincia", ""))),
                                    municipality="",
                                    latitude=float(loc_data.get("LATITUD", 0)) if loc_data.get("LATITUD") else None,
                                    longitude=float(loc_data.get("LONGITUD", 0)) if loc_data.get("LONGITUD") else None,
                                )
                                session.add(location)
                                added_locations.add(name)
                    await session.flush()
                    logger.info(f"Insertadas {len(added_locations)} ubicaciones")
                
                consumptions_data = []
                if "consumos" in result and result["consumos"] is not None:
                    consumptions_data.extend(result["consumos"].get("data", []))
                if "sensores" in result and result["sensores"] is not None:
                    consumptions_data.extend(result["sensores"].get("data", []))
                
                if consumptions_data:
                    for cons_data in consumptions_data:
                        # Soporte de nombres originales del Excel Y nombres renombrados por CostesExplotacionCleaner
                        year_raw = cons_data.get("year", cons_data.get("Year", 2023))
                        mes_raw = cons_data.get("month", cons_data.get("mes", cons_data.get("MES", 1)))
                        try:
                            year = int(float(str(year_raw))) if year_raw not in (None, "") else 2023
                            mes = int(float(str(mes_raw))) if mes_raw not in (None, "") else 1
                            if not (1 <= mes <= 12):
                                mes = 1
                        except (ValueError, TypeError):
                            year, mes = 2023, 1

                        subact_id = str(cons_data.get(
                            "subscriber_code",
                            cons_data.get("SUBACTUACION_ID", cons_data.get("subactuacion_id", ""))
                        ))[:50]
                        subactuacion = str(cons_data.get(
                            "consumption_type",
                            cons_data.get("SUBACTUACION", cons_data.get("subactuacion", "Unknown"))
                        ))
                        real_value = cons_data.get(
                            "volume_m3",
                            cons_data.get("REAL", cons_data.get("real", cons_data.get("value", None)))
                        )

                        if real_value is not None and str(real_value) not in ('nan', 'None', ''):
                            try:
                                volume = Decimal(str(real_value))
                            except Exception:
                                continue
                            consumption = Consumption(
                                file_upload_id=uuid.UUID(upload_id),
                                period_start=datetime(year, mes, 1),
                                period_end=datetime(year, mes, 28),
                                volume_m3=volume,
                                consumption_type=subactuacion[:50] if subactuacion else "Unknown",
                                subscriber_code=subact_id,
                                raw_data=sanitize_for_json(cons_data),
                            )
                            session.add(consumption)
                            total_records += 1
                    await session.flush()
                    logger.info(f"Insertados {total_records} consumos")
                
                file_upload.status = FileUploadStatus.COMPLETED
                file_upload.rows_processed = total_records
                file_upload.extra_data = sanitize_for_json(result)
                await session.commit()
                logger.info(f"Archivo procesado exitosamente: {upload_id}, registros: {total_records}")
            except Exception as e:
                logger.error(f"Error procesando archivo {upload_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                file_upload.status = FileUploadStatus.FAILED
                file_upload.error_message = str(e)
                await session.commit()
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsb')):
        raise HTTPException(
            status_code=400, 
            detail="Solo se permiten archivos Excel (.xlsx, .xls, .xlsb)"
        )
    
    try:
        file_path, file_size = await save_file(file)
        
        file_upload = FileUpload(
            filename=file.filename,
            file_size=file_size,
            file_path=file_path,
            status=FileUploadStatus.PENDING
        )
        db.add(file_upload)
        await db.commit()
        await db.refresh(file_upload)
        
        await process_file_background(str(file_upload.id), file_path)
        logger.info(f"Procesamiento completado para upload {file_upload.id}")
        
        result = await db.execute(select(FileUpload).where(FileUpload.id == file_upload.id))
        updated_upload = result.scalar_one()
        
        return {
            "id": str(updated_upload.id),
            "filename": updated_upload.filename,
            "file_size": updated_upload.file_size,
            "status": updated_upload.status.value,
            "rows_processed": updated_upload.rows_processed,
            "message": f"Archivo procesado. Estado: {updated_upload.status.value}"
        }
        
    except Exception as e:
        logger.error(f"Error en upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


@router.get("/uploads")
async def list_uploads(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileUpload)
        .order_by(FileUpload.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    uploads = result.scalars().all()
    
    return {
        "total": len(uploads),
        "uploads": [
            {
                "id": str(u.id),
                "filename": u.filename,
                "file_size": u.file_size,
                "status": u.status.value,
                "rows_processed": u.rows_processed,
                "error_message": u.error_message,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in uploads
        ]
    }


@router.get("/uploads/{upload_id}")
async def get_upload_status(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileUpload).where(FileUpload.id == upload_id)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    
    return {
        "id": str(upload.id),
        "filename": upload.filename,
        "file_size": upload.file_size,
        "status": upload.status.value,
        "rows_processed": upload.rows_processed,
        "error_message": upload.error_message,
        "extra_data": upload.extra_data,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "updated_at": upload.updated_at.isoformat() if upload.updated_at else None
    }


@router.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileUpload).where(FileUpload.id == upload_id)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    
    if os.path.exists(upload.file_path):
        os.remove(upload.file_path)
    
    await db.delete(upload)
    await db.commit()
    
    return {"message": "Upload eliminado correctamente"}


@router.post("/uploads/{upload_id}/retry")
async def retry_upload(
    upload_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileUpload).where(FileUpload.id == upload_id)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    
    if upload.status not in [FileUploadStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede reintentar un upload con estado: {upload.status.value}"
        )
    
    if not os.path.exists(upload.file_path):
        raise HTTPException(
            status_code=400,
            detail="El archivo original no existe en el servidor"
        )
    
    upload.status = FileUploadStatus.PENDING
    upload.error_message = None
    await db.commit()
    
    background_tasks.add_task(process_file_background, str(upload.id), upload.file_path)
    
    return {
        "message": "Reintento de procesamiento iniciado",
        "upload_id": str(upload.id)
    }
