import { useState, useEffect } from 'react'
import { FileSpreadsheet, CheckCircle, Clock, XCircle, RotateCcw, Trash } from 'lucide-react'
import { api } from '../services/api'

void api

interface UploadRecord {
  id: string
  filename: string
  file_size: number
  status: string
  rows_processed: number | null
  error_message: string | null
  created_at: string
}

export default function UploadHistory() {
  const [uploads, setUploads] = useState<UploadRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadUploads()
  }, [])

  const loadUploads = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/uploads`)
      if (response.ok) {
        const data = await response.json()
        setUploads(data.uploads || [])
      }
    } catch (error) {
      console.error('Error loading uploads:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = async (id: string) => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/uploads/${id}/retry`, {
        method: 'POST'
      })
      loadUploads()
    } catch (error) {
      console.error('Error retrying upload:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('¿Estás seguro de eliminar este registro?')) return
    
    try {
      await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/uploads/${id}`, {
        method: 'DELETE'
      })
      setUploads(uploads.filter(u => u.id !== id))
    } catch (error) {
      console.error('Error deleting upload:', error)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge bg-success"><CheckCircle size={12} className="me-1" /> Completado</span>
      case 'pending':
      case 'processing':
        return <span className="badge bg-warning text-dark"><Clock size={12} className="me-1" /> {status === 'processing' ? 'Procesando' : 'Pendiente'}</span>
      case 'failed':
        return <span className="badge bg-danger"><XCircle size={12} className="me-1" /> Error</span>
      default:
        return <span className="badge bg-secondary">{status}</span>
    }
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

  if (uploads.length === 0) {
    return (
      <div className="text-center py-5">
        <FileSpreadsheet size={64} className="text-muted mb-3" />
        <h4 className="text-muted">No hay archivos subidos</h4>
        <p className="text-muted">Sube un archivo Excel para comenzar el análisis</p>
      </div>
    )
  }

  return (
    <div className="data-table-container">
      <div className="table-header">
        <h4>
          <i className="bi bi-clock-history me-2"></i>
          Historial de Cargas ({uploads.length})
        </h4>
        <button className="btn btn-outline-primary btn-sm" onClick={loadUploads}>
          <i className="bi bi-arrow-clockwise me-1"></i> Actualizar
        </button>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Tamaño</th>
              <th>Estado</th>
              <th>Registros</th>
              <th>Fecha</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {uploads.map(upload => (
              <tr key={upload.id}>
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <FileSpreadsheet size={20} className="text-success" />
                    <span className="fw-medium">{upload.filename}</span>
                  </div>
                </td>
                <td>{formatFileSize(upload.file_size)}</td>
                <td>{getStatusBadge(upload.status)}</td>
                <td>
                  {upload.rows_processed !== null ? (
                    <span className="fw-bold">{upload.rows_processed.toLocaleString()}</span>
                  ) : (
                    <span className="text-muted">-</span>
                  )}
                </td>
                <td>{formatDate(upload.created_at)}</td>
                <td>
                  <div className="d-flex gap-1">
                    {upload.status === 'failed' && (
                      <button
                        className="btn btn-sm btn-outline-warning"
                        title="Reintentar"
                        onClick={() => handleRetry(upload.id)}
                      >
                        <RotateCcw size={14} />
                      </button>
                    )}
                    <button
                      className="btn btn-sm btn-outline-danger"
                      title="Eliminar"
                      onClick={() => handleDelete(upload.id)}
                    >
                      <Trash size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
