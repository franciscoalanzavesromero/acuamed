from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import time
import logging
from decimal import Decimal

from app.application.llm_client import llm_service
from app.domain.entities.models import WaterRecord, Consumption, Sensor, Location
from app.domain.repositories import WaterRecordRepository, ConsumptionRepository

logger = logging.getLogger(__name__)

# Caché simple en memoria con expiración de 10 minutos
query_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRY_SECONDS = 600  # 10 minutos


SYSTEM_PROMPT = """Eres ACUAMED AI, un asistente experto en análisis de datos hídricos para la gestión del agua en España. Tu objetivo es proporcionar respuestas rápidas, precisas y accionables sobre cualquier aspecto de los datos hídricos.

## ESQUEMA DE BASE DE DATOS
Tablas principales:
1. locations (ubicaciones):
   - id: UUID, name: VARCHAR (EJ: 'Sistema Carboneras (D+D)', 'Sistema Dalías (D)', 'Sistema Torrevieja (D+D)')
   - region: VARCHAR (Almería, Murcia, Alicante, Castellón, Valencia, etc.)
   - province: VARCHAR, municipality: VARCHAR
   - latitude, longitude: coordenadas geográficas
   
2. sensors (sensores):
   - id: UUID, sensor_code: VARCHAR único, name: VARCHAR
   - sensor_type: ENUM (caudalimetro, presion, temperatura, turbidez, ph, conductividad, nivel)
   - location_id: FK → locations.id, unit: VARCHAR unidad de medida
   
3. water_records (registros de agua):
   - id: UUID, sensor_id: FK → sensors.id, timestamp: TIMESTAMP
   - value: DECIMAL, is_anomaly: BOOLEAN, anomaly_score: FLOAT (0-1)
   - anomaly_reason: TEXT razón de la anomalía
   
4. consumptions (consumos):
   - id: UUID, location_id: FK → locations.id
   - period_start, period_end: TIMESTAMP (contienen año y mes)
   - volume_m3: DECIMAL (volumen en metros cúbicos)
   - consumption_type: VARCHAR tipo de consumo
   - Para filtrar por año: EXTRACT(YEAR FROM c.period_start) = 2025
   - Para agrupar por mes: EXTRACT(MONTH FROM c.period_start)

## PATRONES DE PREGUNTAS COMUNES

### EVOLUCIÓN TEMPORAL (ej: "evolución consumo Carboneras 2025"):
SELECT EXTRACT(MONTH FROM c.period_start) as mes,
       SUM(c.volume_m3) as total_consumo_m3
FROM consumptions c JOIN locations l ON c.location_id = l.id
WHERE LOWER(l.name) LIKE '%carboneras%'
  AND EXTRACT(YEAR FROM c.period_start) = 2025
GROUP BY EXTRACT(MONTH FROM c.period_start) ORDER BY mes;

### COMPARATIVA ENTRE SISTEMAS:
SELECT l.name, SUM(c.volume_m3) as total_consumo_m3
FROM consumptions c JOIN locations l ON c.location_id = l.id
GROUP BY l.name ORDER BY total_consumo_m3 DESC;

### UBICACIONES DISPONIBLES:
Los nombres en la BD son: Sistema Dalías (D), Sistema Valdelentisco (D+D),
Sistema Torrevieja (D+D), Sistema Águilas (D+D), Sistema Mutxamel (D+D),
Sistema Oropesa (D+D), Sistema Moncófar (D+D), Sistema Sagunto (D+D),
Sistema Carboneras (D+D).

Para buscar por nombre usar: LOWER(l.name) LIKE '%nombre_parcial%'

NUNCA digas "no hay datos" sin ejecutar primero una consulta SQL.

## FORMATO DE TABLA OBLIGATORIO (CRÍTICO - NO FALLAR)

CADA TABLA DEBE TENER EXACTAMENTE ESTE FORMATO:
| Encabezado1 | Encabezado2 |
|-------------|-------------|
| Valor1 | Valor2 |
| Valor3 | Valor4 |

REGLAS INQUEBRANTABLES:
1. CADA FILA EN UNA LÍNEA SEPARADA
2. UNA SOLA línea de separación (|-------------|-------------|)
3. NUNCA pongas múltiples filas en la misma línea
4. NUNCA pongas el separador en la misma línea que el encabezado
5. Los números SIN formato especial en los datos de la tabla
6. Máximo 2-3 columnas para gráficos

## FORMATO DE RESPUESTA

### ESTRUCTURA OBLIGATORIA:
1. **Resumen ejecutivo** (1-2 oraciones): Hallazgo principal con datos concretos
2. **Tabla de datos**: Formato limpio para gráficos
3. **Análisis clave**: Puntos importantes numerados
4. **Recomendaciones**: Acciones específicas basadas en los datos

RESPONDE SIEMPRE EN ESPAÑOL. SÉ CONCISO Y ACCIONABLE."""


class SQLGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_sql(self, question: str, schema_info: str) -> str:
        # Formato nativo de SQLCoder (defog/sqlcoder-7b-2)
        # El modelo está entrenado para completar este patrón exacto.
        prompt = f"""### Task
Generate a SQL query to answer [QUESTION]{question}[/QUESTION]

### Database Schema
The query will run on a PostgreSQL database with the following schema:
{schema_info}

### Additional rules
- Use LOWER(l.name) LIKE '%keyword%' to search location names
- Use EXTRACT(YEAR FROM c.period_start) to filter by year
- Use EXTRACT(MONTH FROM c.period_start) to group by month
- Do NOT add LIMIT for temporal/evolution queries (need all months)
- Add LIMIT 20 for other query types
- Use simple JOINs, avoid complex subqueries
- Return ONLY the SQL query, no explanations

### Answer
Given the database schema, here is the SQL query that answers [QUESTION]{question}[/QUESTION]
[SQL]"""

        # SQLCoder no necesita system prompt, el formato del prompt es suficiente
        result = await self.llm.generate(
            prompt=prompt,
            system_prompt=None,
            temperature=0.1,
            max_tokens=512
        )
        # SQLCoder puede cerrar con [/SQL] - lo limpiamos
        sql = result.strip() if result else ""
        if "[/SQL]" in sql:
            sql = sql[:sql.index("[/SQL]")].strip()
        return sql

    async def get_schema_description(self, session: AsyncSession) -> str:
        schema = """
TABLAS DISPONIBLES:

1. locations
   - id: UUID (clave primaria)
   - name: VARCHAR(255) - nombre de la ubicación
     EJEMPLOS: 'Sistema Carboneras (D+D)', 'Sistema Dalías (D)', 'Sistema Torrevieja (D+D)',
               'Sistema Águilas (D+D)', 'Sistema Sagunto (D+D)', 'Sistema Oropesa (D+D)',
               'Sistema Moncófar (D+D)', 'Sistema Mutxamel (D+D)', 'Sistema Valdelentisco (D+D)'
   - region: VARCHAR(100) - región (Almería, Murcia, Alicante, Castellón, Valencia)
   - province: VARCHAR(100) - provincia
   - latitude, longitude: coordenadas

2. consumptions
   - id: UUID (clave primaria)
   - location_id: UUID (FK -> locations.id)
   - period_start: TIMESTAMP - inicio del período (CONTIENE AÑO Y MES)
   - period_end: TIMESTAMP - fin del período
   - volume_m3: DECIMAL - volumen en metros cúbicos
   - consumption_type: VARCHAR(50) - tipo de consumo

PATRONES SQL:

-- Evolución mensual por ubicación (para preguntas como "evolución Carboneras 2025"):
SELECT EXTRACT(MONTH FROM c.period_start) as mes,
       SUM(c.volume_m3) as total_consumo_m3
FROM consumptions c JOIN locations l ON c.location_id = l.id
WHERE LOWER(l.name) LIKE '%carboneras%'
  AND EXTRACT(YEAR FROM c.period_start) = 2025
GROUP BY EXTRACT(MONTH FROM c.period_start) ORDER BY mes;

-- Consumo total por sistema:
SELECT l.name, SUM(c.volume_m3) as total_consumo_m3
FROM consumptions c JOIN locations l ON c.location_id = l.id
GROUP BY l.name ORDER BY total_consumo_m3 DESC;

-- Evolución por sistema y mes (sin LIMIT para series temporales):
SELECT l.name, EXTRACT(MONTH FROM c.period_start) as mes,
       SUM(c.volume_m3) as total_consumo_m3
FROM consumptions c JOIN locations l ON c.location_id = l.id
WHERE EXTRACT(YEAR FROM c.period_start) = 2025
GROUP BY l.name, EXTRACT(MONTH FROM c.period_start)
ORDER BY l.name, mes;
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
    # Pre-calculated queries for common trends (faster response)
    PRE_CALCULATED_QUERIES = {
        "evolución carboneras": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumo_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            WHERE LOWER(l.name) LIKE '%carboneras%'
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "evolución dalías": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumo_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            WHERE LOWER(l.name) LIKE '%dali%'
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "evolución torrevieja": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumo_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            WHERE LOWER(l.name) LIKE '%torrevieja%'
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "evolución águilas": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumo_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            WHERE LOWER(l.name) LIKE '%águilas%' OR LOWER(l.name) LIKE '%aguilas%'
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "evolución sagunto": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumo_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            WHERE LOWER(l.name) LIKE '%sagunto%'
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "consumo total": """
            SELECT l.region, SUM(c.volume_m3) as total_consumption_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            GROUP BY l.region ORDER BY total_consumption_m3 DESC LIMIT 10;
        """,
        "tendencia mensual": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumption_m3
            FROM consumptions c
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "consumo mensual": """
            SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                   EXTRACT(YEAR FROM c.period_start) as anio,
                   SUM(c.volume_m3) as total_consumption_m3
            FROM consumptions c
            GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
            ORDER BY anio, mes;
        """,
        "anomalias recientes": """
            SELECT s.sensor_code, l.region, wr.value, wr.anomaly_score, wr.timestamp
            FROM water_records wr
            JOIN sensors s ON wr.sensor_id = s.id
            JOIN locations l ON s.location_id = l.id
            WHERE wr.is_anomaly = true AND wr.timestamp >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY wr.anomaly_score DESC LIMIT 10;
        """,
        "top ubicaciones": """
            SELECT l.name, l.region, SUM(c.volume_m3) as total_consumption_m3
            FROM consumptions c JOIN locations l ON c.location_id = l.id
            GROUP BY l.name, l.region ORDER BY total_consumption_m3 DESC LIMIT 5;
        """,
    }

    def __init__(self):
        self.llm = llm_service
        self.sql_generator = SQLGenerator(self.llm)
        self.anomaly_detector = AnomalyDetector(self.llm)

    def _generate_cache_key(self, question: str) -> str:
        """Genera una clave de caché basada en la pregunta normalizada"""
        # Normalizar la pregunta: minúsculas, sin espacios extra
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtiene un resultado del caché si existe y no ha expirado"""
        if cache_key in query_cache:
            cached = query_cache[cache_key]
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_SECONDS:
                return cached['result']
            else:
                # Eliminar entradas expiradas
                del query_cache[cache_key]
        return None
    
    def _set_cached_result(self, cache_key: str, result: Dict[str, Any]):
        """Guarda un resultado en el caché"""
        query_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        # Limpiar caché si excede 100 entradas
        if len(query_cache) > 100:
            # Eliminar las entradas más antiguas
            oldest_keys = sorted(
                query_cache.keys(),
                key=lambda k: query_cache[k]['timestamp']
            )[:10]  # Eliminar las 10 más antiguas
            for key in oldest_keys:
                del query_cache[key]
    
    def _analyze_data_for_charts(self, data: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
        """Analiza los datos para determinar el mejor formato de gráfico"""
        if not data:
            return {"has_data": False}
        
        # Analizar estructura de datos
        columns = list(data[0].keys()) if data else []
        numeric_columns = []
        
        # Identificar columnas numéricas
        
        for col in columns:
            # Verificar si la columna contiene valores numéricos (no None)
            has_numeric = False
            for row in data[:5]:  # Revisar primeras 5 filas
                value = row.get(col)
                # Verificar si es numérico (int, float o Decimal)
                if value is not None and isinstance(value, (int, float, Decimal)):
                    has_numeric = True
                    break
            if has_numeric:
                numeric_columns.append(col)
        
        # Determinar tipo de gráfico basado en datos y pregunta
        question_lower = question.lower()
        
        # Detectar si los datos tienen columnas temporales
        has_temporal_col = any(
            any(t in col.lower() for t in ["month", "year", "date", "period", "mes", "año"])
            for col in columns
        )

        chart_type = "bar"  # Por defecto

        if any(word in question_lower for word in ["tendencia", "evolución", "histórico", "evolucio", "tiempo", "series temporales"]):
            chart_type = "line"
        elif has_temporal_col and any(word in question_lower for word in ["mensual", "anual", "mes", "año", "meses", "años"]):
            chart_type = "line"
        elif any(word in question_lower for word in ["porcentaje", "proporción", "reparto", "radial", "región", "regiones"]):
            chart_type = "pie"
        elif any(word in question_lower for word in ["acumulado", "acumulación"]):
            chart_type = "area"
        elif has_temporal_col:
            chart_type = "area"
        elif 3 <= len(data) <= 7 and not any(word in question_lower for word in ["top", "ranking", "comparar"]):
            # Pocos registros sin intención de ranking → pie
            chart_type = "pie"
        
        # Determinar ejes - priorizar columnas con datos más relevantes
        # Primero verificar si es una consulta de tendencia temporal
        question_lower = question.lower()
        is_temporal = any(word in question_lower for word in ["tendencia", "evolución", "tiempo", "mes", "año", "meses", "años", "período", "periodo", "evolution", "trend"])
        
        # Orden de prioridad para ejes X
        if is_temporal:
            # Para tendencias temporales, priorizar columnas de fecha
            # "month" debe tener prioridad sobre "region"
            x_axis_candidates = ["month", "date", "year", "period", "timestamp", "time", "day", "week", "quarter"]
        else:
            # Para consultas normales, priorizar categorías
            x_axis_candidates = ["name", "location", "region", "province", "municipality", 
                               "sensor", "type", "category"]
        
        # Buscar la primera columna que coincida con los candidatos
        x_axis = None
        for candidate in x_axis_candidates:
            for col in columns:
                if candidate in col.lower():
                    x_axis = col
                    break
            if x_axis:
                break
        
        # Si no se encuentra, usar la primera columna que no sea numérica
        if not x_axis:
            for col in columns:
                # Verificar si es columna no numérica (candidata a eje X)
                is_numeric = False
                for row in data[:1]:
                    if isinstance(row.get(col), (int, float, Decimal)):
                        is_numeric = True
                        break
                if not is_numeric:
                    x_axis = col
                    break
        
        # Si aún no hay, usar la primera columna
        if not x_axis:
            x_axis = columns[0] if columns else "name"
        
        # Para y_axis, priorizar columnas que parecen contener valores principales
        # Orden de prioridad: total_consumption > total > consumption > volume > value > amount > average > max > min > count
        y_axis_priority = ["total_consumption", "total", "consumption", "volume", "value", "amount", "average", "max", "min", "count"]
        y_axis = None
        
        # Primero buscar coincidencias exactas o parciales que empiecen con la palabra clave
        for priority in y_axis_priority:
            for col in numeric_columns:
                if col != x_axis:
                    col_lower = col.lower()
                    # Coincidencia exacta o que empieza con la palabra clave
                    if col_lower == priority or col_lower.startswith(priority):
                        y_axis = col
                        break
                    # Coincidencia que contiene la palabra clave (menos prioritario)
                    elif priority in col_lower:
                        y_axis = col
                        break
            if y_axis:
                break
        
        # Si no se encuentra, usar la primera columna numérica que no sea x_axis
        if not y_axis:
            for col in numeric_columns:
                if col != x_axis:
                    y_axis = col
                    break
        
        # Si aún no hay y_axis, usar "value" como fallback
        if not y_axis:
            y_axis = "value"
        
        # Generar título apropiado
        chart_title = f"Consumo por {x_axis}" if x_axis != "name" else "Distribución de datos"
        if "region" in x_axis.lower():
            chart_title = "Consumo por Región"
        elif "province" in x_axis.lower():
            chart_title = "Consumo por Provincia"
        elif "month" in x_axis.lower() or "year" in x_axis.lower():
            chart_title = "Evolución Temporal"
        
        # Formato que el frontend espera (compatibilidad con chartGenerator.ts)
        return {
            "has_data": True,
            "type": chart_type,  # El frontend espera 'type' no 'chart_type'
            "chart_type": chart_type,  # Mantener ambos por compatibilidad
            "x_axis": x_axis,
            "y_axis": y_axis,
            "data_keys": numeric_columns,
            "total_records": len(data),
            "sample_data": data[:5],  # Muestra para contexto
            "data": data[:10],  # Datos completos para el frontend
            "title": chart_title,
            "description": f"Datos de {len(data)} registros"
        }

    def _get_pre_calculated_sql(self, question: str) -> Optional[str]:
        """Busca una consulta pre-calculada para preguntas comunes.
        Ordena por longitud descendente para que las más específicas coincidan primero."""
        question_lower = question.lower()
        sorted_keys = sorted(self.PRE_CALCULATED_QUERIES.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in question_lower:
                return self.PRE_CALCULATED_QUERIES[key]
        return None

    async def query_natural_language(
        self,
        question: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        import re
        from sqlalchemy import text
        
        # Verificar caché primero
        cache_key = self._generate_cache_key(question)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Verificar consultas pre-calculadas (más rápido que generar SQL)
        pre_calculated = self._get_pre_calculated_sql(question)
        if pre_calculated:
            logger.info(f"[QUERY_NL] Pregunta: '{question}'")
            logger.info(f"[QUERY_NL] Usando consulta pre-calculada: {pre_calculated[:100]}...")
            try:
                result = await session.execute(text(pre_calculated))
                rows = result.fetchall()
                columns = result.keys()
                result_data = [dict(zip(columns, row)) for row in rows]
                
                chart_context = self._analyze_data_for_charts(result_data, question)
                
                summary_prompt = f"""Pregunta: "{question}"
Datos: {result_data[:5]}

INSTRUCCIONES CRÍTICAS:
1. USA SOLO LOS DATOS PROPORCIONADOS
2. CADA FILA EN UNA LÍNEA SEPARADA
3. NÚMEROS SIN formato (123456789, NO 123.456.789)

**Resumen**: [1-2 oraciones]

| [Col1] | [Col2] |
|--------|--------|
| [Dato] | [Valor] |

EJEMPLO:
| Sistema | Consumo |
|---------|---------|
| Carboneras | 99447958 |"""
                
                explanation = await self.llm.generate(
                    prompt=summary_prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=400
                )
                
                logger.info(f"[QUERY_NL] Pre-calculada: tabla en respuesta: {'|' in explanation}")
                
                result = {
                    "question": question,
                    "sql_generated": pre_calculated,
                    "result": result_data,
                    "count": len(result_data),
                    "explanation": explanation,
                    "chart_context": chart_context,
                    "pre_calculated": True
                }
                
                self._set_cached_result(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Query pre-calculada falló: {e}. Generando SQL con LLM...")
                # Continuar a la generación SQL con LLM
        
        schema = await self.sql_generator.get_schema_description(session)
        
        sql_query = await self.sql_generator.generate_sql(question, schema)
        
        # Limpiar formato markdown de la consulta SQL
        clean_sql = sql_query
        
        # Primero intentar extraer de bloques de código markdown
        if "```" in sql_query:
            match = re.search(r'```(?:sql)?\s*(.*?)```', sql_query, re.DOTALL | re.IGNORECASE)
            if match:
                clean_sql = match.group(1).strip()
            else:
                # Si hay ``` de apertura pero no de cierre, tomar todo después de ```
                match = re.search(r'```(?:sql)?\s*(.*?)$', sql_query, re.DOTALL | re.IGNORECASE)
                if match:
                    clean_sql = match.group(1).strip()
        
        # Si la SQL parece estar cortada (no termina con ; o paréntesis), intentar repararla
        clean_sql = clean_sql.rstrip()
        if clean_sql and not clean_sql.endswith((';', ')', 'LIMIT 10')):
            # Si no termina correctamente, buscar el último punto y coma o cierre
            last_semicolon = clean_sql.rfind(';')
            last_paren = clean_sql.rfind(')')
            if last_semicolon > 0:
                clean_sql = clean_sql[:last_semicolon + 1]
            elif last_paren > 0:
                clean_sql = clean_sql[:last_paren + 1]
            else:
                # Agregar LIMIT 10 y cierre si no está completo
                if 'GROUP BY' in clean_sql.upper() and 'LIMIT' not in clean_sql.upper():
                    clean_sql += '\nLIMIT 10;'
        
        result_data = []
        try:
            if "SELECT" in clean_sql.upper():
                result = await session.execute(text(clean_sql))
                rows = result.fetchall()
                columns = result.keys()
                result_data = [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error SQL primario: {error_msg}")
            
            # Fallback 1: Consulta inteligente basada en el tipo de error y la pregunta
            fallback_queries = []
            
            # Detectar si la pregunta menciona una ubicación específica
            location_keywords = [
                'carboneras', 'dalías', 'dalias', 'torrevieja', 'águilas', 'aguilas',
                'sagunto', 'mutxamel', 'oropesa', 'moncófar', 'valdelentisco'
            ]
            found_location = None
            for loc in location_keywords:
                if loc in question.lower():
                    found_location = loc
                    break
            
            if found_location:
                # Fallback específico por ubicación
                fallback_queries.append(f"""
                    SELECT EXTRACT(MONTH FROM c.period_start) as mes,
                           EXTRACT(YEAR FROM c.period_start) as anio,
                           SUM(c.volume_m3) as total_consumo_m3
                    FROM consumptions c
                    JOIN locations l ON c.location_id = l.id
                    WHERE LOWER(l.name) LIKE '%{found_location}%'
                    GROUP BY EXTRACT(YEAR FROM c.period_start), EXTRACT(MONTH FROM c.period_start)
                    ORDER BY anio, mes;
                """)
            
            # Fallback genérico: consumos por ubicación y mes del año actual
            fallback_queries.append("""
                SELECT l.name as sistema,
                       EXTRACT(MONTH FROM c.period_start) as mes,
                       SUM(c.volume_m3) as total_consumo_m3
                FROM consumptions c JOIN locations l ON c.location_id = l.id
                WHERE EXTRACT(YEAR FROM c.period_start) = EXTRACT(YEAR FROM CURRENT_DATE)
                GROUP BY l.name, EXTRACT(MONTH FROM c.period_start)
                ORDER BY l.name, mes;
            """)
            
            # Fallback: registros recientes
            fallback_queries.append("""
                SELECT l.name, l.region, wr.value, wr.timestamp
                FROM water_records wr
                JOIN sensors s ON wr.sensor_id = s.id
                JOIN locations l ON s.location_id = l.id
                ORDER BY wr.timestamp DESC LIMIT 10;
            """)
            
            fallback_success = False
            for idx, fallback_sql in enumerate(fallback_queries):
                try:
                    result = await session.execute(text(fallback_sql))
                    rows = result.fetchall()
                    columns = result.keys()
                    result_data = [dict(zip(columns, row)) for row in rows]
                    clean_sql = fallback_sql
                    fallback_success = True
                    logger.info(f"Fallback {idx + 1} ejecutado correctamente")
                    break
                except Exception as fallback_error:
                    logger.warning(f"Fallback {idx + 1} falló: {str(fallback_error)}")
                    continue
            
            if not fallback_success:
                return {
                    "question": question,
                    "sql_generated": clean_sql,
                    "error": f"Error en consulta: {error_msg}. No se pudo ejecutar consulta de respaldo. Verifica la conexión a la base de datos.",
                    "result": None,
                    "explanation": "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, intenta reformular la pregunta o contacta al administrador.",
                    "error_type": "database_error"
                }
        
        # Limitar datos para el prompt de resumen (rendimiento)
        # Para series temporales, enviar todos los datos. Para otros, limitar
        question_lower_q = question.lower()
        is_temporal_q = any(w in question_lower_q for w in [
            "evolución", "evolucion", "tendencia", "mensual", "mes", "temporal",
            "anual", "año", "años", "periodo", "período"
        ])
        if is_temporal_q:
            limited_data = result_data[:30] if len(result_data) > 30 else result_data
        else:
            limited_data = result_data[:20] if len(result_data) > 20 else result_data
        
        # Generar tabla markdown en Python directamente desde los datos
        # (no depender del LLM para el formato de tabla - SQLCoder es un modelo SQL, no chat)
        def build_markdown_table(data: list) -> str:
            if not data:
                return ""
            columns = list(data[0].keys())
            sep = "|" + "|".join("-" * (len(c) + 2) for c in columns) + "|"
            header = "| " + " | ".join(str(c) for c in columns) + " |"
            rows = []
            for row in data:
                cells = []
                for c in columns:
                    v = row[c]
                    cells.append(str(v) if v is not None else "")
                rows.append("| " + " | ".join(cells) + " |")
            return "\n".join([header, sep] + rows)

        markdown_table = build_markdown_table(limited_data)

        # Pedir al LLM solo un resumen textual breve (sin tabla)
        summary_prompt = f"""Pregunta: "{question}"
Datos: {limited_data[:5]}

Escribe UN resumen ejecutivo de 1-2 oraciones en español con el hallazgo principal.
Solo texto, sin tablas ni listas."""

        try:
            llm_summary = await self.llm.generate(
                prompt=summary_prompt,
                system_prompt=None,
                temperature=0.3,
                max_tokens=150
            )
            llm_summary = llm_summary.strip() if llm_summary else ""
        except Exception:
            llm_summary = ""

        # Combinar: resumen LLM + tabla generada en Python
        if llm_summary:
            explanation = f"**Resumen**: {llm_summary}\n\n{markdown_table}"
        else:
            explanation = markdown_table

        logger.info(f"[QUERY_NL] Tabla generada en Python: {len(limited_data)} filas")
        
        # Analizar datos para determinar el mejor formato de gráfico
        chart_context = self._analyze_data_for_charts(result_data, question)
        
        result = {
            "question": question,
            "sql_generated": sql_query,
            "result": result_data,
            "count": len(result_data),
            "explanation": explanation,
            "chart_context": chart_context  # Contexto adicional para generación de gráficos
        }
        
        # Guardar en caché
        self._set_cached_result(cache_key, result)
        
        return result

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
            LIMIT 10
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        # Filtrar solo anomalías por encima del umbral
        anomaly_rows = [row for row in rows if row.z_score > threshold_z]
        
        if not anomaly_rows:
            return []
        
        # Preparar datos para UNA SOLA llamada al LLM
        anomalies_summary = []
        for row in anomaly_rows[:5]:  # Máximo 5 anomalías para análisis
            anomalies_summary.append(
                f"- ID: {row.location_id[:8]}..., Volumen: {row.volume_m3:,.2f} m³, "
                f"Promedio: {row.avg_volume:,.2f} m³, Z-Score: {row.z_score:.2f}, "
                f"Período: {row.period_start} a {row.period_end}"
            )
        
        anomalies_text = "\n".join(anomalies_summary)
        
        # UNA SOLA llamada al LLM para todas las anomalías
        prompt = f"""Analiza estas {len(anomalies_summary)} anomalías de consumo de agua detectadas:

{anomalies_text}

Para cada anomalía indica en UNA SOLA línea:
- Causa más probable (fuga/error medición/aumento demanda)
- Nivel de criticidad (crítico/alto/medio)

Respuesta concisa, máximo 100 palabras total."""
        
        try:
            batch_analysis = await self.llm.generate(
                prompt=prompt,
                system_prompt="Eres un experto en análisis de datos hídricos. Responde de forma concisa.",
                temperature=0.3,
                max_tokens=400
            )
        except Exception as e:
            logger.error(f"Error en análisis de anomalías: {e}")
            batch_analysis = "Análisis no disponible"
        
        # Construir respuesta
        anomalies = []
        for row in anomaly_rows:
            severity = "critical" if row.z_score > 5 else "high" if row.z_score > 3 else "medium"
            anomalies.append({
                "id": str(row.id),
                "location_id": str(row.location_id),
                "volume_m3": float(row.volume_m3),
                "avg_volume": float(row.avg_volume),
                "z_score": float(row.z_score),
                "period_start": str(row.period_start),
                "period_end": str(row.period_end),
                "severity": severity,
                "llm_analysis": batch_analysis if len(anomalies) == 0 else None
            })
        
        return anomalies


analytics_chain = AnalyticsChain()
