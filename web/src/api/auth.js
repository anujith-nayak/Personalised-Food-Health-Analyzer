import api from './client'

export const register = (data) => api.post('/auth/register', data)
export const login    = (data) => api.post('/auth/login', data)
export const refresh  = (token) => api.post('/auth/refresh-token', { refresh_token: token })

export const saveTokens = (access, refresh) => {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export const clearTokens = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export const isLoggedIn = () => !!localStorage.getItem('access_token')
