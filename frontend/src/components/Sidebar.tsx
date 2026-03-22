import { Droplets, LayoutDashboard, Upload, Database, History, MessageSquare, Crosshair, FileText } from 'lucide-react'

type View = 'upload' | 'dashboard' | 'data' | 'history' | 'simulation' | 'reports'

interface SidebarProps {
  activeView: View
  onViewChange: (view: View) => void
  apiStatus: 'online' | 'offline' | 'checking'
  modelStatus: 'loaded' | 'not_loaded' | 'unknown'
}

export default function Sidebar({ activeView, onViewChange, apiStatus, modelStatus }: SidebarProps) {
  const mainNavItems = [
    { id: 'upload' as View, icon: <Upload size={20} />, label: 'Cargar Excel' },
    { id: 'dashboard' as View, icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
    { id: 'data' as View, icon: <Database size={20} />, label: 'Explorador' },
    { id: 'history' as View, icon: <History size={20} />, label: 'Historial' },
  ]

  const analysisNavItems = [
    { id: 'simulation' as View, icon: <Crosshair size={20} />, label: 'Simulador What-If' },
    { id: 'reports' as View, icon: <FileText size={20} />, label: 'Informes' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Droplets size={32} color="#03a9f4" />
          <div>
            <h1>ACUAMED</h1>
            <p className="sidebar-subtitle">Analítica Hídrica con IA</p>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-title">Principal</div>
          {mainNavItems.map(item => (
            <div
              key={item.id}
              className={`nav-item ${activeView === item.id ? 'active' : ''}`}
              onClick={() => onViewChange(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Análisis Avanzado</div>
          {analysisNavItems.map(item => (
            <div
              key={item.id}
              className={`nav-item ${activeView === item.id ? 'active' : ''}`}
              onClick={() => onViewChange(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Modelo IA</div>
          <div
            className="nav-item"
            style={{ opacity: 0.7, cursor: 'default' }}
          >
            <MessageSquare size={20} />
            <span>ministral-3-8b</span>
          </div>
        </div>
      </nav>

      <div className="sidebar-footer">
        <div className="status-badge">
          <span className={`status-dot ${apiStatus === 'online' ? 'online' : ''}`}></span>
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 500 }}>
              API {apiStatus === 'checking' ? 'Verificando...' : apiStatus}
            </div>
            <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>
              LLM: {modelStatus === 'loaded' ? 'Cargado' : modelStatus === 'not_loaded' ? 'No cargado' : 'Desconocido'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
