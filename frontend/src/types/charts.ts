export type ChartType = 'line' | 'bar' | 'pie' | 'area' | 'composed' | 'table' | 'scatter' | 'heatmap'
export type ChartSize = 'small' | 'medium' | 'large'

export interface ChartDataPoint {
  [key: string]: string | number | null
}

export interface ChartConfig {
  id: string
  title: string
  type: ChartType
  data: ChartDataPoint[]
  dataKeys: string[]
  xAxisKey?: string
  colors?: string[]
  description?: string
  source?: string
  createdAt: Date
  isDeletable: boolean
  size: ChartSize
}

export interface ChartGenerationRequest {
  content: string
  context?: any
}

export interface GeneratedChart {
  config: ChartConfig
  previewHtml?: string
  confidence: number
  reasoning: string
}

export interface DashboardState {
  defaultCharts: ChartConfig[]
  userCharts: ChartConfig[]
  chartOrder: string[]
  isEditMode: boolean
  selectedChartId: string | null
  history: {
    past: DashboardState[]
    future: DashboardState[]
  }
}

export interface ChartGridItem {
  id: string
  chart: ChartConfig
  gridArea?: string
}

export const DEFAULT_COLORS = [
  '#0d6efd',
  '#198754',
  '#ffc107',
  '#dc3545',
  '#0dcaf0',
  '#6f42c1',
  '#20c997',
  '#e83e8c'
]

export const SIZE_DIMENSIONS: Record<ChartSize, { width: number; height: number }> = {
  small: { width: 100, height: 200 },
  medium: { width: 100, height: 300 },
  large: { width: 100, height: 400 }
}
