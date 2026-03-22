import { useState, useCallback, useEffect, useMemo } from 'react'
import { ChartConfig, DashboardState, ChartDataPoint, ChartSize } from '../types/charts'

const STORAGE_KEY_USER_CHARTS = 'acuamed_user_charts'
const STORAGE_KEY_CHART_ORDER = 'acuamed_chart_order'

const generateId = (): string => `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

const createDefaultCharts = (): ChartConfig[] => []

export interface UseDashboardReturn {
  defaultCharts: ChartConfig[]
  userCharts: ChartConfig[]
  allCharts: ChartConfig[]
  chartOrder: string[]
  isEditMode: boolean
  selectedChartId: string | null
  canUndo: boolean
  canRedo: boolean
  isLoading: boolean
  setEditMode: (mode: boolean) => void
  setSelectedChart: (id: string | null) => void
  addChart: (chart: Omit<ChartConfig, 'id' | 'createdAt'>) => string
  updateChart: (id: string, updates: Partial<ChartConfig>) => void
  deleteChart: (id: string) => void
  moveChart: (fromIndex: number, toIndex: number) => void
  updateChartOrder: (newOrder: string[]) => void
  updateChartData: (id: string, data: ChartDataPoint[]) => void
  updateChartTitle: (id: string, title: string) => void
  updateChartSize: (id: string, size: ChartSize) => void
  undo: () => void
  redo: () => void
  refreshChart: (id: string) => Promise<void>
  clearUserCharts: () => void
}

export const useDashboard = (): UseDashboardReturn => {
  const [defaultCharts] = useState<ChartConfig[]>(createDefaultCharts())
  const [userCharts, setUserCharts] = useState<ChartConfig[]>([])
  const [chartOrder, setChartOrder] = useState<string[]>([])
  const [isEditMode, setEditMode] = useState(false)
  const [selectedChartId, setSelectedChartId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [history, setHistory] = useState<{ past: DashboardState[], future: DashboardState[] }>({
    past: [],
    future: []
  })

  useEffect(() => {
    try {
      const storedUserCharts = localStorage.getItem(STORAGE_KEY_USER_CHARTS)
      const storedOrder = localStorage.getItem(STORAGE_KEY_CHART_ORDER)
      
      if (storedUserCharts) {
        const parsed = JSON.parse(storedUserCharts)
        setUserCharts(parsed.map((c: ChartConfig) => ({
          ...c,
          createdAt: new Date(c.createdAt)
        })))
      }
      
      if (storedOrder) {
        setChartOrder(JSON.parse(storedOrder))
      } else {
        const defaultIds = createDefaultCharts().map(c => c.id)
        const userIds = storedUserCharts ? JSON.parse(storedUserCharts).map((c: ChartConfig) => c.id) : []
        setChartOrder([...defaultIds, ...userIds])
      }
    } catch (error) {
      console.error('Error loading dashboard state:', error)
    }
  }, [])

  const saveUserCharts = useCallback((charts: ChartConfig[]) => {
    try {
      localStorage.setItem(STORAGE_KEY_USER_CHARTS, JSON.stringify(charts))
    } catch (error) {
      console.error('Error saving user charts:', error)
    }
  }, [])

  const saveChartOrder = useCallback((order: string[]) => {
    try {
      localStorage.setItem(STORAGE_KEY_CHART_ORDER, JSON.stringify(order))
    } catch (error) {
      console.error('Error saving chart order:', error)
    }
  }, [])

  const saveToHistory = useCallback((state: DashboardState) => {
    setHistory(prev => ({
      past: [...prev.past.slice(-19), state],
      future: []
    }))
  }, [])

  const currentState = useMemo((): DashboardState => ({
    defaultCharts,
    userCharts,
    chartOrder,
    isEditMode,
    selectedChartId,
    history: { past: [], future: [] }
  }), [defaultCharts, userCharts, chartOrder, isEditMode, selectedChartId])

  const addChart = useCallback((chartData: Omit<ChartConfig, 'id' | 'createdAt'>): string => {
    const newChart: ChartConfig = {
      ...chartData,
      id: generateId(),
      createdAt: new Date()
    }
    
    saveToHistory(currentState)
    setUserCharts(prev => {
      const updated = [...prev, newChart]
      saveUserCharts(updated)
      return updated
    })
    setChartOrder(prev => {
      const updated = [...prev, newChart.id]
      saveChartOrder(updated)
      return updated
    })
    
    return newChart.id
  }, [currentState, saveToHistory, saveUserCharts, saveChartOrder])

  const updateChart = useCallback((id: string, updates: Partial<ChartConfig>) => {
    saveToHistory(currentState)
    
    const isUserChart = userCharts.some(c => c.id === id)
    if (isUserChart) {
      setUserCharts(prev => {
        const updated = prev.map(c => c.id === id ? { ...c, ...updates } : c)
        saveUserCharts(updated)
        return updated
      })
    } else {
      defaultCharts.forEach((c) => {
        if (c.id === id) {
          Object.assign(c, updates)
        }
      })
    }
  }, [currentState, userCharts, defaultCharts, saveToHistory, saveUserCharts])

  const deleteChart = useCallback((id: string) => {
    const chart = userCharts.find(c => c.id === id)
    if (!chart?.isDeletable) return
    
    saveToHistory(currentState)
    setUserCharts(prev => {
      const updated = prev.filter(c => c.id !== id)
      saveUserCharts(updated)
      return updated
    })
    setChartOrder(prev => {
      const updated = prev.filter(oid => oid !== id)
      saveChartOrder(updated)
      return updated
    })
  }, [currentState, userCharts, saveToHistory, saveUserCharts, saveChartOrder])

  const moveChart = useCallback((fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    
    saveToHistory(currentState)
    setChartOrder(prev => {
      const newOrder = [...prev]
      const [moved] = newOrder.splice(fromIndex, 1)
      newOrder.splice(toIndex, 0, moved)
      saveChartOrder(newOrder)
      return newOrder
    })
  }, [currentState, saveToHistory, saveChartOrder])

  const updateChartOrder = useCallback((newOrder: string[]) => {
    saveToHistory(currentState)
    setChartOrder(newOrder)
    saveChartOrder(newOrder)
  }, [currentState, saveToHistory, saveChartOrder])

  const updateChartData = useCallback((id: string, data: ChartDataPoint[]) => {
    updateChart(id, { data })
  }, [updateChart])

  const updateChartTitle = useCallback((id: string, title: string) => {
    updateChart(id, { title })
  }, [updateChart])

  const updateChartSize = useCallback((id: string, size: ChartSize) => {
    updateChart(id, { size })
  }, [updateChart])

  const undo = useCallback(() => {
    if (history.past.length === 0) return
    
    const previousState = history.past[history.past.length - 1]
    setHistory(prev => ({
      past: prev.past.slice(0, -1),
      future: [currentState, ...prev.future]
    }))
    
    setUserCharts(previousState.userCharts)
    setChartOrder(previousState.chartOrder)
    saveUserCharts(previousState.userCharts)
    saveChartOrder(previousState.chartOrder)
  }, [history, currentState, saveUserCharts, saveChartOrder])

  const redo = useCallback(() => {
    if (history.future.length === 0) return
    
    const nextState = history.future[0]
    setHistory(prev => ({
      past: [...prev.past, currentState],
      future: prev.future.slice(1)
    }))
    
    setUserCharts(nextState.userCharts)
    setChartOrder(nextState.chartOrder)
    saveUserCharts(nextState.userCharts)
    saveChartOrder(nextState.chartOrder)
  }, [history, currentState, saveUserCharts, saveChartOrder])

  const refreshChart = useCallback(async () => {
    setIsLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearUserCharts = useCallback(() => {
    saveToHistory(currentState)
    setUserCharts([])
    setChartOrder(defaultCharts.map(c => c.id))
    saveUserCharts([])
    saveChartOrder(defaultCharts.map(c => c.id))
  }, [currentState, defaultCharts, saveToHistory, saveUserCharts, saveChartOrder])

  const allCharts = useMemo(() => {
    const chartsMap = new Map<string, ChartConfig>()
    
    defaultCharts.forEach(chart => {
      chartsMap.set(chart.id, chart)
    })
    
    userCharts.forEach(chart => {
      chartsMap.set(chart.id, chart)
    })
    
    return chartOrder
      .map(id => chartsMap.get(id))
      .filter((chart): chart is ChartConfig => chart !== undefined)
  }, [defaultCharts, userCharts, chartOrder])

  return {
    defaultCharts,
    userCharts,
    allCharts,
    chartOrder,
    isEditMode,
    selectedChartId,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
    isLoading,
    setEditMode,
    setSelectedChart: setSelectedChartId,
    addChart,
    updateChart,
    deleteChart,
    moveChart,
    updateChartOrder,
    updateChartData,
    updateChartTitle,
    updateChartSize,
    undo,
    redo,
    refreshChart,
    clearUserCharts
  }
}
