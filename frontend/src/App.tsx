import { useState, useEffect } from 'react'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import FileDropZone from './components/FileDropZone'
import Dashboard from './components/Dashboard'
import DataTable from './components/DataTable'
import UploadHistory from './components/UploadHistory'
import WhatIfSimulator from './components/WhatIfSimulator'
import ReportGenerator from './components/ReportGenerator'
import { api } from './services/api'

type View = 'upload' | 'dashboard' | 'data' | 'history' | 'simulation' | 'reports'

function App() {
  const [activeView, setActiveView] = useState<View>('upload')
  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'checking'>('checking')
  const [modelStatus, setModelStatus] = useState<'loaded' | 'not_loaded' | 'unknown'>('unknown')
  const [showChat, setShowChat] = useState(true)

  useEffect(() => {
    checkApiStatus()
    checkModelStatus()
  }, [])

  const checkApiStatus = async () => {
    try {
      const res = await api.healthCheck()
      setApiStatus(res.status === 'healthy' ? 'online' : 'offline')
    } catch {
      setApiStatus('offline')
    }
  }

  const checkModelStatus = async () => {
    try {
      const res = await api.getModelStatus()
      setModelStatus(res.model_loaded ? 'loaded' : 'not_loaded')
    } catch {
      setModelStatus('unknown')
    }
  }

  const getViewTitle = () => {
    const titles: Record<View, string> = {
      upload: 'Cargar Datos',
      dashboard: 'Panel de Control',
      data: 'Explorador de Datos',
      history: 'Historial de Cargas',
      simulation: 'Simulador What-If',
      reports: 'Informes Ejecutivos'
    }
    return titles[activeView]
  }

  const renderContent = () => {
    switch (activeView) {
      case 'upload':
        return <FileDropZone onUploadComplete={() => setActiveView('history')} />
      case 'dashboard':
        return <Dashboard />
      case 'data':
        return <DataTable />
      case 'history':
        return <UploadHistory />
      case 'simulation':
        return <WhatIfSimulator />
      case 'reports':
        return <ReportGenerator />
      default:
        return <FileDropZone onUploadComplete={() => setActiveView('history')} />
    }
  }

  return (
    <div className="app-container">
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        apiStatus={apiStatus}
        modelStatus={modelStatus}
      />
      
      <div className="main-content">
        <div className="top-bar">
          <h2>{getViewTitle()}</h2>
          <div className="d-flex gap-2 align-items-center">
            <button
              className="btn btn-outline-primary btn-sm d-flex align-items-center gap-2"
              onClick={() => setShowChat(!showChat)}
            >
              <i className={`bi ${showChat ? 'bi-chat-left-text-fill' : 'bi-chat-left'}`}></i>
              {showChat ? 'Ocultar' : 'Mostrar'} Chat IA
            </button>
          </div>
        </div>
        
        <div className="content-area">
          <main className="main-panel">
            {renderContent()}
          </main>
          
          {showChat && <ChatPanel />}
        </div>
      </div>
    </div>
  )
}

export default App
