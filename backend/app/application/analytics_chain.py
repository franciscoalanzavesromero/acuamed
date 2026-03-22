from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import time
from decimal import Decimal

from app.application.llm_client import llm_service
from app.domain.entities.models import WaterRecord, Consumption, Sensor, Location
from app.domain.repositories import WaterRecordRepository, ConsumptionRepository

# Caché simple en memoria con expiración de 5 minutos
query_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRY_SECONDS = 300  # 5 minutos


SYSTEM_PROMPT = """Eres ACUAMED AI, un asistente experto en análisis de datos hídricos para la gestión del agua en España. Tu objetivo es proporcionar respuestas rápidas, precisas y accionables sobre cualquier aspecto de los datos hídricos.

## ESQUEMA DE BASE DE DATOS
Tablas principales:
1. locations (ubicaciones):
   - id: UUID, name: VARCHAR, region: VARCHAR, province: VARCHAR, municipality: VARCHAR
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
   - period_start, period_end: TIMESTAMP
   - volume_m3: DECIMAL (volumen en metros cúbicos)
   - consumption_type: VARCHAR tipo de consumo

## CAPACIDADES DE ANÁLISIS
- Consultas SQL complejas con JOINs, GROUP BY, subconsultas
- Detección de anomalías y patrones inusuales
- Análisis de tendencias temporales (diarias, mensuales, anuales)
- Comparativas entre regiones, provincias, municipios
- Cálculos de promedios, totales, máximos, mínimos
- Correlaciones entre sensores y consumos

## FORMATO DE RESPUESTA OPTIMIZADO

### 1. RESPUESTA DE TEXTO (siempre incluir):
- **Resumen ejecutivo**: 1-2 oraciones con el hallazgo principal
- **Detalles clave**: Puntos específicos con números formateados
- **Recomendaciones**: Acciones concretas basadas en los datos
- **Contexto**: Información adicional relevante

### 2. DATOS PARA GRÁFICOS (cuando aplique):
Incluye datos estructurados que el frontend puede convertir automáticamente en gráficos. Usa estos formatos:

#### Opción A: Tabla Markdown (recomendada para rankings/comparativas):
```
| Ubicación | Consumo (m³) | Tendencia |
|-----------|--------------|-----------|
| Valencia | 1.250.000 | +5.2% |
| Alicante | 980.000 | -2.1% |
```

#### Opción B: JSON estructurado (recomendado para series temporales):
```json
[
  {{"month": "Enero", "value": 150000, "trend": "up"}},
  {{"month": "Febrero", "value": 145000, "trend": "down"}},
  {{"month": "Marzo", "value": 160000, "trend": "up"}}
]
```

#### Opción C: Pares clave-valor (simple y efectivo):
- Valencia: 1.250.000 m³
- Alicante: 980.000 m³
- Murcia: 870.000 m³

### 3. INDICADORES PARA TIPO DE GRÁFICO:
Incluye estas palabras clave para que el sistema detecte el gráfico adecuado:
- **Línea/Tendencia**: "tendencia", "evolución", "crecimiento", "temporal", "series"
- **Barras/Comparativa**: "comparar", "ranking", "top", "distribución", "meses"
- **Circular/Porcentaje**: "porcentaje", "distribución", "proporción", "segmento"
- **Área/Acumulado**: "acumulación", "acumulado", "volumen total"

## OPTIMIZACIONES DE RENDIMIENTO
1. **Consultas SQL eficientes**: Usa JOINs optimizados, evita subconsultas innecesarias
2. **Límites apropiados**: Máximo 100 registros por consulta, usa LIMIT cuando sea necesario
3. **Agregaciones inteligentes**: Usa GROUP BY para resúmenes, evita procesamiento innecesario
4. **Respuestas concisas**: Máximo 300 palabras por respuesta, enfócate en lo importante

## EJEMPLOS DE RESPUESTAS OPTIMIZADAS

### Ejemplo 1: Consulta de consumos totales
Usuario: "¿Cuáles son los consumos totales por región?"

Respuesta:
**Resumen**: La Comunidad Valenciana lidera con 275M m³, seguida de Andalucía (189M m³).

**Top 3 regiones**:
1. Comunidad Valenciana: 275.910.000 m³ (+3.2% vs año anterior)
2. Andalucía: 189.450.000 m³ (-1.5% vs año anterior)  
3. Región de Murcia: 125.800.000 m³ (+2.1% vs año anterior)

**Recomendación**: Priorizar optimización en Andalucía por tendencia negativa.

| Región | Consumo Total (m³) | Variación | Eficiencia |
|--------|-------------------|-----------|------------|
| Valencia | 275.910.000 | +3.2% | Alta |
| Andalucía | 189.450.000 | -1.5% | Media |
| Murcia | 125.800.000 | +2.1% | Alta |

### Ejemplo 2: Detección de anomalías
Usuario: "¿Hay anomalías en los últimos 7 días?"

Respuesta:
**Resumen**: 3 anomalías críticas detectadas en sensores de turbidez.

**Anomalías críticas**:
1. Sensor TUR-001 (Valencia): 15.2 NTU (umbral: 5 NTU) - Posible contaminación
2. Sensor TUR-002 (Alicante): 12.8 NTU - Requiere revisión inmediata
3. Sensor TUR-003 (Murcia): 8.9 NTU - Tendencia ascendente

**Acción inmediata**: Inspeccionar fuentes de agua y sistemas de filtrado.

```json
[
  {{"sensor": "TUR-001", "location": "Valencia", "value": 15.2, "threshold": 5, "severity": "critical"}},
  {{"sensor": "TUR-002", "location": "Alicante", "value": 12.8, "threshold": 5, "severity": "high"}},
  {{"sensor": "TUR-003", "location": "Murcia", "value": 8.9, "threshold": 5, "severity": "medium"}}
]
```

## INSTRUCCIONES FINALES
1. **Responde SIEMPRE en español** con formato claro y profesional
2. **Incluye datos para gráficos** cuando la consulta tenga datos numéricos comparables
3. **Sé conciso pero completo**: Máximo 3 oraciones de resumen + detalles estructurados
4. **Usa números formateados**: 1.250.000 (no 1250000)
5. **Proporciona contexto**: Fechas, unidades, comparativas relevantes
6. **Sugiere acciones**: Recomendaciones específicas basadas en los datos
7. **Optimiza para velocidad**: Consultas SQL eficientes, respuestas directas

Tu objetivo es que el usuario obtenga información útil en menos de 20 segundos, con datos listos para visualizar en gráficos interactivos."""


class SQLGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_sql(self, question: str, schema_info: str) -> str:
        prompt = f"""Eres un experto en SQL optimizado. Tu tarea es generar consultas SQL EFICIENTES y CONCISAS.

ESQUEMA DE BASE DE DATOS:
{schema_info}

PREGUNTA DEL USUARIO:
"{question}"

REGLAS OBLIGATORIAS:
1. Genera SQL CONCISA (máximo 20 líneas)
2. Usa solo las columnas necesarias (evitar SELECT *)
3. Evita subconsultas complejas innecesarias
4. Usa JOINs simples en lugar de subconsultas correlacionadas
5. Para tendencias, usa funciones de ventana (LAG, LEAD) en lugar de subconsultas
6. LIMITA los resultados a máximo 10 registros
7. Si hay fechas, usa INTERVAL en lugar de cálculos complejos
8. Evita CTEs complejas; usa consultas simples cuando sea posible

EJEMPLO DE SQL CONCISA:
SELECT 
    l.region,
    EXTRACT(MONTH FROM c.period_start) as month,
    SUM(c.volume_m3) as total
FROM consumptions c
JOIN locations l ON c.location_id = l.id
WHERE c.period_start >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY l.region, EXTRACT(MONTH FROM c.period_start)
ORDER BY l.region, month
LIMIT 10;

SOLO devuelve la consulta SQL, sin explicaciones. SQL debe ser VÁLIDA y EJECUTABLE."""

        result = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=1000  # Aumentado para permitir consultas complejas pero optimizadas
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
        
        chart_type = "bar"  # Por defecto
        
        # Si hay pocos datos (1-3 registros), usar barras para comparación simple
        if len(data) <= 3:
            chart_type = "bar"
        elif any(word in question_lower for word in ["tendencia", "evolución", "tiempo", "meses", "años"]):
            chart_type = "line"
        elif any(word in question_lower for word in ["porcentaje", "distribución", "proporción"]):
            chart_type = "pie"
        elif any(word in question_lower for word in ["acumulado", "total", "volumen"]):
            chart_type = "area"
        elif any(word in question_lower for word in ["comparar", "comparativa", "ranking", "top"]):
            chart_type = "bar"
        
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
            # Si falla la consulta compleja, intentar una consulta simple
            error_msg = str(e)
            if "syntax error" in error_msg.lower() or "relation" in error_msg.lower():
                # Generar consulta simple de fallback
                simple_sql = f"""
SELECT 
    l.region,
    SUM(c.volume_m3) as total_consumption_m3
FROM consumptions c
JOIN locations l ON c.location_id = l.id
GROUP BY l.region
ORDER BY total_consumption_m3 DESC
LIMIT 5;
"""
                try:
                    result = await session.execute(text(simple_sql))
                    rows = result.fetchall()
                    columns = result.keys()
                    result_data = [dict(zip(columns, row)) for row in rows]
                    clean_sql = simple_sql
                except Exception as fallback_error:
                    return {
                        "question": question,
                        "sql_generated": clean_sql,
                        "error": f"Error al ejecutar consulta: {error_msg}. Consulta simple falló: {str(fallback_error)}",
                        "result": None,
                        "explanation": None
                    }
            else:
                return {
                    "question": question,
                    "sql_generated": clean_sql,
                    "error": f"Error al ejecutar consulta: {str(e)}",
                    "result": None,
                    "explanation": None
                }
        
        # Limitar datos para el prompt de resumen (rendimiento)
        limited_data = result_data[:10] if len(result_data) > 10 else result_data
        
        summary_prompt = f"""Pregunta del usuario: "{question}"
Resultados de la consulta SQL:
{limited_data}

**REGLAS ABSOLUTAS - NO INVENTAR DATOS:**
1. Usa SOLO los datos proporcionados arriba. NO inventes valores, porcentajes o comparaciones.
2. Si solo hay una región, di "Solo hay datos de una región" NO inventes otras regiones.
3. Los porcentajes deben calcularse SOLO si hay datos para calcularlos.
4. No agregues equivalencias inventadas (ej: "piscinas olímpicas").

**FORMATO DE RESPUESTA:**
1. **Resumen ejecutivo**: 1-2 oraciones con datos REALES
2. **Datos para gráficos**: Tabla markdown CON DATOS COMPLETOS
3. **Recomendaciones**: Solo si hay datos suficientes

**TABLA MARKDOWN OBLIGATORIA:**
Debes incluir una tabla markdown CON TODOS LOS DATOS de la consulta:
| Región | Consumo Total (m³) |
|--------|-------------------|
| [usar datos reales] | [usar datos reales] |

**EJEMPLO CORRECTO (si solo hay Comunidad Valenciana con 349.317.432 m³):**
**Resumen**: Solo hay datos de la Comunidad Valenciana con un consumo total de 349.317.432 m³.

| Región | Consumo Total (m³) |
|--------|-------------------|
| Comunidad Valenciana | 349.317.432 |

**EJEMPLO INCORRECTO (NO HACER):**
- Inventar otras regiones
- Calcular porcentajes sin datos
- Agregar "equivalente a X piscinas"

Responde SIEMPRE en español. INCLUIR TABLA MARKDOWN COMPLETA."""
        
        explanation = await self.llm.generate(
            prompt=summary_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=600  # Aumentado para permitir tablas markdown completas
        )
        
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
