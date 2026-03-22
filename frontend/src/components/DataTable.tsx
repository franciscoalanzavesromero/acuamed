import { useState, useEffect } from 'react'
import { Search, Filter, Download } from 'lucide-react'

interface DataRow {
  id: string
  location: string
  period: string
  volume: number
  type: string
}

export default function DataTable() {
  const [data, setData] = useState<DataRow[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/consumption/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      
      if (response.ok) {
        const result = await response.json()
        if (result.period_summary) {
          const formattedData = result.period_summary.map((item: any, index: number) => ({
            id: `row-${index}`,
            location: item.consumption_type || 'Sin ubicación',
            period: `${new Date(item.period_start).toLocaleDateString('es-ES')} - ${new Date(item.period_end).toLocaleDateString('es-ES')}`,
            volume: item.total_volume_m3,
            type: item.consumption_type || 'General'
          }))
          setData(formattedData)
        }
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredData = data.filter(item =>
    item.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.type.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const totalPages = Math.ceil(filteredData.length / itemsPerPage)

  const formatVolume = (vol: number) => {
    return vol.toLocaleString('es-ES', { maximumFractionDigits: 2 }) + ' m³'
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
      <div className="data-table-container">
        <div className="table-header">
          <h4>
            <i className="bi bi-table me-2"></i>
            Registros de Consumo
          </h4>
          <div className="d-flex gap-2">
            <div className="input-group" style={{ width: '250px' }}>
              <span className="input-group-text bg-white">
                <Search size={16} />
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Buscar..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>
            <button className="btn btn-outline-secondary">
              <Filter size={16} className="me-1" /> Filtrar
            </button>
            <button className="btn btn-outline-success">
              <Download size={16} className="me-1" /> Exportar
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ubicación</th>
                <th>Período</th>
                <th>Volumen (m³)</th>
                <th>Tipo</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-4 text-muted">
                    No hay datos disponibles. Sube un archivo Excel para comenzar.
                  </td>
                </tr>
              ) : (
                paginatedData.map(row => (
                  <tr key={row.id}>
                    <td>
                      <span className="badge bg-light text-dark">
                        <i className="bi bi-geo-alt me-1"></i>
                        {row.location}
                      </span>
                    </td>
                    <td>{row.period}</td>
                    <td className="fw-bold">{formatVolume(row.volume)}</td>
                    <td>
                      <span className={`badge ${
                        row.type === 'domestico' ? 'bg-primary' :
                        row.type === 'industrial' ? 'bg-warning text-dark' :
                        'bg-secondary'
                      }`}>
                        {row.type}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="d-flex justify-content-between align-items-center p-3 border-top">
            <span className="text-muted small">
              Mostrando {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredData.length)} de {filteredData.length}
            </span>
            <nav>
              <ul className="pagination pagination-sm mb-0">
                <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                  <button className="page-link" onClick={() => setCurrentPage(p => p - 1)}>Anterior</button>
                </li>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = i + 1
                  return (
                    <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                      <button className="page-link" onClick={() => setCurrentPage(page)}>{page}</button>
                    </li>
                  )
                })}
                <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                  <button className="page-link" onClick={() => setCurrentPage(p => p + 1)}>Siguiente</button>
                </li>
              </ul>
            </nav>
          </div>
        )}
      </div>
    </div>
  )
}
