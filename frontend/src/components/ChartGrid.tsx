import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Undo2, Redo2, Edit3, Check, X, AlertTriangle } from 'lucide-react'
import ChartWidget from './ChartWidget'
import { ChartConfig, ChartSize } from '../types/charts'

interface ChartGridProps {
  charts: ChartConfig[]
  isEditMode: boolean
  selectedChartId: string | null
  canUndo: boolean
  canRedo: boolean
  onSelectChart: (id: string | null) => void
  onUpdateChartOrder: (newOrder: string[]) => void
  onDeleteChart: (id: string) => void
  onUpdateChartTitle: (id: string, title: string) => void
  onUpdateChartSize: (id: string, size: ChartSize) => void
  onRefreshChart: (id: string) => void
  onUndo: () => void
  onRedo: () => void
  onToggleEditMode: () => void
}

const ChartGrid: React.FC<ChartGridProps> = ({
  charts,
  isEditMode,
  selectedChartId,
  canUndo,
  canRedo,
  onSelectChart,
  onUpdateChartOrder,
  onDeleteChart,
  onUpdateChartTitle,
  onUpdateChartSize,
  onRefreshChart,
  onUndo,
  onRedo,
  onToggleEditMode
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (gridRef.current && !gridRef.current.contains(e.target as Node)) {
        onSelectChart(null)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onSelectChart])

  const handleDragStart = useCallback((e: React.DragEvent, index: number) => {
    setDraggedIndex(index)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
    
    const target = e.target as HTMLElement
    setTimeout(() => {
      target.style.opacity = '0.5'
    }, 0)
  }, [])

  const handleDragEnd = useCallback((e: React.DragEvent) => {
    const target = e.target as HTMLElement
    target.style.opacity = '1'
    setDraggedIndex(null)
    setDragOverIndex(null)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (index !== draggedIndex) {
      setDragOverIndex(index)
    }
  }, [draggedIndex])

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, dropIndex: number) => {
    e.preventDefault()
    if (draggedIndex !== null && draggedIndex !== dropIndex) {
      const newOrder = [...charts.map(c => c.id)]
      const [moved] = newOrder.splice(draggedIndex, 1)
      newOrder.splice(dropIndex, 0, moved)
      onUpdateChartOrder(newOrder)
    }
    setDraggedIndex(null)
    setDragOverIndex(null)
  }, [draggedIndex, charts, onUpdateChartOrder])

  const handleDeleteClick = useCallback((id: string) => {
    setDeleteConfirm(id)
  }, [])

  const confirmDelete = useCallback(() => {
    if (deleteConfirm) {
      onDeleteChart(deleteConfirm)
      setDeleteConfirm(null)
    }
  }, [deleteConfirm, onDeleteChart])

  const getChartColumns = (chart: ChartConfig): string => {
    switch (chart.size) {
      case 'small':
        return 'span 1'
      case 'large':
        return 'span 2'
      default:
        return 'span 1'
    }
  }

  return (
    <div className="chart-grid-container" ref={gridRef}>
      <div className="chart-grid-toolbar">
        <div className="d-flex align-items-center gap-2">
          {isEditMode ? (
            <>
              <button
                className="btn btn-sm btn-outline-secondary"
                onClick={onToggleEditMode}
                title="Salir del modo edición"
              >
                <Check size={16} className="me-1" />
                Guardar
              </button>
              <div className="btn-group">
                <button
                  className="btn btn-sm btn-outline-secondary"
                  onClick={onUndo}
                  disabled={!canUndo}
                  title="Deshacer"
                >
                  <Undo2 size={16} />
                </button>
                <button
                  className="btn btn-sm btn-outline-secondary"
                  onClick={onRedo}
                  disabled={!canRedo}
                  title="Rehacer"
                >
                  <Redo2 size={16} />
                </button>
              </div>
              <span className="text-muted small">
                Arrastra las gráficas para reordenarlas
              </span>
            </>
          ) : (
            <button
              className="btn btn-sm btn-outline-primary"
              onClick={onToggleEditMode}
              title="Editar dashboard"
            >
              <Edit3 size={16} className="me-1" />
              Editar
            </button>
          )}
        </div>
        <div className="text-muted small">
          {charts.length} gráfica{charts.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="chart-grid">
        {charts.map((chart, index) => (
          <div
            key={chart.id}
            className={`chart-grid-item ${draggedIndex === index ? 'dragging' : ''} ${dragOverIndex === index ? 'drag-over' : ''}`}
            draggable={isEditMode}
            onDragStart={e => handleDragStart(e, index)}
            onDragEnd={handleDragEnd}
            onDragOver={e => handleDragOver(e, index)}
            onDragLeave={handleDragLeave}
            onDrop={e => handleDrop(e, index)}
            style={{
              gridColumn: getChartColumns(chart)
            }}
          >
            <ChartWidget
              chart={chart}
              isEditMode={isEditMode}
              isSelected={selectedChartId === chart.id}
              onSelect={() => onSelectChart(chart.id)}
              onDelete={() => handleDeleteClick(chart.id)}
              onUpdateTitle={title => onUpdateChartTitle(chart.id, title)}
              onRefresh={() => onRefreshChart(chart.id)}
              onResize={size => onUpdateChartSize(chart.id, size)}
            />
          </div>
        ))}
      </div>

      {deleteConfirm && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-sm modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  <AlertTriangle size={20} className="text-warning me-2" />
                  Confirmar eliminación
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setDeleteConfirm(null)}
                />
              </div>
              <div className="modal-body">
                <p>¿Estás seguro de que deseas eliminar esta gráfica?</p>
                <p className="text-muted small mb-0">Esta acción no se puede deshacer.</p>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setDeleteConfirm(null)}
                >
                  <X size={16} className="me-1" />
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={confirmDelete}
                >
                  <Check size={16} className="me-1" />
                  Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChartGrid
