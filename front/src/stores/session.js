import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSessionStore = defineStore('session', () => {
  // 当前激活的会话 ID（null = 新对话）
  const currentSessionId = ref(null)
  // 当前对话的消息列表
  const messages = ref([])

  function setCurrentSession(id) {
    currentSessionId.value = id
  }

  function clearSession() {
    currentSessionId.value = null
    messages.value = []
  }

  function clearMessages() {
    messages.value = []
  }

  function addMessage(message) {
    messages.value.push(message)
  }

  /** 更新最后一条消息的内容（流式追加） */
  function appendToLastMessage(chunk) {
    if (messages.value.length === 0) return
    const last = messages.value[messages.value.length - 1]
    last.content += chunk
  }

  /** 标记最后一条消息流式结束 */
  function finishLastMessage() {
    if (messages.value.length === 0) return
    messages.value[messages.value.length - 1].streaming = false
  }

  return {
    currentSessionId,
    messages,
    setCurrentSession,
    clearSession,
    clearMessages,
    addMessage,
    appendToLastMessage,
    finishLastMessage,
  }
})
