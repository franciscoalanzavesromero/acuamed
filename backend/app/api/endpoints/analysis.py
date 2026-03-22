from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.infrastructure.db import get_db
from app.application.llm_client import llm_service
from app.application.analytics_chain import analytics_chain

router = APIRouter()


class NaturalLanguageQuery(BaseModel):
    question: str


class ConsumptionSummaryRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_id: Optional[str] = None


class AnomalyDetectionRequest(BaseModel):
    threshold_z: float = 2.5


@router.get("/models/status")
async def check_llm_status():
    models = await llm_service.get_models()
    is_loaded = await llm_service.is_model_loaded()
    
    return {
        "lm_studio_connected": "error" not in models,
        "model_loaded": is_loaded,
        "models": models.get("data", []) if "data" in models else [],
        "error": models.get("error")
    }


@router.post("/query")
async def query_natural_language(
    query: NaturalLanguageQuery,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await analytics_chain.query_natural_language(
            question=query.question,
            session=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la consulta: {str(e)}"
        )


@router.post("/consumption/summary")
async def get_consumption_summary(
    request: ConsumptionSummaryRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await analytics_chain.get_consumption_summary(
            session=db,
            start_date=request.start_date,
            end_date=request.end_date,
            location_id=request.location_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener resumen de consumos: {str(e)}"
        )


@router.post("/anomalies/detect")
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        anomalies = await analytics_chain.detect_consumption_anomalies(
            session=db,
            threshold_z=request.threshold_z
        )
        return {
            "count": len(anomalies),
            "anomalies": anomalies
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al detectar anomalías: {str(e)}"
        )


@router.post("/chat")
async def chat_with_data(
    message: NaturalLanguageQuery,
    db: AsyncSession = Depends(get_db)
):
    try:
        is_loaded = await llm_service.is_model_loaded()
        
        if not is_loaded:
            return {
                "response": "El modelo de IA no está cargado en LM Studio. Por favor, carga el modelo 'ministral-3-8b-instruct-2512' desde la interfaz de LM Studio.",
                "requires_action": True,
                "action": "load_model"
            }
        
        response = await analytics_chain.query_natural_language(
            question=message.question,
            session=db
        )
        
        if response is None:
            raise HTTPException(
                status_code=500,
                detail="La respuesta de analytics_chain.query_natural_language es None"
            )
        
        result_data = response.get("result", [])
        if result_data is None:
            result_data = []
        
        return {
            "question": message.question,
            "response": response.get("explanation", ""),
            "data": result_data[:5],
            "sql": response.get("sql_generated", ""),
            "requires_action": False
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en chat: {str(e)}"
        )


@router.get("/schema")
async def get_database_schema(db: AsyncSession = Depends(get_db)):
    from app.application.analytics_chain import SQLGenerator
    
    sql_gen = SQLGenerator(llm_service)
    schema = await sql_gen.get_schema_description(db)
    
    return {"schema": schema}
