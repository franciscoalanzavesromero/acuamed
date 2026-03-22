import { ChartConfig, ChartType, ChartDataPoint, DEFAULT_COLORS } from '../types/charts'

export interface ParsedChartData {
  type: ChartType
  title: string
  data: ChartDataPoint[]
  dataKeys: string[]
  xAxisKey: string
  description?: string
  confidence: number
}

const CHART_INDICATORS: Record<ChartType, string[]> = {
  line: ['tendencia', 'evolución', 'crecimiento', 'temporal', 'tiempo', 'series'],
  bar: ['comparar', 'comparativa', 'ranking', 'top', 'distribución', 'meses', 'anual'],
  pie: ['porcentaje', 'distribución', 'proporción', 'parte', 'segmento'],
  area: ['acumulación', 'acumulado', 'volumen total', 'cumulative'],
  composed: ['múltiple', 'combinado', 'varios', 'comparar con'],
  table: ['detalle', 'lista', 'registro', 'tabla', 'completo'],
  scatter: ['dispersión', 'correlación', 'relación', 'scatter', 'disperse'],
  heatmap: ['mapa de calor', 'intensidad', 'heatmap', 'calor', 'densidad']
}

const DATA_PATTERN = /(\d+[.,]\d+|\d+)/g

export const parseChartFromText = (content: string, context?: any): ParsedChartData | null => {
  const lowerContent = content.toLowerCase()
  
  let detectedType: ChartType = 'bar'
  let maxScore = 0
  
  for (const [type, keywords] of Object.entries(CHART_INDICATORS)) {
    const score = keywords.filter(kw => lowerContent.includes(kw)).length
    if (score > maxScore) {
      maxScore = score
      detectedType = type as ChartType
    }
  }
  
  if (maxScore === 0 && context?.type) {
    detectedType = context.type
  }
  
  const title = extractTitle(content) || generateTitle(detectedType)
  
  const data = extractDataFromContent(content, context)
  
  if (data.length === 0 && context?.data) {
    data.push(...context.data)
  }
  
  const dataKeys = data.length > 0 ? Object.keys(data[0]).filter(k => k !== 'name' && k !== 'month') : ['value']
  
  return {
    type: detectedType,
    title,
    data,
    dataKeys,
    xAxisKey: 'name' in data[0] ? 'name' : 'month',
    description: extractDescription(content),
    confidence: Math.min(maxScore / 3, 1)
  }
}

const extractTitle = (content: string): string | null => {
  const patterns = [
    /\*\*(.+?)\*\*/,
    /# (.+)/,
    /gráfica?\s+(?:de|del|sobre)?\s*(.+)/i,
    /gráfico\s+(?:de|del|sobre)?\s*(.+)/i,
    /visualización\s+(?:de|del|sobre)?\s*(.+)/i,
    /(?:mostrar|ver|presentar)\s+(?:un[ao]?\s+)?(?:gráfica?|gráfico|visualización)\s+(?:de|del|sobre)?\s*(.+)/i
  ]
  
  for (const pattern of patterns) {
    const match = content.match(pattern)
    if (match && match[1]) {
      return match[1].trim()
    }
  }
  
  return null
}

const generateTitle = (type: ChartType): string => {
  const titles: Record<ChartType, string> = {
    line: 'Tendencia de Consumo',
    bar: 'Comparativa de Datos',
    pie: 'Distribución Porcentual',
    area: 'Evolución Acumulada',
    composed: 'Análisis Combinado',
    table: 'Resumen de Datos',
    scatter: 'Diagrama de Dispersión',
    heatmap: 'Mapa de Calor'
  }
  
  return titles[type]
}

const extractDataFromContent = (content: string, _context?: any): ChartDataPoint[] => {
  const data: ChartDataPoint[] = []
  
  // Find all table-like structures (lines starting with |)
  const lines = content.split('\n')
  const tableLines: string[] = []
  let inTable = false
  
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      // Check if it's a separator line (only contains |, -, :, spaces)
      const isSeparator = /^[\|\-\:\s]+$/.test(trimmed)
      if (!isSeparator) {
        tableLines.push(trimmed)
        inTable = true
      }
    } else if (inTable && !trimmed.startsWith('|')) {
      // End of table
      if (tableLines.length > 1) break
    }
  }
  
  // Parse table if we found data rows
  if (tableLines.length >= 2) {
    const headers = tableLines[0]
      .split('|')
      .filter(h => h.trim())
      .map(h => h.trim().toLowerCase()
        .replace(/\s*\(.*?\)\s*/g, '') // Remove units in parentheses
        .replace(/\s+/g, '_')
      )
    
    for (let i = 1; i < tableLines.length; i++) {
      const cells = tableLines[i].split('|').filter(c => c.trim())
      const row: ChartDataPoint = {}
      
      headers.forEach((header, idx) => {
        const cellValue = cells[idx]?.trim() || ''
        // Handle Spanish number format (1.234.567,89)
        const normalizedValue = cellValue
          .replace(/\./g, '')      // Remove thousands separator
          .replace(/,/g, '.')      // Convert decimal separator
          .replace(/[^\d.-]/g, '') // Keep only numbers, dots, minus
        const numValue = parseFloat(normalizedValue)
        
        if (!isNaN(numValue) && cellValue.match(/[\d]/)) {
          row[header] = numValue
        } else if (cellValue) {
          row[header] = cellValue
        }
      })
      
      // Only add row if it has at least one numeric value
      const hasNumeric = Object.values(row).some(v => typeof v === 'number')
      if (Object.keys(row).length > 0 && hasNumeric) {
        // Generate a name for the row if not present
        if (!row.name && !row.ubicación && !row.region) {
          const firstTextValue = Object.entries(row).find(([_, v]) => typeof v === 'string')
          if (firstTextValue) {
            row.name = firstTextValue[1] as string
          } else {
            row.name = `Item ${i}`
          }
        }
        data.push(row)
      }
    }
  }
  
  // Fallback: Try JSON extraction if no table data found
  if (data.length === 0) {
    const jsonMatch = content.match(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1])
        if (Array.isArray(parsed)) {
          data.push(...parsed)
        }
      } catch {}
    }
  }
  
  // Fallback: Try key-value patterns
  if (data.length === 0) {
    const keyValuePattern = /([^:\n]+)\s*:\s*([\d.,]+)\s*(?:m³|m3)?/g
    let match
    while ((match = keyValuePattern.exec(content)) !== null) {
      const key = match[1].trim().replace(/\*\*/g, '')
      const valueStr = match[2].replace(/\./g, '').replace(/,/g, '.')
      const value = parseFloat(valueStr)
      
      if (!isNaN(value) && value > 0) {
        data.push({ name: key, value })
      }
    }
  }
  
  return data.slice(0, 10) // Limit to 10 items for charts
}

const extractDescription = (content: string): string | undefined => {
  const sentences = content.split(/[.!?]/).filter(s => s.trim().length > 20)
  
  if (sentences.length > 0) {
    const description = sentences[0].trim()
    if (description.length > 10 && description.length < 200) {
      return description.replace(/\*\*/g, '')
    }
  }
  
  return undefined
}

export const createChartConfig = (parsed: ParsedChartData): Omit<ChartConfig, 'id' | 'createdAt'> => {
  return {
    title: parsed.title,
    type: parsed.type,
    data: parsed.data,
    dataKeys: parsed.dataKeys,
    xAxisKey: parsed.xAxisKey,
    colors: DEFAULT_COLORS,
    description: parsed.description,
    source: 'Generado por IA',
    isDeletable: true,
    size: parsed.type === 'table' ? 'medium' : 'medium'
  }
}

export const detectChartableContent = (content: string): boolean => {
  const hasNumbers = DATA_PATTERN.test(content)
  const hasChartKeywords = Object.values(CHART_INDICATORS).flat().some(kw => 
    content.toLowerCase().includes(kw)
  )
  const hasTable = content.includes('|') && content.includes('---')
  const hasJson = /```(?:json)?\s*\[/.test(content)
  
  return (hasNumbers && hasChartKeywords) || hasTable || hasJson
}

export const formatChartData = (
  data: any[],
  xKey: string,
  yKeys: string[],
  options?: {
    fillMissingMonths?: boolean
    sortBy?: 'name' | 'value' | 'date'
    limit?: number
  }
): ChartDataPoint[] => {
  let formatted = data.map(item => ({
    name: item[xKey] || item.name || item.month || '',
    ...yKeys.reduce((acc, key) => {
      acc[key] = item[key] ?? 0
      return acc
    }, {} as Record<string, any>)
  }))
  
  if (options?.sortBy === 'value') {
    formatted = formatted.sort((a, b) => ((b as any).value || 0) - ((a as any).value || 0))
  }
  
  if (options?.limit) {
    formatted = formatted.slice(0, options.limit)
  }
  
  return formatted
}

export const aggregateByPeriod = (
  data: any[],
  periodKey: string,
  valueKey: string,
  aggregation: 'sum' | 'avg' | 'max' = 'sum'
): ChartDataPoint[] => {
  const grouped: Record<string, number[]> = {}
  
  data.forEach(item => {
    const period = item[periodKey] || item.period || item.date
    if (!grouped[period]) {
      grouped[period] = []
    }
    grouped[period].push(item[valueKey] || 0)
  })
  
  return Object.entries(grouped).map(([period, values]) => {
    let aggregated: number
    switch (aggregation) {
      case 'avg':
        aggregated = values.reduce((a, b) => a + b, 0) / values.length
        break
      case 'max':
        aggregated = Math.max(...values)
        break
      default:
        aggregated = values.reduce((a, b) => a + b, 0)
    }
    return { name: period, value: aggregated }
  })
}
