import request from './request'

export const getSessions = (params) => request.get('/sessions', { params })
export const createSession = (data = {}) => request.post('/sessions', data)
export const getSessionDetail = (id) => request.get(`/sessions/${id}`)
export const deleteSession = (id) => request.delete(`/sessions/${id}`)
export const clearAllSessions = () => request.delete('/sessions')
export const updateSessionTitle = (id, title) => request.put(`/sessions/${id}`, { title })
export const getAllMessages = (sessionId) => request.get(`/sessions/${sessionId}/messages/all`)
export const searchMessages = (keyword, page = 1, pageSize = 20) =>
  request.get('/sessions/search', { params: { keyword, page, pageSize } })
