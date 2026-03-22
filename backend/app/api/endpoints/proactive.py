from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.infrastructure.db import get_db
from app.application.proactive_analysis import whatif_simulator, report_generator

router = APIRouter()


class WhatIfScenarioRequest(BaseModel):
    scenario_type: str
    location_id: Optional[str] = None
    drought_level: float = 0.0
    demand_change: float = 0.0
    population_change: float = 0.0
    months: int = 12


class CompareScenariosRequest(BaseModel):
    scenarios: List[dict]


class ReportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_id: Optional[str] = None


@router.post("/simulation/whatif")
async def run_whatif_simulation(
    request: WhatIfScenarioRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await whatif_simulator.simulate_scenario(
            session=db,
            scenario_type=request.scenario_type,
            location_id=request.location_id,
            drought_level=request.drought_level,
            demand_change=request.demand_change,
            population_change=request.population_change,
            months=request.months
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en simulación: {str(e)}"
        )


@router.post("/simulation/compare")
async def compare_scenarios(
    request: CompareScenariosRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await whatif_simulator.compare_scenarios(
            session=db,
            scenarios=request.scenarios
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al comparar escenarios: {str(e)}"
        )


@router.post("/report/executive")
async def generate_executive_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await report_generator.generate_executive_report(
            session=db,
            start_date=request.start_date,
            end_date=request.end_date,
            location_id=request.location_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar informe: {str(e)}"
        )


@router.get("/report/location/{location_id}")
async def generate_location_report(
    location_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await report_generator.generate_location_report(
            session=db,
            location_id=location_id
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar informe de ubicación: {str(e)}"
        )


@router.get("/reports/templates")
async def get_report_templates():
    return {
        "templates": [
            {
                "id": "monthly_summary",
                "name": "Resumen Mensual",
                "description": "Informe mensual de consumos y tendencias"
            },
            {
                "id": "quarterly_analysis",
                "name": "Análisis Trimestral",
                "description": "Análisis detallado del último trimestre"
            },
            {
                "id": "annual_report",
                "name": "Informe Anual",
                "description": "Resumen ejecutivo del año completo"
            },
            {
                "id": "drought应急预案",
                "name": "Plan de Sequía",
                "description": "Informe con recomendaciones para escenarios de sequía"
            }
        ]
    }


@router.post("/simulation/preset/{preset_name}")
async def run_preset_simulation(
    preset_name: str,
    months: int = Query(default=12, ge=1, le=60),
    db: AsyncSession = Depends(get_db)
):
    presets = {
        "severe_drought": {
            "scenario_type": "Sequía Severa",
            "drought_level": 0.5,
            "demand_change": 0.1,
            "population_change": 0.02
        },
        "moderate_drought": {
            "scenario_type": "Sequía Moderada",
            "drought_level": 0.3,
            "demand_change": 0.05,
            "population_change": 0.01
        },
        "population_growth": {
            "scenario_type": "Crecimiento Poblacional",
            "drought_level": 0.1,
            "demand_change": 0.2,
            "population_change": 0.05
        },
        "efficiency_improvement": {
            "scenario_type": "Mejora de Eficiencia",
            "drought_level": 0.1,
            "demand_change": -0.1,
            "population_change": 0.02
        },
        "best_case": {
            "scenario_type": "Mejor Escenario",
            "drought_level": 0.0,
            "demand_change": 0.0,
            "population_change": 0.0
        },
        "worst_case": {
            "scenario_type": "Peor Escenario",
            "drought_level": 0.7,
            "demand_change": 0.3,
            "population_change": 0.1
        }
    }
    
    if preset_name not in presets:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_name}' no encontrado"
        )
    
    preset = presets[preset_name]
    
    try:
        result = await whatif_simulator.simulate_scenario(
            session=db,
            scenario_type=preset["scenario_type"],
            drought_level=preset["drought_level"],
            demand_change=preset["demand_change"],
            population_change=preset["population_change"],
            months=months
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en simulación: {str(e)}"
        )
