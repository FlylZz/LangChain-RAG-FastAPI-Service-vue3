import axios from 'axios'

// HTTP 状态码中文映射
const HTTP_STATUS_ZH = {
  400: '请求参数错误',
  401: '未授权，请重新登录',
  403: '拒绝访问',
  404: '请求资源不存在',
  408: '请求超时',
  409: '数据冲突',
  422: '请求参数验证失败',
  429: '请求过于频繁，请稍后再试',
  500: '服务器内部错误',
  502: '服务不可用，请检查后端服务是否启动',
  503: '服务暂时不可用，请稍后再试',
  504: '网关超时，请检查网络连接',
}

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器 - 自动注入 Token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - 统一处理错误（中文提示）
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    const status = error.response?.status

    // 401 跳转登录
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      window.location.href = '/login'
    }

    // 优先取后端返回的中文消息，否则按状态码翻译，最后兜底
    let msg = error.response?.data?.message || error.response?.data?.detail
    if (!msg && status) {
      msg = HTTP_STATUS_ZH[status]
    }
    if (!msg) {
      msg = error.code === 'ECONNABORTED' ? '请求超时，请稍后重试'
        : !error.response ? '网络连接失败，请检查网络'
        : '请求失败，请稍后重试'
    }

    return Promise.reject(new Error(msg))
  },
)

export default request
