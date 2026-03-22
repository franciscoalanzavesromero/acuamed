const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const api = {
  async healthCheck() {
    const res = await fetch(`${API_BASE}/health`)
    return res.json()
  },

  async getModelStatus() {
    const res = await fetch(`${API_BASE}/models/status`)
    return res.json()
  },

  async uploadFile(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    })
    return res.json()
  },

  async getUploads() {
    const res = await fetch(`${API_BASE}/uploads`)
    return res.json()
  },

  async getUploadStatus(uploadId: string) {
    const res = await fetch(`${API_BASE}/uploads/${uploadId}`)
    return res.json()
  },

  async deleteUpload(uploadId: string) {
    const res = await fetch(`${API_BASE}/uploads/${uploadId}`, {
      method: 'DELETE'
    })
    return res.json()
  },

  async retryUpload(uploadId: string) {
    const res = await fetch(`${API_BASE}/uploads/${uploadId}/retry`, {
      method: 'POST'
    })
    return res.json()
  },

  async chat(message: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: message }),
    })
    return res.json()
  },

  async query(question: string): Promise<any> {
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    return res.json()
  },

  async getConsumptionSummary(params?: {
    start_date?: string
    end_date?: string
    location_id?: string
  }) {
    const res = await fetch(`${API_BASE}/consumption/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params || {}),
    })
    return res.json()
  },

  async detectAnomalies(thresholdZ: number = 2.5) {
    const res = await fetch(`${API_BASE}/anomalies/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threshold_z: thresholdZ }),
    })
    return res.json()
  },

  async getSchema() {
    const res = await fetch(`${API_BASE}/schema`)
    return res.json()
  }
}
