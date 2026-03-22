import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, User } from 'lucide-react'
import { api } from '../services/api'

interface Message {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: Date
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'ai',
      content: '¡Hola! Soy el asistente de ACUAMED. Puedo ayudarte a analizar tus datos hídricos. Pregúntame sobre consumos, anomalías o tendencias.',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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

    try {
      const aiMessageId = (Date.now() + 1).toString()
      setMessages(prev => [...prev, {
        id: aiMessageId,
        role: 'ai',
        content: '',
        timestamp: new Date()
      }])

      const response = await api.chat(input)
      
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: response.response || response.message || 'No he podido procesar tu consulta.' }
          : msg
      ))
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === Date.now().toString()
          ? { ...msg, content: 'Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.' }
          : msg
      ))
    } finally {
      setIsLoading(false)
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
    'Top 5 ubicaciones por consumo'
  ]

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>
          <MessageSquare size={20} />
          Asistente IA
        </h3>
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
                {msg.content || (
                  <div className="typing">
                    <span></span>
                    <span></span>
                    <span></span>
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
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
