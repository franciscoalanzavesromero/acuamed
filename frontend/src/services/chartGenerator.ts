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
  table: ['detalle', 'lista', 'registro', 'tabla', 'completo']
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
    table: 'Resumen de Datos'
  }
  
  return titles[type]
}

const extractDataFromContent = (content: string, _context?: any): ChartDataPoint[] => {
  const data: ChartDataPoint[] = []
  
  const tablePattern = /[|].+[|]\n[|][-|:]+[|]([\s\S]*?)(?=\n\n|$)/
  const tableMatch = content.match(tablePattern)
  
  if (tableMatch) {
    const lines = tableMatch[0].split('\n').filter(line => line.trim() && !line.includes('---'))
    
    if (lines.length > 1) {
      const headers = lines[0].split('|').filter(h => h.trim()).map(h => h.trim().toLowerCase())
      
      for (let i = 1; i < lines.length; i++) {
        const cells = lines[i].split('|').filter(c => c.trim())
        const row: ChartDataPoint = {}
        
        headers.forEach((header, idx) => {
          const cellValue = cells[idx]?.trim() || ''
          const numValue = parseFloat(cellValue.replace(/[.,]/g, '.'))
          row[header] = isNaN(numValue) ? cellValue : numValue
        })
        
        if (Object.keys(row).length > 0) {
          data.push(row)
        }
      }
    }
  }
  
  const jsonMatch = content.match(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/)
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1])
      if (Array.isArray(parsed)) {
        data.push(...parsed)
      }
    } catch {}
  }
  
  const keyValuePattern = /(\w+)\s*:\s*([\d.,]+)/g
  let match
  while ((match = keyValuePattern.exec(content)) !== null) {
    const key = match[1].toLowerCase()
    const value = parseFloat(match[2].replace(/,/g, '.'))
    
    if (!isNaN(value)) {
      const existing = data.find(d => d.name === key || d.month === key)
      if (existing) {
        existing.value = value
      } else {
        data.push({ name: key, value })
      }
    }
  }
  
  return data
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
