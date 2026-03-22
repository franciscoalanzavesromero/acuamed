import React, { useState, useCallback, memo } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, ComposedChart, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ZAxis
} from 'recharts'
import { Trash2, GripVertical, RefreshCw, Maximize2, MoreVertical, Edit2, Check, X, Download, FileImage, FileText } from 'lucide-react'
import { ChartConfig, ChartSize, DEFAULT_COLORS } from '../types/charts'
import { exportChartToPNG, exportChartToPDF } from '../services/chartExport'

interface ChartWidgetProps {
  chart: ChartConfig
  isEditMode: boolean
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
  onUpdateTitle: (title: string) => void
  onRefresh: () => void
  onResize?: (size: ChartSize) => void
}

const SIZE_HEIGHTS: Record<ChartSize, number> = {
  small: 200,
  medium: 300,
  large: 400
}

const ChartWidget: React.FC<ChartWidgetProps> = memo(({
  chart,
  isEditMode,
  isSelected,
  onSelect,
  onDelete,
  onUpdateTitle,
  onRefresh,
  onResize
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState(chart.title)
  const [showMenu, setShowMenu] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const handleTitleSubmit = useCallback(() => {
    if (editedTitle.trim() && editedTitle !== chart.title) {
      onUpdateTitle(editedTitle.trim())
    }
    setIsEditing(false)
  }, [editedTitle, chart.title, onUpdateTitle])

  const handleTitleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTitleSubmit()
    } else if (e.key === 'Escape') {
      setEditedTitle(chart.title)
      setIsEditing(false)
    }
  }, [handleTitleSubmit, chart.title])

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    await onRefresh()
    setTimeout(() => setIsRefreshing(false), 500)
  }, [onRefresh])

  const handleDelete = useCallback(() => {
    setIsDeleting(true)
    setTimeout(() => {
      onDelete()
    }, 200)
  }, [onDelete])

  const handleExportPNG = useCallback(async () => {
    setIsExporting(true)
    setShowMenu(false)
    try {
      const chartId = `chart-${chart.id}`
      await exportChartToPNG(chartId, `${chart.title.replace(/\s+/g, '_')}.png`)
    } catch (error) {
      console.error('Error exporting PNG:', error)
    } finally {
      setIsExporting(false)
    }
  }, [chart.id, chart.title])

  const handleExportPDF = useCallback(async () => {
    setIsExporting(true)
    setShowMenu(false)
    try {
      const chartId = `chart-${chart.id}`
      await exportChartToPDF(chartId, `${chart.title.replace(/\s+/g, '_')}.pdf`)
    } catch (error) {
      console.error('Error exporting PDF:', error)
    } finally {
      setIsExporting(false)
    }
  }, [chart.id, chart.title])

  const renderChart = () => {
    if (!chart.data || chart.data.length === 0) {
      return (
        <div className="d-flex align-items-center justify-content-center h-100 text-muted">
          <span>Sin datos disponibles</span>
        </div>
      )
    }

    const commonProps = {
      data: chart.data,
      margin: { top: 10, right: 30, left: 0, bottom: 0 }
    }

    const axisStyle = { fontSize: 11, fill: '#6c757d' }
    const tooltipStyle = {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      border: '1px solid #dee2e6',
      borderRadius: '0.375rem'
    }

    switch (chart.type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey={chart.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              {chart.dataKeys.length > 1 && <Legend />}
              {chart.dataKeys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey={chart.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              {chart.dataKeys.length > 1 && <Legend />}
              {chart.dataKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3, fill: chart.colors?.[index] }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chart.data}
                dataKey={chart.dataKeys[0] || 'value'}
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={chart.size === 'small' ? 70 : 100}
                paddingAngle={2}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {chart.data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={chart.colors?.[index % (chart.colors?.length || 1)] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey={chart.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              {chart.dataKeys.map((key, index) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  fill={chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  fillOpacity={0.3}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'composed':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey={chart.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              {chart.dataKeys.map((key, index) => {
                const color = chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]
                if (index === 0) {
                  return <Bar key={key} dataKey={key} fill={color} radius={[4, 4, 0, 0]} />
                }
                return <Line key={key} type="monotone" dataKey={key} stroke={color} strokeWidth={2} />
              })}
            </ComposedChart>
          </ResponsiveContainer>
        )

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey={chart.xAxisKey || 'x'} tick={axisStyle} name="X" />
              <YAxis dataKey={chart.dataKeys[0] || 'y'} tick={axisStyle} name="Y" />
              <ZAxis range={[50]} />
              <Tooltip contentStyle={tooltipStyle} />
              {chart.dataKeys.length > 1 && <Legend />}
              {chart.dataKeys.map((key, index) => (
                <Scatter
                  key={key}
                  name={key}
                  data={chart.data}
                  fill={chart.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        )

      case 'heatmap':
        // Heatmap rendered as a grid with color intensity
        return (
          <div className="heatmap-container h-100">
            <div className="heatmap-grid" style={{ 
              display: 'grid', 
              gridTemplateColumns: `repeat(${Math.min(chart.data.length, 5)}, 1fr)`,
              gap: '4px',
              height: '100%',
              padding: '10px'
            }}>
              {chart.data.map((item, index) => {
                const value = item[chart.dataKeys[0]] as number || 0
                const maxValue = Math.max(...chart.data.map(d => (d[chart.dataKeys[0]] as number) || 0))
                const intensity = maxValue > 0 ? value / maxValue : 0
                const hue = 200 - (intensity * 200) // Blue to Red
                
                return (
                  <div
                    key={index}
                    className="heatmap-cell"
                    style={{
                      backgroundColor: `hsl(${hue}, 70%, ${50 + (1 - intensity) * 30}%)`,
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      color: intensity > 0.5 ? '#fff' : '#333',
                      fontWeight: 500
                    }}
                    title={`${item.name || index}: ${value.toLocaleString('es-ES')}`}
                  >
                    {typeof value === 'number' ? value.toLocaleString('es-ES', { maximumFractionDigits: 0 }) : value}
                  </div>
                )
              })}
            </div>
          </div>
        )

      case 'table':
        return (
          <div className="table-responsive h-100">
            <table className="table table-sm table-hover mb-0">
              <thead className="table-light">
                <tr>
                  {Object.keys(chart.data[0] || {}).map(key => (
                    <th key={key} scope="col" style={{ textTransform: 'capitalize' }}>
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chart.data.slice(0, 10).map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {Object.values(row).map((value, colIndex) => (
                      <td key={colIndex}>
                        {typeof value === 'number' ? value.toLocaleString('es-ES') : value}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )

      default:
        return (
          <div className="d-flex align-items-center justify-content-center h-100 text-muted">
            <span>Tipo de gráfica no soportado</span>
          </div>
        )
    }
  }

  return (
    <div
      id={`chart-${chart.id}`}
      className={`chart-widget ${isSelected ? 'selected' : ''} ${isDeleting ? 'deleting' : ''}`}
      style={{ height: SIZE_HEIGHTS[chart.size] }}
      onClick={onSelect}
    >
      <div className="chart-widget-header">
        <div className="chart-widget-title-area">
          {isEditMode && (
            <span className="drag-handle">
              <GripVertical size={16} />
            </span>
          )}
          {isEditing ? (
            <div className="input-group input-group-sm">
              <input
                type="text"
                className="form-control"
                value={editedTitle}
                onChange={e => setEditedTitle(e.target.value)}
                onKeyDown={handleTitleKeyDown}
                onBlur={handleTitleSubmit}
                autoFocus
              />
              <button
                className="btn btn-outline-success btn-sm"
                onClick={handleTitleSubmit}
              >
                <Check size={14} />
              </button>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => {
                  setEditedTitle(chart.title)
                  setIsEditing(false)
                }}
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <h6
              className="chart-widget-title mb-0"
              onDoubleClick={() => setIsEditing(true)}
            >
              {chart.title}
            </h6>
          )}
        </div>
        <div className="chart-widget-actions">
          {isEditMode && (
            <>
              <button
                className="btn btn-sm btn-outline-secondary"
                onClick={e => { e.stopPropagation(); handleRefresh(); }}
                disabled={isRefreshing}
                title="Actualizar"
              >
                <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
              </button>
              <div className="dropdown">
                <button
                  className="btn btn-sm btn-outline-secondary"
                  onClick={e => { e.stopPropagation(); setShowMenu(!showMenu); }}
                  title="Más opciones"
                >
                  <MoreVertical size={14} />
                </button>
                {showMenu && (
                  <div className="dropdown-menu show">
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); setIsEditing(true); setShowMenu(false); }}
                    >
                      <Edit2 size={14} className="me-2" />
                      Editar título
                    </button>
                    <div className="dropdown-divider" />
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); handleExportPNG(); }}
                      disabled={isExporting}
                    >
                      <FileImage size={14} className="me-2" />
                      Exportar PNG
                    </button>
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); handleExportPDF(); }}
                      disabled={isExporting}
                    >
                      <FileText size={14} className="me-2" />
                      Exportar PDF
                    </button>
                    <div className="dropdown-divider" />
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); onResize?.('small'); setShowMenu(false); }}
                    >
                      <Maximize2 size={14} className="me-2" />
                      Tamaño pequeño
                    </button>
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); onResize?.('medium'); setShowMenu(false); }}
                    >
                      <Maximize2 size={14} className="me-2" />
                      Tamaño medio
                    </button>
                    <button
                      className="dropdown-item"
                      onClick={e => { e.stopPropagation(); onResize?.('large'); setShowMenu(false); }}
                    >
                      <Maximize2 size={14} className="me-2" />
                      Tamaño grande
                    </button>
                    {chart.isDeletable && (
                      <>
                        <div className="dropdown-divider" />
                        <button
                          className="dropdown-item text-danger"
                          onClick={e => { e.stopPropagation(); handleDelete(); setShowMenu(false); }}
                        >
                          <Trash2 size={14} className="me-2" />
                          Eliminar
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      <div className="chart-widget-body">
        {renderChart()}
      </div>
      {chart.description && (
        <div className="chart-widget-footer">
          <small className="text-muted">{chart.description}</small>
        </div>
      )}
    </div>
  )
})

ChartWidget.displayName = 'ChartWidget'

export default ChartWidget
