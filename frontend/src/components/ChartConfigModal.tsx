import React, { useState, useCallback, useEffect } from 'react'
import { X, Plus, Trash2, Palette } from 'lucide-react'
import { ChartConfig, ChartType, ChartSize, ChartDataPoint, DEFAULT_COLORS } from '../types/charts'

interface ChartConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (config: Omit<ChartConfig, 'id' | 'createdAt'>) => void
  initialConfig?: Partial<ChartConfig>
  title: string
}

const CHART_TYPES: { value: ChartType; label: string; icon: string }[] = [
  { value: 'bar', label: 'Barras', icon: '📊' },
  { value: 'line', label: 'Líneas', icon: '📈' },
  { value: 'pie', label: 'Torta', icon: '🥧' },
  { value: 'area', label: 'Área', icon: '📉' },
  { value: 'composed', label: 'Combinado', icon: '📊📈' },
  { value: 'table', label: 'Tabla', icon: '📋' }
]

const SIZE_OPTIONS: { value: ChartSize; label: string }[] = [
  { value: 'small', label: 'Pequeño' },
  { value: 'medium', label: 'Mediano' },
  { value: 'large', label: 'Grande' }
]

const ChartConfigModal: React.FC<ChartConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialConfig,
  title
}) => {
  const [config, setConfig] = useState({
    title: initialConfig?.title || '',
    type: initialConfig?.type || 'bar',
    dataKeys: initialConfig?.dataKeys || ['value'],
    xAxisKey: initialConfig?.xAxisKey || 'name',
    colors: initialConfig?.colors || DEFAULT_COLORS,
    description: initialConfig?.description || '',
    size: initialConfig?.size || 'medium'
  })
  
  const [dataInput, setDataInput] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)

  useEffect(() => {
    if (initialConfig?.data) {
      setDataInput(JSON.stringify(initialConfig.data, null, 2))
    }
  }, [initialConfig])

  const handleTypeChange = useCallback((type: ChartType) => {
    setConfig(prev => ({ ...prev, type }))
  }, [])

  const handleSizeChange = useCallback((size: ChartSize) => {
    setConfig(prev => ({ ...prev, size }))
  }, [])

  const handleDataChange = useCallback((value: string) => {
    setDataInput(value)
    try {
      const parsed = JSON.parse(value)
      if (!Array.isArray(parsed)) {
        setJsonError('Los datos deben ser un array de objetos')
      } else {
        setJsonError(null)
      }
    } catch {
      if (value.trim()) {
        setJsonError('JSON inválido')
      } else {
        setJsonError(null)
      }
    }
  }, [])

  const handleAddDataKey = useCallback(() => {
    setConfig(prev => ({
      ...prev,
      dataKeys: [...prev.dataKeys, `series${prev.dataKeys.length + 1}`]
    }))
  }, [])

  const handleRemoveDataKey = useCallback((index: number) => {
    setConfig(prev => ({
      ...prev,
      dataKeys: prev.dataKeys.filter((_, i) => i !== index)
    }))
  }, [])

  const handleDataKeyChange = useCallback((index: number, value: string) => {
    setConfig(prev => ({
      ...prev,
      dataKeys: prev.dataKeys.map((k, i) => i === index ? value : k)
    }))
  }, [])

  const handleColorChange = useCallback((index: number, color: string) => {
    setConfig(prev => {
      const newColors = [...(prev.colors || DEFAULT_COLORS)]
      newColors[index] = color
      return { ...prev, colors: newColors }
    })
  }, [])

  const handleSubmit = useCallback(() => {
    let data: ChartDataPoint[] = []
    
    if (dataInput.trim()) {
      try {
        data = JSON.parse(dataInput)
      } catch {
        setJsonError('JSON inválido')
        return
      }
    }

    onSave({
      ...config,
      data,
      isDeletable: true,
      createdAt: new Date()
    } as Omit<ChartConfig, 'id' | 'createdAt'>)
    
    onClose()
  }, [config, dataInput, onSave, onClose])

  if (!isOpen) return null

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{title}</h5>
            <button
              type="button"
              className="btn-close"
              onClick={onClose}
            />
          </div>
          
          <div className="modal-body">
            <div className="row g-3">
              <div className="col-12">
                <label className="form-label">Título</label>
                <input
                  type="text"
                  className="form-control"
                  value={config.title}
                  onChange={e => setConfig(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Nombre de la gráfica"
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Tipo de gráfica</label>
                <div className="d-flex flex-wrap gap-2">
                  {CHART_TYPES.map(ct => (
                    <button
                      key={ct.value}
                      type="button"
                      className={`btn ${config.type === ct.value ? 'btn-primary' : 'btn-outline-secondary'}`}
                      onClick={() => handleTypeChange(ct.value)}
                    >
                      <span className="me-1">{ct.icon}</span>
                      {ct.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="col-md-6">
                <label className="form-label">Tamaño</label>
                <div className="btn-group w-100">
                  {SIZE_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`btn ${config.size === opt.value ? 'btn-primary' : 'btn-outline-secondary'}`}
                      onClick={() => handleSizeChange(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="col-12">
                <label className="form-label">
                  Campos de datos
                </label>
                <div className="d-flex flex-wrap gap-2 mb-2">
                  {config.dataKeys.map((key, index) => (
                    <div key={index} className="input-group input-group-sm" style={{ width: 'auto' }}>
                      <input
                        type="text"
                        className="form-control"
                        value={key}
                        onChange={e => handleDataKeyChange(index, e.target.value)}
                        style={{ width: '120px' }}
                      />
                      <button
                        className="btn btn-outline-danger"
                        onClick={() => handleRemoveDataKey(index)}
                        disabled={config.dataKeys.length <= 1}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                  <button
                    className="btn btn-outline-primary btn-sm"
                    onClick={handleAddDataKey}
                  >
                    <Plus size={14} className="me-1" />
                    Añadir
                  </button>
                </div>
              </div>

              <div className="col-md-6">
                <label className="form-label">Eje X (campo)</label>
                <input
                  type="text"
                  className="form-control"
                  value={config.xAxisKey}
                  onChange={e => setConfig(prev => ({ ...prev, xAxisKey: e.target.value }))}
                  placeholder="name, month, date..."
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">
                  <Palette size={14} className="me-1" />
                  Colores
                </label>
                <div className="d-flex flex-wrap gap-2">
                  {(config.colors || DEFAULT_COLORS).slice(0, 6).map((color, index) => (
                    <input
                      key={index}
                      type="color"
                      className="form-control form-control-color"
                      value={color}
                      onChange={e => handleColorChange(index, e.target.value)}
                      title={color}
                      style={{ width: '40px', height: '38px' }}
                    />
                  ))}
                </div>
              </div>

              <div className="col-12">
                <label className="form-label">
                  Datos (JSON)
                  <small className="text-muted ms-2">
                    Array de objetos: [{'{'}"name": "A", "value": 100{'}'}]
                  </small>
                </label>
                <textarea
                  className={`form-control font-monospace ${jsonError ? 'is-invalid' : ''}`}
                  rows={8}
                  value={dataInput}
                  onChange={e => handleDataChange(e.target.value)}
                  placeholder='[{"name": "Enero", "value": 100}, {"name": "Febrero", "value": 150}]'
                />
                {jsonError && (
                  <div className="invalid-feedback">{jsonError}</div>
                )}
              </div>

              <div className="col-12">
                <label className="form-label">Descripción (opcional)</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={config.description}
                  onChange={e => setConfig(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Descripción de la gráfica..."
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              <X size={16} className="me-1" />
              Cancelar
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!config.title.trim() || jsonError !== null}
            >
              <Plus size={16} className="me-1" />
              Crear gráfica
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChartConfigModal
