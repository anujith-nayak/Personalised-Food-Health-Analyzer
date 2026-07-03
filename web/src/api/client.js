import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401/403 — try refresh token, retry original request once
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config

    // Only try refresh on 401/403, and only once
    if (
      (err.response?.status === 401 || err.response?.status === 403) &&
      !original._retried
    ) {
      original._retried = true

      if (isRefreshing) {
        // Queue this request while refresh is in progress
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`
          return api(original)
        })
      }

      isRefreshing = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        // No refresh token — force logout
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(err)
      }

      try {
        const res = await axios.post('/api/auth/refresh-token', {
          refresh_token: refreshToken
        })
        const newToken = res.data.access_token
        localStorage.setItem('access_token', newToken)
        localStorage.setItem('refresh_token', res.data.refresh_token)

        api.defaults.headers.common.Authorization = `Bearer ${newToken}`
        processQueue(null, newToken)

        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    // Extract readable error message for non-auth errors
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      'Something went wrong'
    return Promise.reject(new Error(message))
  }
)

export default api
