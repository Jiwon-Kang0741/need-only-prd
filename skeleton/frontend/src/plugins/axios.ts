import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: add common params
api.interceptors.request.use((config) => {
  // Add global params if needed (gPBL_CD, gLANG, etc.)
  return config
})

// Response interceptor: check Hone framework response format
api.interceptors.response.use(
  (response) => {
    // Hone framework wraps response in { header: { responseCode, responseMessage }, payload }
    const data = response.data
    if (data && data.header) {
      if (data.header.responseCode !== 'S0000') {
        const msg = data.header.responseMessage || 'Server error'
        console.warn(`[API] ${msg}`)
        return Promise.reject(new Error(msg))
      }
    }
    return response
  },
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('[API] Request timeout')
    } else if (!error.response) {
      console.error('[API] Network error')
    } else {
      console.error(`[API] ${error.response.status}: ${error.response.statusText}`)
    }
    return Promise.reject(error)
  }
)

export default api
