import { useState, useCallback } from 'react'
import { Plus, BarChart3 } from 'lucide-react'
import ChartGrid from './ChartGrid'
import ChartConfigModal from './ChartConfigModal'
import { ChartConfig } from '../types/charts'
import { UseDashboardReturn } from '../hooks/useDashboard'

interface DashboardProps {
  dashboard: UseDashboardReturn
  onAddChart?: (chart: Omit<ChartConfig, 'id' | 'createdAt'>) => void
}

export default function Dashboard({ dashboard }: DashboardProps) {
  const {
    allCharts,
    isEditMode,
    selectedChartId,
    canUndo,
    canRedo,
    setEditMode,
    setSelectedChart,
    addChart,
    deleteChart,
    updateChartOrder,
    updateChartTitle,
    updateChartSize,
    refreshChart
  } = dashboard

  const [showModal, setShowModal] = useState(false)

  const handleCreateChart = useCallback((config: Omit<ChartConfig, 'id' | 'createdAt'>) => {
    addChart(config)
  }, [addChart])

  return (
    <div className="dashboard-container">
      <div className="dashboard-header mb-4">
        <div>
          <h2 className="mb-1">Dashboard</h2>
          <p className="text-muted mb-0">Personaliza tu dashboard con gráficas del asistente IA</p>
        </div>
        <div className="d-flex gap-2">
          {isEditMode && (
            <button
              className="btn btn-primary"
              onClick={() => setShowModal(true)}
            >
              <Plus size={18} className="me-2" />
              Nueva Gráfica
            </button>
          )}
        </div>
      </div>

      {allCharts.length === 0 ? (
        <div className="dashboard-empty">
          <div className="empty-state">
            <div className="empty-icon">
              <BarChart3 size={64} strokeWidth={1} />
            </div>
            <h3>Tu dashboard está vacío</h3>
            <p className="text-muted">
              Usa el asistente de IA para generar gráficas personalizadas.<br />
              Las gráficas que generes aparecerán aquí.
            </p>
            <div className="d-flex gap-2 justify-content-center flex-wrap">
              <span className="badge bg-light text-dark p-2">Líneas</span>
              <span className="badge bg-light text-dark p-2">Barras</span>
              <span className="badge bg-light text-dark p-2">Tortas</span>
              <span className="badge bg-light text-dark p-2">Área</span>
              <span className="badge bg-light text-dark p-2">Tablas</span>
            </div>
          </div>
        </div>
      ) : (
        <ChartGrid
          charts={allCharts}
          isEditMode={isEditMode}
          selectedChartId={selectedChartId}
          canUndo={canUndo}
          canRedo={canRedo}
          onSelectChart={setSelectedChart}
          onUpdateChartOrder={updateChartOrder}
          onDeleteChart={deleteChart}
          onUpdateChartTitle={updateChartTitle}
          onUpdateChartSize={updateChartSize}
          onRefreshChart={refreshChart}
          onUndo={() => {}}
          onRedo={() => {}}
          onToggleEditMode={() => setEditMode(!isEditMode)}
        />
      )}

      <ChartConfigModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSave={handleCreateChart}
        title="Crear Nueva Gráfica"
      />
    </div>
  )
}
