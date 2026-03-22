import { useState } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { Play, AlertCircle, TrendingUp, TrendingDown, Crosshair, Download } from 'lucide-react'

const PRESETS = [
  { id: 'severe_drought', name: 'Sequía Severa', icon: '🔥', color: '#dc3545' },
  { id: 'moderate_drought', name: 'Sequía Moderada', icon: '⚠️', color: '#ffc107' },
  { id: 'population_growth', name: 'Crecimiento Poblacional', icon: '👥', color: '#17a2b8' },
  { id: 'efficiency_improvement', name: 'Mejora de Eficiencia', icon: '⚡', color: '#28a745' },
  { id: 'best_case', name: 'Mejor Escenario', icon: '🌟', color: '#20c997' },
  { id: 'worst_case', name: 'Peor Escenario', icon: '⛔', color: '#6f42c1' }
]

export default function WhatIfSimulator() {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [months, setMonths] = useState(12)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [customScenario, setCustomScenario] = useState({
    drought_level: 0.3,
    demand_change: 0.1,
    population_change: 0.02
  })

  const runPresetSimulation = async (presetId: string) => {
    setLoading(true)
    setSelectedPreset(presetId)
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/simulation/preset/${presetId}?months=${months}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const data = await response.json()
        setResults(data)
      }
    } catch (error) {
      console.error('Simulation error:', error)
    } finally {
      setLoading(false)
    }
  }

  const runCustomSimulation = async () => {
    setLoading(true)
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/simulation/whatif`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_type: 'Simulación Personalizada',
          ...customScenario,
          months
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setResults(data)
      }
    } catch (error) {
      console.error('Simulation error:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical': return '#dc3545'
      case 'warning': return '#ffc107'
      case 'shortage': return '#fd7e14'
      case 'low': return '#17a2b8'
      default: return '#28a745'
    }
  }

  return (
    <div className="row g-4">
      <div className="col-12">
        <div className="chart-container">
          <div className="chart-header">
            <h4>
              <Crosshair size={20} className="me-2" />
              Simulador What-If
            </h4>
            <div className="d-flex gap-2 align-items-center">
              <label className="small text-muted">Período:</label>
              <select 
                className="form-select form-select-sm" 
                style={{ width: 'auto' }}
                value={months}
                onChange={e => setMonths(Number(e.target.value))}
              >
                <option value={6}>6 meses</option>
                <option value={12}>12 meses</option>
                <option value={24}>24 meses</option>
                <option value={36}>36 meses</option>
              </select>
            </div>
          </div>

          <div className="row g-3 mb-4">
            {PRESETS.map(preset => (
              <div key={preset.id} className="col-md-6 col-lg-4">
                <div 
                  className={`card h-100 ${selectedPreset === preset.id ? 'border-primary' : ''}`}
                  style={{ cursor: 'pointer', borderLeft: `4px solid ${preset.color}` }}
                  onClick={() => runPresetSimulation(preset.id)}
                >
                  <div className="card-body d-flex align-items-center gap-3">
                    <span style={{ fontSize: '1.5rem' }}>{preset.icon}</span>
                    <div>
                      <h6 className="mb-1">{preset.name}</h6>
                      <small className="text-muted">Clic para simular</small>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <hr />

          <h5 className="mb-3">Simulación Personalizada</h5>
          <div className="row g-3 mb-4">
            <div className="col-md-4">
              <label className="form-label small">
                Nivel de Sequía: {(customScenario.drought_level * 100).toFixed(0)}%
              </label>
              <input 
                type="range" 
                className="form-range"
                min="0" 
                max="1" 
                step="0.1"
                value={customScenario.drought_level}
                onChange={e => setCustomScenario(s => ({ ...s, drought_level: Number(e.target.value) }))}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label small">
                Cambio de Demanda: {(customScenario.demand_change * 100).toFixed(0)}%
              </label>
              <input 
                type="range" 
                className="form-range"
                min="-0.5" 
                max="1" 
                step="0.05"
                value={customScenario.demand_change}
                onChange={e => setCustomScenario(s => ({ ...s, demand_change: Number(e.target.value) }))}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label small">
                Crecimiento Poblacional: {(customScenario.population_change * 100).toFixed(0)}%
              </label>
              <input 
                type="range" 
                className="form-range"
                min="0" 
                max="0.5" 
                step="0.01"
                value={customScenario.population_change}
                onChange={e => setCustomScenario(s => ({ ...s, population_change: Number(e.target.value) }))}
              />
            </div>
          </div>
          <button 
            className="btn btn-primary"
            onClick={runCustomSimulation}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" />
                Simulando...
              </>
            ) : (
              <>
                <Play size={16} className="me-2" />
                Ejecutar Simulación
              </>
            )}
          </button>
        </div>
      </div>

      {results && (
        <>
          <div className="col-lg-8">
            <div className="chart-container">
              <div className="chart-header">
                <h4>Proyección de Volumen</h4>
                <span className="badge" style={{ backgroundColor: '#0d6efd' }}>
                  {results.scenario_type}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={results.projections}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                  <XAxis dataKey="month_name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px' }}
                    formatter={(value: number) => [`${value.toLocaleString()} m³`, 'Volumen']}
                  />
                  <Legend />
                  <ReferenceLine 
                    y={results.base_volume_m3} 
                    stroke="#dc3545" 
                    strokeDasharray="5 5"
                    label="Base"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="projected_volume_m3" 
                    stroke="#0d6efd" 
                    strokeWidth={3}
                    dot={(props: any) => {
                      const { cx, cy, payload } = props
                      return (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={6}
                          fill={getStatusColor(payload.status)}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      )
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="col-lg-4">
            <div className="chart-container h-100">
              <h5 className="mb-3">Resumen del Escenario</h5>
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-muted">Volumen Base:</span>
                  <strong>{results.base_volume_m3.toLocaleString()} m³</strong>
                </div>
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-muted">Nivel Sequía:</span>
                  <strong>{(results.drought_level * 100).toFixed(0)}%</strong>
                </div>
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-muted">Cambio Demanda:</span>
                  <strong>{(results.demand_change * 100).toFixed(0)}%</strong>
                </div>
                <div className="d-flex justify-content-between">
                  <span className="text-muted">Crecimiento Pobl.:</span>
                  <strong>{(results.population_change * 100).toFixed(0)}%</strong>
                </div>
              </div>

              <h6>Recomendaciones</h6>
              <ul className="list-unstyled">
                {results.recommendations?.map((rec: string, i: number) => (
                  <li key={i} className="mb-2 d-flex align-items-start gap-2">
                    <i className="bi bi-check-circle text-success mt-1"></i>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="col-12">
            <div className="chart-container">
              <h5 className="mb-3">Resumen Ejecutivo</h5>
              <div className="alert alert-info-custom">
                <p className="mb-0">{results.summary}</p>
              </div>
              
              <h6 className="mt-4 mb-3">Detalles Mensuales</h6>
              <div className="table-responsive">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th>Mes</th>
                      <th>Volumen Proyectado (m³)</th>
                      <th>Diferencia</th>
                      <th>Cambio %</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.projections?.map((p: any, i: number) => (
                      <tr key={i}>
                        <td>{p.month_name} {p.year}</td>
                        <td>{p.projected_volume_m3.toLocaleString()}</td>
                        <td className={p.difference_m3 >= 0 ? 'text-success' : 'text-danger'}>
                          {p.difference_m3 >= 0 ? '+' : ''}{p.difference_m3.toLocaleString()}
                        </td>
                        <td className={p.percent_change >= 0 ? 'text-success' : 'text-danger'}>
                          {p.percent_change >= 0 ? '+' : ''}{p.percent_change.toFixed(1)}%
                        </td>
                        <td>
                          <span 
                            className="badge"
                            style={{ backgroundColor: getStatusColor(p.status) }}
                          >
                            {p.status === 'critical' && <AlertCircle size={12} className="me-1" />}
                            {p.status === 'warning' && <AlertCircle size={12} className="me-1" />}
                            {p.status === 'normal' && <TrendingUp size={12} className="me-1" />}
                            {p.status === 'shortage' && <TrendingDown size={12} className="me-1" />}
                            {p.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
