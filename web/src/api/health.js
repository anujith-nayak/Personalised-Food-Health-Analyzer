import api from './client'

export const getDashboard        = ()     => api.get('/dashboard')
export const getProfile          = ()     => api.get('/profile')
export const updateProfile       = (data) => api.put('/profile', data)
export const submitHealthProfile = (data) => api.post('/health-profile', data)
export const updateHealthProfile = (data) => api.put('/health-profile', data)
export const getHealthProfile    = ()     => api.get('/health-profile')
export const getFoodRestrictions = ()     => api.get('/food-restrictions')

// ── AI Nutrition Assistant (Part 4 / Part 6) ─────────────────────────────────
// POST /ai-nutrition/query
// If condition exists in health_r.csv → returns rule-based analysis (source: "rule_engine")
// Otherwise → calls Gemini/OpenAI (source: "ai_generated")
export const queryAiNutrition = (condition, nutrition = null) =>
  api.post('/ai-nutrition/query', { condition, nutrition })
