import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Droplet, TrendingUp, AlertCircle, MapPin } from 'lucide-react'

const COLORS = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6f42c1']

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalRecords: 0,
    totalVolume: 0,
    anomalies: 0,
    locations: 0
  })
  const [chartData, setChartData] = useState<any>({ volume: [], trend: [], distribution: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/consumption/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.period_summary) {
          const volumeData = data.period_summary.slice(0, 12).map((item: any) => ({
            name: new Date(item.period_start).toLocaleDateString('es-ES', { month: 'short' }),
            volume: item.total_volume_m3 / 1000000
          }))
          
          setChartData({
            volume: volumeData,
            trend: volumeData,
            distribution: [
              { name: 'Enero', value: 25 },
              { name: 'Febrero', value: 20 },
              { name: 'Marzo', value: 22 },
              { name: 'Abril', value: 18 },
              { name: 'Mayo', value: 15 }
            ]
          })
          
          const total = data.period_summary.reduce((acc: number, item: any) => acc + item.total_volume_m3, 0)
          setStats({
            totalRecords: data.total_records,
            totalVolume: total,
            anomalies: 0,
            locations: 0
          })
        }
      }
    } catch (error) {
      console.error('Error loading dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  const formatVolume = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(2) + ' Mm³'
    if (num >= 1000) return (num / 1000).toFixed(2) + ' Km³'
    return num.toFixed(2) + ' m³'
  }

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '50vh' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Cargando...</span>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="row g-4 mb-4">
        <div className="col-md-6 col-lg-3">
          <div className="stat-card">
            <div className="icon blue">
              <Droplet size={24} />
            </div>
            <h3>{formatNumber(stats.totalRecords)}</h3>
            <p>Registros hídricos</p>
          </div>
        </div>
        <div className="col-md-6 col-lg-3">
          <div className="stat-card">
            <div className="icon green">
              <TrendingUp size={24} />
            </div>
            <h3>{formatVolume(stats.totalVolume)}</h3>
            <p>Volumen total procesado</p>
          </div>
        </div>
        <div className="col-md-6 col-lg-3">
          <div className="stat-card">
            <div className="icon red">
              <AlertCircle size={24} />
            </div>
            <h3>{stats.anomalies}</h3>
            <p>Anomalías detectadas</p>
          </div>
        </div>
        <div className="col-md-6 col-lg-3">
          <div className="stat-card">
            <div className="icon orange">
              <MapPin size={24} />
            </div>
            <h3>{stats.locations}</h3>
            <p>Ubicaciones activas</p>
          </div>
        </div>
      </div>

      <div className="row g-4">
        <div className="col-lg-8">
          <div className="chart-container">
            <div className="chart-header">
              <h4>Volumen por Mes (Mm³)</h4>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData.volume}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
                  formatter={(value: number) => [`${value.toFixed(2)} Mm³`, 'Volumen']}
                />
                <Bar dataKey="volume" fill="#0d6efd" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="col-lg-4">
          <div className="chart-container">
            <div className="chart-header">
              <h4>Distribución</h4>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData.distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {chartData.distribution.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="col-12">
          <div className="chart-container">
            <div className="chart-header">
              <h4>Tendencia de Consumo</h4>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="volume" 
                  stroke="#198754" 
                  strokeWidth={2}
                  dot={{ fill: '#198754', strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
