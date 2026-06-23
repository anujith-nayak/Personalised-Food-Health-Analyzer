import { createContext, useContext, useState, useCallback } from 'react'
import { saveTokens, clearTokens, isLoggedIn } from '../api/auth'
import * as authApi from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(isLoggedIn)

  const login = useCallback(async (email, password) => {
    const res = await authApi.login({ email, password })
    saveTokens(res.data.access_token, res.data.refresh_token)
    setAuthenticated(true)
  }, [])

  const register = useCallback(async (data) => {
    const res = await authApi.register(data)
    saveTokens(res.data.access_token, res.data.refresh_token)
    setAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setAuthenticated(false)
  }, [])

  return (
    <AuthContext.Provider value={{ authenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
