from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.llm_client import llm_service
from app.domain.entities.models import Consumption, Location


SYSTEM_PROMPT_REPORT = """Eres un analista experto en gestión hídrica para ACUAMED. 
Genera informes ejecutivos profesionales en español, claros y accionables.
Incluye métricas clave, tendencias y recomendaciones."""


class WhatIfSimulator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def simulate_scenario(
        self,
        session: AsyncSession,
        scenario_type: str,
        location_id: Optional[str] = None,
        drought_level: float = 0.0,
        demand_change: float = 0.0,
        population_change: float = 0.0,
        months: int = 12
    ) -> Dict[str, Any]:
        query = select(
            func.avg(Consumption.volume_m3).label("avg_volume"),
            func.min(Consumption.period_start).label("first_period"),
            func.max(Consumption.period_end).label("last_period"),
        )
        
        if location_id:
            query = query.where(Consumption.location_id == location_id)
        
        result = await session.execute(query)
        row = result.one()
        
        base_volume = float(row.avg_volume) if row.avg_volume else 1000000
        
        projections = self._generate_projections(
            base_volume=base_volume,
            drought_level=drought_level,
            demand_change=demand_change,
            population_change=population_change,
            months=months,
            scenario_type=scenario_type
        )
        
        summary = await self._generate_summary(
            projections=projections,
            scenario_type=scenario_type,
            drought_level=drought_level,
            demand_change=demand_change,
            population_change=population_change
        )
        
        return {
            "scenario_type": scenario_type,
            "base_volume_m3": base_volume,
            "drought_level": drought_level,
            "demand_change": demand_change,
            "population_change": population_change,
            "projections": projections,
            "summary": summary["text"],
            "recommendations": summary["recommendations"]
        }

    def _generate_projections(
        self,
        base_volume: float,
        drought_level: float,
        demand_change: float,
        population_change: float,
        months: int,
        scenario_type: str
    ) -> List[Dict[str, Any]]:
        projections = []
        current_date = datetime.now()
        
        seasonal_factors = {
            1: 1.1, 2: 1.0, 3: 0.9, 4: 0.85,
            5: 0.8, 6: 0.75, 7: 0.7, 8: 0.7,
            9: 0.8, 10: 0.9, 11: 1.0, 12: 1.1
        }
        
        cumulative_demand = 1.0 + demand_change
        cumulative_pop = 1.0 + population_change
        
        for i in range(months):
            month = (current_date.month + i) % 12 + 1
            seasonal = seasonal_factors.get(month, 1.0)
            
            availability_factor = 1.0 - (drought_level * 0.3)
            
            projected_volume = (
                base_volume 
                * seasonal 
                * cumulative_demand 
                * cumulative_pop 
                * availability_factor
            )
            
            difference_from_base = projected_volume - base_volume
            percent_change = (difference_from_base / base_volume) * 100
            
            projections.append({
                "month": month,
                "month_name": self._get_month_name(month),
                "year": current_date.year + (current_date.month + i - 1) // 12,
                "projected_volume_m3": round(projected_volume, 2),
                "difference_m3": round(difference_from_base, 2),
                "percent_change": round(percent_change, 2),
                "seasonal_factor": seasonal,
                "status": self._get_status_label(percent_change)
            })
            
            cumulative_demand *= (1 + demand_change / months)
            cumulative_pop *= (1 + population_change / months)
        
        return projections

    def _get_month_name(self, month: int) -> str:
        months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        return months.get(month, "")

    def _get_status_label(self, percent_change: float) -> str:
        if percent_change > 10:
            return "critical"
        elif percent_change > 5:
            return "warning"
        elif percent_change < -10:
            return "shortage"
        elif percent_change < -5:
            return "low"
        return "normal"

    async def _generate_summary(
        self,
        projections: List[Dict[str, Any]],
        scenario_type: str,
        drought_level: float,
        demand_change: float,
        population_change: float
    ) -> Dict[str, Any]:
        avg_projected = sum(p["projected_volume_m3"] for p in projections) / len(projections)
        total_projected = sum(p["projected_volume_m3"] for p in projections)
        max_projected = max(p["projected_volume_m3"] for p in projections)
        min_projected = min(p["projected_volume_m3"] for p in projections)
        
        critical_months = [p for p in projections if p["status"] == "critical"]
        warning_months = [p for p in projections if p["status"] == "warning"]
        
        prompt = f"""Analiza este escenario de simulación hídrica y genera un resumen ejecutivo:

ESCENARIO: {scenario_type}
NIVEL DE SEQUÍA: {drought_level * 100}%
CAMBIO DE DEMANDA: {demand_change * 100}%
CRECIMIENTO POBLACIONAL: {population_change * 100}%

DATOS PROYECTADOS:
- Volumen promedio mensual: {avg_projected:,.0f} m³
- Volumen total proyectado: {total_projected:,.0f} m³
- Máximo mensual: {max_projected:,.0f} m³
- Mínimo mensual: {min_projected:,.0f} m³
- Meses en estado crítico: {len(critical_months)}
- Meses en estado de alerta: {len(warning_months)}

Genera:
1. Un resumen de 2-3 oraciones
2. Lista de 3-5 recomendaciones específicas

Responde en formato JSON con campos "text" y "recommendations" (array)."""
        
        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_REPORT,
                temperature=0.3,
                max_tokens=1000
            )
            
            import json
            summary_data = json.loads(result)
            return summary_data
        except:
            recommendations = []
            if drought_level > 0.3:
                recommendations.append("Implementar restricciones de uso no esencial")
            if demand_change > 0.1:
                recommendations.append("Invertir en infraestructura de producción")
            if len(critical_months) > 0:
                recommendations.append("Preparar plan de emergencia para meses críticos")
            recommendations.append("Revisar eficiencia de la red de distribución")
            recommendations.append("Considerar fuentes alternativas de suministro")
            
            return {
                "text": f"El escenario {scenario_type} proyecta un {'déficit' if drought_level > demand_change else 'aumento'} significativo de demanda. Se requieren acciones inmediatas para meses críticos.",
                "recommendations": recommendations
            }

    async def compare_scenarios(
        self,
        session: AsyncSession,
        scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        results = []
        for scenario in scenarios:
            result = await self.simulate_scenario(
                session=session,
                scenario_type=scenario["name"],
                drought_level=scenario.get("drought_level", 0),
                demand_change=scenario.get("demand_change", 0),
                population_change=scenario.get("population_change", 0),
                months=scenario.get("months", 12)
            )
            results.append(result)
        
        comparison = {
            "scenarios": results,
            "comparison_summary": self._generate_comparison_summary(results)
        }
        
        return comparison

    def _generate_comparison_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No hay escenarios para comparar"
        
        best = min(results, key=lambda x: self._get_avg_deficit(x["projections"]))
        worst = max(results, key=lambda x: self._get_avg_deficit(x["projections"]))
        
        return f"El escenario '{best['scenario_type']}' es el más favorable con un déficit promedio del {self._get_avg_deficit(best['projections']):.1f}%. El escenario '{worst['scenario_type']}' presenta mayor riesgo con un déficit del {self._get_avg_deficit(worst['projections']):.1f}%."

    def _get_avg_deficit(self, projections: List[Dict]) -> float:
        if not projections:
            return 0
        return sum(p["percent_change"] for p in projections) / len(projections)


class ReportGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_executive_report(
        self,
        session: AsyncSession,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> Dict[str, Any]:
        consumptions_query = select(
            func.sum(Consumption.volume_m3).label("total_volume"),
            func.avg(Consumption.volume_m3).label("avg_volume"),
            func.count(Consumption.id).label("record_count"),
        )
        
        if start_date:
            consumptions_query = consumptions_query.where(
                Consumption.period_start >= start_date
            )
        if end_date:
            consumptions_query = consumptions_query.where(
                Consumption.period_end <= end_date
            )
        if location_id:
            consumptions_query = consumptions_query.where(
                Consumption.location_id == location_id
            )
        
        result = await session.execute(consumptions_query)
        stats = result.one()
        
        locations_query = select(func.count(Location.id)).where(Location.is_active == True)
        locations_result = await session.execute(locations_query)
        active_locations = locations_result.scalar()
        
        monthly_query = select(
            func.date_trunc("month", Consumption.period_start).label("month"),
            func.sum(Consumption.volume_m3).label("volume")
        ).group_by(
            func.date_trunc("month", Consumption.period_start)
        ).order_by(
            func.date_trunc("month", Consumption.period_start)
        )
        
        if start_date:
            monthly_query = monthly_query.where(Consumption.period_start >= start_date)
        if end_date:
            monthly_query = monthly_query.where(Consumption.period_end <= end_date)
        
        monthly_result = await session.execute(monthly_query)
        monthly_data = [
            {"month": str(row.month), "volume": float(row.volume)}
            for row in monthly_result.all()
        ]
        
        report_content = await self._generate_report_content(
            total_volume=float(stats.total_volume) if stats.total_volume else 0,
            avg_volume=float(stats.avg_volume) if stats.avg_volume else 0,
            record_count=stats.record_count,
            active_locations=active_locations,
            monthly_data=monthly_data,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "report_metadata": {
                "title": "Informe Ejecutivo ACUAMED",
                "generated_at": datetime.now().isoformat(),
                "period": {
                    "start": start_date or "Inicio de registros",
                    "end": end_date or "Fin de registros"
                }
            },
            "summary_metrics": {
                "total_volume_m3": float(stats.total_volume) if stats.total_volume else 0,
                "average_monthly_volume_m3": float(stats.avg_volume) if stats.avg_volume else 0,
                "total_records": stats.record_count,
                "active_locations": active_locations
            },
            "monthly_breakdown": monthly_data,
            "content": report_content
        }

    async def _generate_report_content(
        self,
        total_volume: float,
        avg_volume: float,
        record_count: int,
        active_locations: int,
        monthly_data: List[Dict],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Dict[str, Any]:
        trend = "estable"
        if len(monthly_data) >= 2:
            first_half = sum(d["volume"] for d in monthly_data[:len(monthly_data)//2]) / (len(monthly_data)//2)
            second_half = sum(d["volume"] for d in monthly_data[len(monthly_data)//2:]) / (len(monthly_data) - len(monthly_data)//2)
            if second_half > first_half * 1.1:
                trend = "ascendente"
            elif second_half < first_half * 0.9:
                trend = "descendente"
        
        prompt = f"""Genera un informe ejecutivo profesional para ACUAMED sobre gestión hídrica.

MÉTRICAS CLAVE:
- Volumen total: {total_volume:,.0f} m³
- Promedio mensual: {avg_volume:,.0f} m³
- Registros analizados: {record_count:,}
- Ubicaciones activas: {active_locations}
- Tendencia: {trend}

DATOS MENSUALES:
{chr(10).join([f"- {d['month']}: {d['volume']:,.0f} m³" for d in monthly_data[:6]])}

Genera en formato JSON:
{{
  "executive_summary": "Resumen ejecutivo de 3-4 oraciones",
  "key_findings": ["Hallazgo 1", "Hallazgo 2", "Hallazgo 3"],
  "metrics_interpretation": "Interpretación de las métricas principales",
  "recommendations": ["Recomendación 1", "Recomendación 2", "Recomendación 3"],
  "risk_alerts": ["Alerta de riesgo 1", "Alerta de riesgo 2"] o [] si no hay riesgos
}}"""
        
        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_REPORT,
                temperature=0.3,
                max_tokens=1500
            )
            
            import json
            content = json.loads(result)
            return content
        except:
            return {
                "executive_summary": f"Se han procesado {record_count:,} registros de consumo hídrico en {active_locations} ubicaciones activas.",
                "key_findings": [
                    f"El volumen total procesado es de {total_volume:,.0f} m³",
                    f"El promedio mensual de consumo es de {avg_volume:,.0f} m³",
                    "Los datos muestran una tendencia " + trend
                ],
                "metrics_interpretation": "Los indicadores sugieren una gestión hídrica efectiva.",
                "recommendations": [
                    "Mantener el monitoreo continuo de sensores",
                    "Revisar puntos de alta demanda para optimización",
                    "Preparar planes de contingencia para períodos de sequía"
                ],
                "risk_alerts": []
            }

    async def generate_location_report(
        self,
        session: AsyncSession,
        location_id: str
    ) -> Dict[str, Any]:
        from uuid import UUID
        
        location_result = await session.execute(
            select(Location).where(Location.id == UUID(location_id))
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            return {"error": "Ubicación no encontrada"}
        
        consumptions_query = select(
            Consumption
        ).where(
            Consumption.location_id == UUID(location_id)
        ).order_by(
            Consumption.period_start.desc()
        ).limit(50)
        
        result = await session.execute(consumptions_query)
        consumptions = result.scalars().all()
        
        if not consumptions:
            return {
                "location": {
                    "id": str(location.id),
                    "name": location.name,
                    "region": location.region,
                    "province": location.province
                },
                "message": "No hay datos de consumo para esta ubicación"
            }
        
        total_volume = sum(float(c.volume_m3) for c in consumptions)
        avg_volume = total_volume / len(consumptions)
        
        return {
            "location": {
                "id": str(location.id),
                "name": location.name,
                "region": location.region,
                "province": location.province,
                "latitude": location.latitude,
                "longitude": location.longitude
            },
            "summary": {
                "total_volume_m3": total_volume,
                "average_volume_m3": avg_volume,
                "record_count": len(consumptions)
            },
            "recent_consumptions": [
                {
                    "period_start": str(c.period_start),
                    "period_end": str(c.period_end),
                    "volume_m3": float(c.volume_m3),
                    "consumption_type": c.consumption_type
                }
                for c in consumptions[:12]
            ]
        }


whatif_simulator = WhatIfSimulator(llm_service)
report_generator = ReportGenerator(llm_service)
