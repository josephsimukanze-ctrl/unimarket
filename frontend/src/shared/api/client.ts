import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach access token from localStorage to every request
apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem('unimarket-auth')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      const token = parsed?.state?.access
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {
      // ignore malformed storage
    }
  }
  return config
})

// On 401, clear auth state (refresh flow added in a later phase)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('unimarket-auth')
    }
    return Promise.reject(error)
  },
)
