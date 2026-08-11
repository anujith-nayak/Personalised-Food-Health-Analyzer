import api from './client'

export const uploadBloodReport = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/health/blood-report/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getBloodReport = () =>
  api.get('/health/blood-report')

export const confirmBloodReport = (reportId, confirmedItems) =>
  api.put(`/health/blood-report/${reportId}/confirm`, { confirmed_items: confirmedItems })

export const deleteBloodReport = (reportId) =>
  api.delete(`/health/blood-report/${reportId}`)
