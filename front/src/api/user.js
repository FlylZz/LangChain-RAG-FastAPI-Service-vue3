import request from './request'

export const userLogin = (data) => request.post('/user/login', data)
export const userRegister = (data) => request.post('/user/register', data)
export const getUserInfo = () => request.get('/user/info')
export const updateUserInfo = (data) => request.put('/user/update', data)
export const changePassword = (data) => request.put('/user/password', data)
export const uploadAvatar = (formData) => request.post('/user/avatar', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
