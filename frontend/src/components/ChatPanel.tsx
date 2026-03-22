import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, MessageSquare, User, Trash2, Maximize2, Minimize2, Loader2, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { api } from '../services/api'
import ChartPreview from './ChartPreview'
import { parseChartFromText, createChartConfig, detectChartableContent } from '../services/chartGenerator'
import { ChartConfig } from '../types/charts'

interface Message {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: Date
  chartConfig?: Omit<ChartConfig, 'id' | 'createdAt'>
  chartAdded?: boolean
}

interface ChatPanelProps {
  onAddChartToDashboard?: (chart: Omit<ChartConfig, 'id' | 'createdAt'>) => void
}

export default function ChatPanel({ onAddChartToDashboard }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'ai',
      content: '¡Hola! Soy el asistente de ACUAMED. Puedo ayudarte a analizar tus datos hídricos. Pregúntame sobre consumos, anomalías o tendencias. También puedo generar gráficas interactivas para visualizar los datos.',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState<string>('')
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [addingChartId, setAddingChartId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const loadingInterval = useRef<NodeJS.Timeout | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleClearChat = () => {
    setMessages([
      {
        id: Date.now().toString(),
        role: 'ai',
        content: 'Chat borrado. ¿En qué puedo ayudarte ahora?',
        timestamp: new Date()
      }
    ])
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  const handleAddChart = useCallback((messageId: string, chartConfig: Omit<ChartConfig, 'id' | 'createdAt'>) => {
    setAddingChartId(messageId)
    
    setTimeout(() => {
      if (onAddChartToDashboard) {
        onAddChartToDashboard(chartConfig)
      }
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, chartAdded: true }
          : msg
      ))
      setAddingChartId(null)
    }, 500)
  }, [onAddChartToDashboard])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setLoadingStage('Iniciando consulta...')
    setLoadingProgress(0)

    // Simular progreso basado en el tiempo (las respuestas típicas tardan 15-16 segundos)
    const startTime = Date.now()
    const totalTime = 16000 // Tiempo estimado total
    
    loadingInterval.current = setInterval(() => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(95, (elapsed / totalTime) * 100)
      setLoadingProgress(progress)
      
      if (elapsed < 3000) {
        setLoadingStage('Procesando pregunta...')
      } else if (elapsed < 8000) {
        setLoadingStage('Generando consulta SQL...')
      } else if (elapsed < 13000) {
        setLoadingStage('Ejecutando consulta en base de datos...')
      } else {
        setLoadingStage('Analizando resultados...')
      }
    }, 500)

    try {
      const aiMessageId = (Date.now() + 1).toString()
      setMessages(prev => [...prev, {
        id: aiMessageId,
        role: 'ai',
        content: '',
        timestamp: new Date()
      }])

      const response = await api.chat(input, 35000) // 35 segundos de timeout
      const aiContent = response.response || response.message || 'No he podido procesar tu consulta.'
      
      // Completar progreso
      setLoadingProgress(100)
      setLoadingStage('Respuesta recibida')
      
      let chartConfig: Omit<ChartConfig, 'id' | 'createdAt'> | undefined
      if (detectChartableContent(aiContent)) {
        const parsed = parseChartFromText(aiContent, response.context)
        if (parsed && parsed.data.length > 0) {
          chartConfig = createChartConfig(parsed)
        }
      }
      
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: aiContent, chartConfig }
          : msg
      ))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.'
      setMessages(prev => prev.map(msg => 
        msg.id === (Date.now() + 1).toString()
          ? { ...msg, content: `**Error:** ${errorMessage}` }
          : msg
      ))
    } finally {
      if (loadingInterval.current) {
        clearInterval(loadingInterval.current)
        loadingInterval.current = null
      }
      setIsLoading(false)
      setLoadingStage('')
      setLoadingProgress(0)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const suggestedQuestions = [
    '¿Cuáles son los consumos totales?',
    '¿Hay anomalías en los datos?',
    'Resumen del último mes',
    'Top 5 ubicaciones por consumo',
    'Mostrar tendencia de consumo'
  ]

  return (
    <div className={`chat-panel ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="chat-header">
        <h3>
          <MessageSquare size={20} />
          Asistente IA
        </h3>
        <div className="chat-header-actions">
          <button 
            className="chat-header-btn"
            onClick={handleClearChat}
            title="Borrar chat"
          >
            <Trash2 size={18} />
          </button>
          <button 
            className="chat-header-btn"
            onClick={toggleFullscreen}
            title={isFullscreen ? "Salir de pantalla completa" : "Pantalla completa"}
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="d-flex align-items-start gap-2">
              {msg.role === 'ai' ? (
                <MessageSquare size={18} className="mt-1 flex-shrink-0" style={{ color: '#1976d2' }} />
              ) : (
                <User size={18} className="mt-1 flex-shrink-0" style={{ color: '#388e3c' }} />
              )}
              <div className="flex-grow-1">
                {msg.content || msg.chartConfig ? (
                  <>
                    {msg.content && (
                      <ReactMarkdown
                        components={{
                          code({ node, className, children, ...props }: any) {
                            const match = /language-(\w+)/.exec(className || '')
                            const inline = node?.position?.start.line === node?.position?.end.line
                            return !inline && match ? (
                              <SyntaxHighlighter
                                style={oneDark as any}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            ) : (
                              <code className={className} {...props}>
                                {children}
                              </code>
                            )
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    )}
                    
                    {msg.chartConfig && !msg.chartAdded && (
                      <div className="mt-3">
                        <ChartPreview
                          config={msg.chartConfig}
                          onAddToDashboard={() => handleAddChart(msg.id, msg.chartConfig!)}
                          isAdding={addingChartId === msg.id}
                        />
                      </div>
                    )}
                    
                    {msg.chartAdded && (
                      <div className="alert alert-success py-2 px-3 mt-3 mb-0" style={{ fontSize: '0.85rem' }}>
                        Gráfica añadida al dashboard correctamente
                      </div>
                    )}
                  </>
                ) : (
                  <div className="loading-container">
                    <div className="loading-header">
                      <Loader2 size={16} className="spin" />
                      <span className="loading-stage">{loadingStage}</span>
                    </div>
                    <div className="loading-progress">
                      <div 
                        className="loading-progress-bar" 
                        style={{ width: `${loadingProgress}%` }}
                      ></div>
                    </div>
                    <div className="loading-time">
                      <Clock size={12} />
                      <span>Tiempo estimado: {Math.max(0, Math.ceil((16000 - (loadingProgress / 100 * 16000)) / 1000))}s</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="px-3 pb-2">
          <p style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.5rem' }}>Preguntas sugeridas:</p>
          <div className="d-flex flex-wrap gap-1">
            {suggestedQuestions.map((q, i) => (
              <button
                key={i}
                className="btn btn-sm btn-outline-primary"
                style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                onClick={() => setInput(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-input-area">
        <div className="chat-input-group">
          <input
            type="text"
            className="chat-input"
            placeholder="Escribe tu pregunta..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
          />
          <button 
            className="chat-send-btn" 
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  )
}
