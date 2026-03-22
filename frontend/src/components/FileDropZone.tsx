import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileSpreadsheet, CheckCircle, XCircle, ChevronRight } from 'lucide-react'
import { api } from '../services/api'

interface FileDropZoneProps {
  onUploadComplete?: () => void
}

interface UploadState {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  filename: string
  fileSize: number
  message: string
  uploadId?: string
}

export default function FileDropZone({ onUploadComplete }: FileDropZoneProps) {
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    filename: '',
    fileSize: 0,
    message: ''
  })

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploadState({
      status: 'uploading',
      progress: 0,
      filename: file.name,
      fileSize: file.size,
      message: 'Subiendo archivo...'
    })

    try {
      const progressInterval = setInterval(() => {
        setUploadState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }))
      }, 200)

      const result = await api.uploadFile(file)
      
      clearInterval(progressInterval)

      if (result.id) {
        setUploadState({
          status: 'processing',
          progress: 95,
          filename: file.name,
          fileSize: file.size,
          message: 'Procesando datos...',
          uploadId: result.id
        })

        const pollStatus = setInterval(async () => {
          try {
            const status = await api.getUploadStatus(result.id)
            if (status.status === 'completed') {
              clearInterval(pollStatus)
              setUploadState({
                status: 'completed',
                progress: 100,
                filename: file.name,
                fileSize: file.size,
                message: `Procesados ${status.rows_processed || 0} registros`,
                uploadId: result.id
              })
              onUploadComplete?.()
            } else if (status.status === 'failed') {
              clearInterval(pollStatus)
              setUploadState({
                status: 'error',
                progress: 0,
                filename: file.name,
                fileSize: file.size,
                message: status.error_message || 'Error en el procesamiento'
              })
            }
          } catch {
            clearInterval(pollStatus)
          }
        }, 1000)
      } else {
        throw new Error(result.detail || 'Error al subir archivo')
      }
    } catch (error: any) {
      setUploadState({
        status: 'error',
        progress: 0,
        filename: file.name,
        fileSize: file.size,
        message: error.message || 'Error al procesar el archivo'
      })
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: false,
    disabled: uploadState.status === 'uploading' || uploadState.status === 'processing'
  })

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const resetUpload = () => {
    setUploadState({
      status: 'idle',
      progress: 0,
      filename: '',
      fileSize: 0,
      message: ''
    })
  }

  if (uploadState.status === 'idle') {
    return (
      <div
        {...getRootProps()}
        className={`file-drop-zone ${isDragActive ? 'dragover' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="drop-icon">
          <UploadCloud size={64} />
        </div>
        <h3 className="drop-zone-title">
          {isDragActive ? 'Suelta el archivo aquí' : 'Arrastra tu archivo Excel'}
        </h3>
        <p className="drop-zone-subtitle">
          Formatos aceptados: .xlsx, .xls
        </p>
        <button className="btn btn-primary mt-3">
          <i className="bi bi-folder2-open me-2"></i>
          Seleccionar archivo
        </button>
        <div className="mt-4 pt-3 border-top">
          <p className="text-muted small mb-2">Estructura esperada del archivo:</p>
          <div className="d-flex gap-2 justify-content-center flex-wrap">
            <span className="badge bg-light text-dark">Hoja: GesMed</span>
            <span className="badge bg-light text-dark">Hoja: Ubicaciones</span>
            <span className="badge bg-light text-dark">Hoja: Volumenes</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="file-preview">
      <div className="file-info">
        <div className="file-icon">
          <FileSpreadsheet size={28} />
        </div>
        <div className="file-details">
          <h4>{uploadState.filename}</h4>
          <span>{formatFileSize(uploadState.fileSize)}</span>
        </div>
        {uploadState.status === 'completed' && (
          <CheckCircle size={24} className="ms-auto" style={{ color: '#198754' }} />
        )}
        {uploadState.status === 'error' && (
          <XCircle size={24} className="ms-auto" style={{ color: '#dc3545' }} />
        )}
      </div>

      <div className="upload-progress">
        <div className="d-flex justify-content-between mb-1">
          <span className="small">{uploadState.message}</span>
          <span className="small fw-bold">{uploadState.progress}%</span>
        </div>
        <div className="progress-bar-container">
          <div 
            className="progress-bar-fill"
            style={{ width: `${uploadState.progress}%` }}
          ></div>
        </div>
      </div>

      {uploadState.status === 'completed' && (
        <div className="mt-4 d-flex gap-2 justify-content-center">
          <button className="btn btn-success" onClick={resetUpload}>
            <i className="bi bi-plus-lg me-2"></i>
            Subir otro archivo
          </button>
          <button 
            className="btn btn-primary"
            onClick={onUploadComplete}
          >
            Ver datos <ChevronRight size={16} className="ms-2" />
          </button>
        </div>
      )}

      {uploadState.status === 'error' && (
        <div className="mt-4">
          <div className="alert alert-danger d-flex align-items-center" role="alert">
            <XCircle size={20} className="me-2" />
            <div>{uploadState.message}</div>
          </div>
          <button className="btn btn-outline-primary" onClick={resetUpload}>
            <i className="bi bi-arrow-counterclockwise me-2"></i>
            Intentar de nuevo
          </button>
        </div>
      )}

      {uploadState.status === 'processing' && (
        <div className="mt-3 text-center">
          <div className="spinner-border spinner-border-sm text-primary me-2" role="status">
            <span className="visually-hidden">Procesando...</span>
          </div>
          <span className="small text-muted">El sistema está analizando tu archivo...</span>
        </div>
      )}
    </div>
  )
}
