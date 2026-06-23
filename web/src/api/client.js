import axios from 'axios'

const api = axios.create({
  baseURL: '/api',   // proxied to http://localhost:8000 via vite config
  headers: { 'Content-Type': 'application/json' }
})

// Attach JWT token to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Extract readable error messages
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      'Something went wrong'
    return Promise.reject(new Error(message))
  }
)

export default api
