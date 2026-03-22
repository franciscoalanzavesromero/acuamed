from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.llm_client import llm_service
from app.domain.entities.models import WaterRecord, Consumption, Sensor, Location
from app.domain.repositories import WaterRecordRepository, ConsumptionRepository


SYSTEM_PROMPT = """Eres un asistente especializado en análisis de datos hídricos para ACUAMED.

El esquema de la base de datos incluye:
- locations: id, name, region, province, municipality, latitude, longitude
- sensors: id, sensor_code, name, sensor_type, location_id, unit
- water_records: id, sensor_id, timestamp, value, is_anomaly, anomaly_score
- consumptions: id, location_id, period_start, period_end, volume_m3, consumption_type

Responde siempre en español. Proporciona análisis claros y accionables."""


class SQLGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_sql(self, question: str, schema_info: str) -> str:
        prompt = f"""Dados los siguientes datos del esquema de base de datos:
{schema_info}

Genera una consulta SQL válida para PostgreSQL que responda a esta pregunta:
"{question}"

Solo devuelve la consulta SQL, sin explicaciones adicionales. La consulta debe ser válida y ejecutable."""

        result = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=1000
        )
        return result.strip() if result else ""

    async def get_schema_description(self, session: AsyncSession) -> str:
        schema = """
TABLAS DISPONIBLES:

1. locations
   - id: UUID (clave primaria)
   - name: VARCHAR(255) - nombre de la ubicación
   - region: VARCHAR(100) - región
   - province: VARCHAR(100) - provincia
   - municipality: VARCHAR(100) - municipio
   - latitude, longitude: coordenadas

2. sensors
   - id: UUID (clave primaria)
   - sensor_code: VARCHAR(50) - código único del sensor
   - name: VARCHAR(255) - nombre descriptivo
   - sensor_type: ENUM(caudalimetro, presion, temperatura, turbidez, ph, conductividad, nivel)
   - location_id: UUID (FK -> locations.id)
   - unit: VARCHAR(20) - unidad de medida

3. water_records
   - id: UUID (clave primaria)
   - sensor_id: UUID (FK -> sensors.id)
   - timestamp: TIMESTAMP WITH TIME ZONE
   - value: DECIMAL
   - is_anomaly: BOOLEAN
   - anomaly_score: FLOAT (0-1)
   - anomaly_reason: TEXT

4. consumptions
   - id: UUID (clave primaria)
   - location_id: UUID (FK -> locations.id)
   - period_start: TIMESTAMP
   - period_end: TIMESTAMP
   - volume_m3: DECIMAL - volumen en metros cúbicos
   - consumption_type: VARCHAR(50) - tipo de consumo
"""
        return schema


class AnomalyDetector:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def analyze_anomaly(
        self,
        record_value: float,
        sensor_type: str,
        historical_values: List[float],
        timestamp: str
    ) -> Dict[str, Any]:
        import statistics
        
        if not historical_values:
            return {
                "is_anomaly": False,
                "score": 0.0,
                "reason": "Sin datos históricos para comparar"
            }
        
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if stdev == 0:
            z_score = 0
        else:
            z_score = abs((record_value - mean) / stdev)
        
        is_anomaly = z_score > 3
        
        prompt = f"""Analiza el siguiente dato de sensor hídrico para ACUAMED:

- Tipo de sensor: {sensor_type}
- Valor registrado: {record_value}
- Media histórica: {mean:.2f}
- Desviación estándar: {stdev:.2f}
- Puntuación Z: {z_score:.2f}
- Timestamp: {timestamp}

¿Este valor representa una anomalía? Explica brevemente (1-2 oraciones)."""
        
        llm_analysis = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=500
        )
        
        return {
            "is_anomaly": is_anomaly,
            "score": min(z_score / 3, 1.0) if is_anomaly else 0.0,
            "reason": llm_analysis,
            "z_score": z_score,
            "mean": mean,
            "stdev": stdev
        }


class AnalyticsChain:
    def __init__(self):
        self.llm = llm_service
        self.sql_generator = SQLGenerator(self.llm)
        self.anomaly_detector = AnomalyDetector(self.llm)

    async def query_natural_language(
        self,
        question: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        import re
        from sqlalchemy import text
        
        schema = await self.sql_generator.get_schema_description(session)
        
        sql_query = await self.sql_generator.generate_sql(question, schema)
        
        # Limpiar formato markdown de la consulta SQL
        clean_sql = sql_query
        if "```" in sql_query:
            # Extraer SQL de bloques de código markdown
            match = re.search(r'```(?:sql)?\s*(.*?)```', sql_query, re.DOTALL | re.IGNORECASE)
            if match:
                clean_sql = match.group(1).strip()
        
        result_data = []
        try:
            if "SELECT" in clean_sql.upper():
                result = await session.execute(text(clean_sql))
                rows = result.fetchall()
                columns = result.keys()
                result_data = [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            return {
                "question": question,
                "sql_generated": clean_sql,
                "error": f"Error al ejecutar consulta: {str(e)}",
                "result": None,
                "explanation": None
            }
        
        summary_prompt = f"""Pregunta del usuario: "{question}"
Resultados de la consulta SQL:
{result_data[:10] if len(result_data) > 10 else result_data}

Proporciona un resumen claro y conciso de estos resultados en español (máximo 3 oraciones)."""
        
        explanation = await self.llm.generate(
            prompt=summary_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=500
        )
        
        return {
            "question": question,
            "sql_generated": sql_query,
            "result": result_data,
            "count": len(result_data),
            "explanation": explanation
        }

    async def get_consumption_summary(
        self,
        session: AsyncSession,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> Dict[str, Any]:
        query = select(
            Consumption.period_start,
            Consumption.period_end,
            func.sum(Consumption.volume_m3).label("total_volume"),
            func.count(Consumption.id).label("record_count"),
            Consumption.consumption_type
        ).group_by(
            Consumption.period_start,
            Consumption.period_end,
            Consumption.consumption_type
        ).order_by(Consumption.period_start.desc())
        
        if start_date:
            query = query.where(Consumption.period_start >= start_date)
        if end_date:
            query = query.where(Consumption.period_end <= end_date)
        if location_id:
            query = query.where(Consumption.location_id == location_id)
        
        result = await session.execute(query)
        rows = result.all()
        
        return {
            "period_summary": [
                {
                    "period_start": str(row.period_start),
                    "period_end": str(row.period_end),
                    "total_volume_m3": float(row.total_volume),
                    "record_count": row.record_count,
                    "consumption_type": row.consumption_type
                }
                for row in rows
            ],
            "total_records": len(rows)
        }

    async def detect_consumption_anomalies(
        self,
        session: AsyncSession,
        threshold_z: float = 2.5
    ) -> List[Dict[str, Any]]:
        from sqlalchemy import text
        
        query = text("""
            WITH stats AS (
                SELECT 
                    location_id,
                    AVG(volume_m3) as avg_volume,
                    STDDEV(volume_m3) as std_volume
                FROM consumptions
                WHERE volume_m3 > 0
                GROUP BY location_id
            )
            SELECT 
                c.id,
                c.location_id,
                c.volume_m3,
                c.period_start,
                c.period_end,
                s.avg_volume,
                s.std_volume,
                ABS(c.volume_m3 - s.avg_volume) / NULLIF(s.std_volume, 0) as z_score
            FROM consumptions c
            JOIN stats s ON c.location_id = s.location_id
            WHERE c.volume_m3 > 0 AND s.std_volume > 0
            ORDER BY z_score DESC
            LIMIT 50
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        anomalies = []
        for row in rows:
            if row.z_score > threshold_z:
                prompt = f"""Analiza esta anomalía de consumo de agua detectada:

- Ubicación ID: {row.location_id}
- Volumen consumido: {row.volume_m3} m³
- Volumen promedio: {row.avg_volume:.2f} m³
- Z-Score: {row.z_score:.2f}
- Período: {row.period_start} a {row.period_end}

Posibles causas (fuga,Error de medición, aumento de demanda, etc.)"""
                
                analysis = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=300
                )
                
                anomalies.append({
                    "id": str(row.id),
                    "location_id": str(row.location_id),
                    "volume_m3": float(row.volume_m3),
                    "avg_volume": float(row.avg_volume),
                    "z_score": float(row.z_score),
                    "period_start": str(row.period_start),
                    "period_end": str(row.period_end),
                    "llm_analysis": analysis,
                    "severity": "high" if row.z_score > 3 else "medium"
                })
        
        return anomalies


analytics_chain = AnalyticsChain()
