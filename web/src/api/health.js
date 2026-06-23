import api from './client'

export const getDashboard      = ()     => api.get('/dashboard')
export const getProfile        = ()     => api.get('/profile')
export const updateProfile     = (data) => api.put('/profile', data)
export const submitHealthProfile = (data) => api.post('/health-profile', data)
export const updateHealthProfile = (data) => api.put('/health-profile', data)
export const getHealthProfile  = ()     => api.get('/health-profile')
export const getFoodRestrictions = ()   => api.get('/food-restrictions')
