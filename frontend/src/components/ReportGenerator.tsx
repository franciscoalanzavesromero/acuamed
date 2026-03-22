import { useState } from 'react'
import { FileText, Download, Calendar, Building, Printer } from 'lucide-react'

export default function ReportGenerator() {
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<any>(null)
  const [dateRange, setDateRange] = useState({
    start_date: '',
    end_date: ''
  })

  const generateReport = async () => {
    setLoading(true)
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/report/executive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: dateRange.start_date || null,
          end_date: dateRange.end_date || null
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setReport(data)
      }
    } catch (error) {
      console.error('Report generation error:', error)
    } finally {
      setLoading(false)
    }
  }

  const printReport = () => {
    window.print()
  }

  const downloadReport = () => {
    const content = document.getElementById('report-content')
    if (!content) return

    const text = `
ACUAMED - INFORME EJECUTIVO
===========================
Generado: ${new Date().toLocaleDateString('es-ES', { 
  day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' 
})}
Período: ${dateRange.start_date || 'Inicio'} - ${dateRange.end_date || 'Fin'}

RESUMEN EJECUTIVO
-----------------
${report?.content?.executive_summary || 'No disponible'}

MÉTRICAS CLAVE
--------------
- Volumen Total: ${report?.summary_metrics?.total_volume_m3?.toLocaleString() || 0} m³
- Promedio Mensual: ${report?.summary_metrics?.average_monthly_volume_m3?.toLocaleString() || 0} m³
- Registros: ${report?.summary_metrics?.total_records?.toLocaleString() || 0}
- Ubicaciones Activas: ${report?.summary_metrics?.active_locations || 0}

HALLAZGOS CLAVE
---------------
${report?.content?.key_findings?.map((h: string, i: number) => `${i + 1}. ${h}`).join('\n') || 'No disponibles'}

RECOMENDACIONES
---------------
${report?.content?.recommendations?.map((r: string, i: number) => `${i + 1}. ${r}`).join('\n') || 'No disponibles'}
    `.trim()

    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ACUAMED_Informe_${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="chart-container mb-4">
        <div className="row g-3 align-items-end">
          <div className="col-md-3">
            <label className="form-label small text-muted">
              <Calendar size={14} className="me-1" />
              Fecha Inicio
            </label>
            <input 
              type="date" 
              className="form-control"
              value={dateRange.start_date}
              onChange={e => setDateRange(d => ({ ...d, start_date: e.target.value }))}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small text-muted">
              <Calendar size={14} className="me-1" />
              Fecha Fin
            </label>
            <input 
              type="date" 
              className="form-control"
              value={dateRange.end_date}
              onChange={e => setDateRange(d => ({ ...d, end_date: e.target.value }))}
            />
          </div>
          <div className="col-md-4">
            <button 
              className="btn btn-primary w-100"
              onClick={generateReport}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" />
                  Generando...
                </>
              ) : (
                <>
                  <FileText size={16} className="me-2" />
                  Generar Informe
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {report && (
        <div id="report-content" className="chart-container">
          <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom no-print">
            <div>
              <h4 className="mb-1">{report.report_metadata?.title}</h4>
              <small className="text-muted">
                Generado: {new Date(report.report_metadata?.generated_at).toLocaleString('es-ES')}
              </small>
            </div>
            <div className="d-flex gap-2">
              <button className="btn btn-outline-secondary btn-sm" onClick={printReport}>
                <Printer size={16} className="me-1" /> Imprimir
              </button>
              <button className="btn btn-outline-success btn-sm" onClick={downloadReport}>
                <Download size={16} className="me-1" /> Descargar
              </button>
            </div>
          </div>

          <div className="row g-4 mb-4">
            <div className="col-md-3">
              <div className="p-3 bg-light rounded">
                <div className="text-muted small">Volumen Total</div>
                <div className="h4 mb-0">
                  {(report.summary_metrics?.total_volume_m3 / 1000000).toFixed(2)} Mm³
                </div>
              </div>
            </div>
            <div className="col-md-3">
              <div className="p-3 bg-light rounded">
                <div className="text-muted small">Promedio Mensual</div>
                <div className="h4 mb-0">
                  {(report.summary_metrics?.average_monthly_volume_m3 / 1000).toFixed(1)} Km³
                </div>
              </div>
            </div>
            <div className="col-md-3">
              <div className="p-3 bg-light rounded">
                <div className="text-muted small">Registros</div>
                <div className="h4 mb-0">
                  {report.summary_metrics?.total_records?.toLocaleString() || 0}
                </div>
              </div>
            </div>
            <div className="col-md-3">
              <div className="p-3 bg-light rounded">
                <div className="text-muted small">Ubicaciones</div>
                <div className="h4 mb-0">
                  {report.summary_metrics?.active_locations || 0}
                </div>
              </div>
            </div>
          </div>

          <div className="row g-4">
            <div className="col-lg-8">
              <div className="mb-4">
                <h5 className="mb-3">
                  <i className="bi bi-file-text me-2 text-primary"></i>
                  Resumen Ejecutivo
                </h5>
                <p className="lead">{report.content?.executive_summary}</p>
              </div>

              <div className="mb-4">
                <h5 className="mb-3">
                  <i className="bi bi-lightbulb me-2 text-warning"></i>
                  Hallazgos Clave
                </h5>
                <ul className="list-group">
                  {report.content?.key_findings?.map((finding: string, i: number) => (
                    <li key={i} className="list-group-item d-flex align-items-center">
                      <span className="badge bg-primary me-3">{i + 1}</span>
                      {finding}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mb-4">
                <h5 className="mb-3">
                  <i className="bi bi-list-check me-2 text-success"></i>
                  Recomendaciones
                </h5>
                <div className="row g-2">
                  {report.content?.recommendations?.map((rec: string, i: number) => (
                    <div key={i} className="col-md-6">
                      <div className="p-3 bg-success bg-opacity-10 rounded h-100">
                        <div className="d-flex align-items-start gap-2">
                          <i className="bi bi-check-circle-fill text-success mt-1"></i>
                          <span>{rec}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="col-lg-4">
              <div className="card border-0 shadow-sm mb-4">
                <div className="card-header bg-primary text-white">
                  <h6 className="mb-0">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    Alertas de Riesgo
                  </h6>
                </div>
                <div className="card-body">
                  {report.content?.risk_alerts?.length > 0 ? (
                    <ul className="list-unstyled mb-0">
                      {report.content?.risk_alerts?.map((alert: string, i: number) => (
                        <li key={i} className="mb-2 d-flex align-items-start gap-2">
                          <i className="bi bi-exclamation-circle text-danger mt-1"></i>
                          <span>{alert}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center text-success py-3">
                      <i className="bi bi-check-circle-fill fs-1"></i>
                      <p className="mb-0 mt-2">No hay alertas de riesgo</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="card border-0 shadow-sm">
                <div className="card-header bg-light">
                  <h6 className="mb-0">
                    <Building size={16} className="me-2" />
                    Desglose Mensual
                  </h6>
                </div>
                <div className="card-body p-0">
                  <div className="table-responsive">
                    <table className="table table-sm mb-0">
                      <thead>
                        <tr>
                          <th>Mes</th>
                          <th className="text-end">Volumen</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.monthly_breakdown?.slice(0, 6).map((m: any, i: number) => (
                          <tr key={i}>
                            <td>{new Date(m.month).toLocaleDateString('es-ES', { month: 'short', year: 'numeric' })}</td>
                            <td className="text-end fw-bold">
                              {(m.volume / 1000).toFixed(0)} Km³
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-top text-center text-muted small no-print">
            <p className="mb-0">
              <i className="bi bi-shield-check me-1"></i>
              ACUAMED - Sistema de Analítica Hídrica con IA Local
              <span className="mx-3">|</span>
              Documento generado automáticamente
            </p>
          </div>
        </div>
      )}

      {!report && !loading && (
        <div className="text-center py-5">
          <FileText size={64} className="text-muted mb-3" />
          <h5 className="text-muted">Sin informe generado</h5>
          <p className="text-muted">Selecciona el período y genera tu informe ejecutivo</p>
        </div>
      )}

      <style>{`
        @media print {
          .no-print { display: none !important; }
          .chart-container { 
            box-shadow: none !important; 
            border: 1px solid #dee2e6 !important;
          }
          body { background: white !important; }
        }
      `}</style>
    </div>
  )
}
