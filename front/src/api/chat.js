/**
 * SSE 流式对话
 * @param {string} query - 用户提问
 * @param {number|null} sessionId - 会话ID（null 则自动创建）
 * @param {object} callbacks - { onSession, onChunk, onDone, onError }
 */
export async function streamChat(query, sessionId, callbacks) {
  const { onSession, onChunk, onDone, onError } = callbacks
  const token = localStorage.getItem('token')

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      query,
      ...(sessionId ? { sessionId } : {}),
    }),
  })

  if (!response.ok) {
    const STATUS_ZH = {
      400: '请求参数错误',
      401: '未授权，请重新登录',
      403: '拒绝访问',
      404: '请求资源不存在',
      422: '请求参数验证失败',
      500: '服务器内部错误',
      502: '服务不可用，请检查后端服务是否启动',
      503: '服务暂时不可用，请稍后再试',
      504: '网关超时，请检查网络连接',
    }
    let errMsg = STATUS_ZH[response.status] || '请求失败，请稍后重试'
    try {
      const err = await response.json()
      errMsg = err.message || err.detail || errMsg
    } catch (_) {}
    throw new Error(errMsg)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 解析完整的 SSE 事件块（以 \n\n 分隔）
    let boundary
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      let eventType = 'message'
      let data = null

      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            data = JSON.parse(line.slice(6))
          } catch (_) {
            data = line.slice(6)
          }
        }
      }

      if (data !== null) {
        if (eventType === 'session' && onSession) onSession(data)
        else if (eventType === 'chunk' && onChunk) onChunk(data)
        else if (eventType === 'done' && onDone) onDone(data)
        else if (eventType === 'error' && onError) onError(data)
      }
    }
  }
}
