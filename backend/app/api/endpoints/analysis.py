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
            "requires_action": False,
            "context": response.get("chart_context", {})  # Incluir contexto para gráficos
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


@router.get("/aggregations/daily")
async def get_daily_aggregations(
    days: int = 30,
    location_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene agregaciones diarias pre-calculadas para respuestas más rápidas"""
    from sqlalchemy import text
    
    query = """
        SELECT 
            DATE(c.period_start) as date,
            l.region,
            SUM(c.volume_m3) as total_volume,
            COUNT(*) as record_count
        FROM consumptions c
        JOIN locations l ON c.location_id = l.id
        WHERE c.period_start >= CURRENT_DATE - INTERVAL ':days days'
    """
    
    params: dict = {"days": days}
    
    if location_id:
        query += " AND c.location_id = :location_id"
        params["location_id"] = location_id
    
    query += """
        GROUP BY DATE(c.period_start), l.region
        ORDER BY date DESC, l.region
    """
    
    try:
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        columns = result.keys()
        return {
            "aggregations": [dict(zip(columns, row)) for row in rows],
            "period_days": days,
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener agregaciones diarias: {str(e)}"
        )


@router.get("/aggregations/monthly")
async def get_monthly_aggregations(
    months: int = 12,
    location_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene agregaciones mensuales pre-calculadas para respuestas más rápidas"""
    from sqlalchemy import text
    
    query = """
        SELECT 
            EXTRACT(YEAR FROM c.period_start) as year,
            EXTRACT(MONTH FROM c.period_start) as month,
            l.region,
            SUM(c.volume_m3) as total_volume,
            AVG(c.volume_m3) as avg_volume,
            COUNT(*) as record_count
        FROM consumptions c
        JOIN locations l ON c.location_id = l.id
        WHERE c.period_start >= CURRENT_DATE - INTERVAL ':months months'
    """
    
    params: dict = {"months": months}
    
    if location_id:
        query += " AND c.location_id = :location_id"
        params["location_id"] = location_id
    
    query += """
        GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start), l.region
        ORDER BY year DESC, month DESC, l.region
    """
    
    try:
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        columns = result.keys()
        return {
            "aggregations": [dict(zip(columns, row)) for row in rows],
            "period_months": months,
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener agregaciones mensuales: {str(e)}"
        )
