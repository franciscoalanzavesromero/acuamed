import React, { useState, memo } from 'react'
import { Plus, BarChart3, TrendingUp, PieChart as PieChartIcon, Table, Loader2 } from 'lucide-react'
import { ChartConfig, ChartType, DEFAULT_COLORS } from '../types/charts'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

interface ChartPreviewProps {
  config: Omit<ChartConfig, 'id' | 'createdAt'>
  onAddToDashboard: () => void
  isAdding?: boolean
}

const TYPE_ICONS: Record<ChartType, React.ReactNode> = {
  bar: <BarChart3 size={16} />,
  line: <TrendingUp size={16} />,
  pie: <PieChartIcon size={16} />,
  area: <TrendingUp size={16} />,
  composed: <BarChart3 size={16} />,
  table: <Table size={16} />
}

const ChartPreview: React.FC<ChartPreviewProps> = memo(({
  config,
  onAddToDashboard,
  isAdding = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const renderChart = () => {
    if (!config.data || config.data.length === 0) {
      return (
        <div className="text-center text-muted py-4">
          <small>Sin datos para mostrar</small>
        </div>
      )
    }

    const commonProps = {
      data: config.data,
      margin: { top: 5, right: 15, left: 0, bottom: 5 }
    }

    const axisStyle = { fontSize: 10, fill: '#6c757d' }
    const tooltipStyle = {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      border: '1px solid #dee2e6',
      borderRadius: '0.25rem',
      fontSize: '0.75rem'
    }

    switch (config.type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={isExpanded ? 250 : 180}>
            <BarChart {...commonProps}>
              <XAxis dataKey={config.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} width={40} />
              <Tooltip contentStyle={tooltipStyle} />
              {config.dataKeys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={config.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  radius={[2, 2, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={isExpanded ? 250 : 180}>
            <LineChart {...commonProps}>
              <XAxis dataKey={config.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} width={40} />
              <Tooltip contentStyle={tooltipStyle} />
              {config.dataKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={config.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={isExpanded ? 250 : 180}>
            <PieChart>
              <Pie
                data={config.data}
                dataKey={config.dataKeys[0] || 'value'}
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={isExpanded ? 90 : 65}
                paddingAngle={2}
              >
                {config.data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={config.colors?.[index % (config.colors?.length || 1)] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend iconSize={8} />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={isExpanded ? 250 : 180}>
            <AreaChart {...commonProps}>
              <XAxis dataKey={config.xAxisKey || 'name'} tick={axisStyle} />
              <YAxis tick={axisStyle} width={40} />
              <Tooltip contentStyle={tooltipStyle} />
              {config.dataKeys.map((key, index) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={config.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  fill={config.colors?.[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                  fillOpacity={0.3}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'table':
        return (
          <div className="table-responsive" style={{ maxHeight: isExpanded ? '300px' : '180px' }}>
            <table className="table table-sm table-hover mb-0">
              <thead className="table-light sticky-top">
                <tr>
                  {Object.keys(config.data[0] || {}).map(key => (
                    <th key={key} scope="col" style={{ textTransform: 'capitalize', fontSize: '0.75rem' }}>
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {config.data.slice(0, isExpanded ? 20 : 5).map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {Object.values(row).map((value, colIndex) => (
                      <td key={colIndex} style={{ fontSize: '0.75rem' }}>
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
          <div className="text-center text-muted py-4">
            <small>Vista previa no disponible</small>
          </div>
        )
    }
  }

  return (
    <div className={`chart-preview ${isExpanded ? 'expanded' : ''}`}>
      <div className="chart-preview-header">
        <div className="d-flex align-items-center gap-2">
          <span className="chart-type-badge">
            {TYPE_ICONS[config.type]}
            <span className="text-capitalize ms-1">{config.type}</span>
          </span>
          <span className="chart-preview-title">{config.title}</span>
        </div>
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? 'Colapsar' : 'Expandir'}
        </button>
      </div>
      
      <div className="chart-preview-body">
        {renderChart()}
      </div>

      {config.description && (
        <div className="chart-preview-footer">
          <small className="text-muted">{config.description}</small>
        </div>
      )}

      <div className="chart-preview-actions">
        <button
          className="btn btn-primary btn-sm w-100"
          onClick={onAddToDashboard}
          disabled={isAdding}
        >
          {isAdding ? (
            <>
              <Loader2 size={14} className="me-1 spin" />
              Añadiendo...
            </>
          ) : (
            <>
              <Plus size={14} className="me-1" />
              Añadir al Dashboard
            </>
          )}
        </button>
      </div>
    </div>
  )
})

ChartPreview.displayName = 'ChartPreview'

export default ChartPreview
