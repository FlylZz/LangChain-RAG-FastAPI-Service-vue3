<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { marked } from 'marked'
import { useSessionStore } from '@/stores/session'
import { streamChat } from '@/api/chat'
import { getSessions, getAllMessages } from '@/api/session'

const sessionStore = useSessionStore()
const inputText = ref('')
const isStreaming = ref(false)
const messagesEl = ref(null)
const inputEl = ref(null)
const errorMsg = ref('')

// 会话列表（顶部下拉选择）
const sessionList = ref([])
const showSessionPicker = ref(false)

const messages = computed(() => sessionStore.messages)
const currentSessionId = computed(() => sessionStore.currentSessionId)

// 配置 marked
marked.setOptions({ breaks: true })

function renderMarkdown(content) {
  return marked.parse(content || '')
}

async function loadSessions() {
  try {
    const res = await getSessions()
    sessionList.value = res.data?.list || res.data?.items || res.data || []
  } catch (e) {
    console.error('获取会话列表失败', e)
  }
}

onMounted(() => {
  loadSessions()
  // 如果从会话管理页面跳转过来，自动加载历史消息
  if (currentSessionId.value) {
    loadHistoryMessages(currentSessionId.value)
  }
})

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || isStreaming.value) return

  errorMsg.value = ''
  inputText.value = ''
  isStreaming.value = true

  // 添加用户消息
  sessionStore.addMessage({ role: 'user', content: query, streaming: false })
  // 添加 AI 占位消息
  sessionStore.addMessage({ role: 'assistant', content: '', streaming: true })

  await scrollToBottom()

  try {
    await streamChat(query, currentSessionId.value, {
      onSession(data) {
        // 后端返回 session 信息（sessionId 为 camelCase）
        const sid = data.sessionId ?? data.session_id ?? data.id ?? data
        if (sid) sessionStore.setCurrentSession(sid)
        // 刷新会话列表
        loadSessions()
      },
      onChunk(data) {
        const text = typeof data === 'string' ? data : (data.content ?? data.chunk ?? '')
        // 逐字渲染，模拟 typewriter 效果（每字符间隔 ~25ms）
        typewriterAppend(text)
      },
      onDone() {
        sessionStore.finishLastMessage()
        isStreaming.value = false
        loadSessions()
      },
      onError(data) {
        const msg = typeof data === 'string' ? data : (data.message ?? '对话出错')
        sessionStore.finishLastMessage()
        errorMsg.value = msg
        isStreaming.value = false
      },
    })
  } catch (e) {
    sessionStore.finishLastMessage()
    errorMsg.value = e.message || '网络错误，请重试'
    isStreaming.value = false
  }
}

function newChat() {
  sessionStore.clearSession()
  errorMsg.value = ''
}

function selectSession(session) {
  sessionStore.clearMessages()
  sessionStore.setCurrentSession(session.id)
  showSessionPicker.value = false
  // 加载历史消息
  loadHistoryMessages(session.id)
}

async function loadHistoryMessages(sessionId) {
  try {
    const res = await getAllMessages(sessionId)
    const msgs = res.data?.messages || res.data || []
    sessionStore.clearMessages()
    msgs.forEach(m => {
      sessionStore.addMessage({
        role: m.role,
        content: m.content,
        streaming: false,
      })
    })
    scrollToBottom()
  } catch (e) {
    console.error('加载历史消息失败', e)
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const currentSessionTitle = computed(() => {
  if (!currentSessionId.value) return '新对话'
  const s = sessionList.value.find(s => s.id === currentSessionId.value)
  return s?.title || `会话 #${currentSessionId.value}`
})

// ====== 逐字渲染队列 ======
const typewriterQueue = ref([])
let typewriterRunning = false

async function typewriterAppend(text) {
  // 将文本加入逐字渲染队列
  for (const ch of text) {
    typewriterQueue.value.push(ch)
  }
  if (!typewriterRunning) {
    typewriterRunning = true
    while (typewriterQueue.value.length > 0) {
      const ch = typewriterQueue.value.shift()
      sessionStore.appendToLastMessage(ch)
      await new Promise(r => setTimeout(r, 25))
    }
    typewriterRunning = false
  }
}
</script>

<template>
  <div class="chat-view">
    <!-- 顶部栏 -->
    <header class="chat-header">
      <button class="session-selector" @click="showSessionPicker = !showSessionPicker">
        <span class="session-title">{{ currentSessionTitle }}</span>
        <span class="arrow">▾</span>
      </button>
      <button class="new-btn" @click="newChat" title="新对话">✏️</button>
    </header>

    <!-- 会话选择下拉 -->
    <div v-if="showSessionPicker" class="session-picker" @click.self="showSessionPicker = false">
      <div class="picker-inner">
        <div class="picker-header">选择会话</div>
        <div class="picker-item new-item" @click="newChat(); showSessionPicker = false">
          ＋ 新对话
        </div>
        <div
          v-for="s in sessionList"
          :key="s.id"
          class="picker-item"
          :class="{ active: s.id === currentSessionId }"
          @click="selectSession(s)"
        >
          <span class="picker-title">{{ s.title || `会话 #${s.id}` }}</span>
          <span class="picker-time">{{ formatTime(s.updated_at || s.created_at) }}</span>
        </div>
        <div v-if="sessionList.length === 0" class="picker-empty">暂无历史会话</div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages" ref="messagesEl">
      <div v-if="messages.length === 0" class="empty-hint">
        <div class="hint-icon">🤖</div>
        <p>你好！我是 AI 助手，有什么可以帮你的？</p>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message-row"
        :class="msg.role"
      >
        <!-- AI 头像 -->
        <div v-if="msg.role === 'assistant'" class="avatar ai-avatar">AI</div>

        <div class="bubble-wrap">
          <div
            class="bubble"
            :class="{ 'streaming-bubble': msg.streaming }"
          >
            <!-- AI 消息渲染 Markdown -->
            <template v-if="msg.role === 'assistant'">
              <div
                v-if="msg.content"
                class="markdown-body"
                v-html="renderMarkdown(msg.content)"
              />
              <span v-else class="typing-dots"><span /><span /><span /></span>
            </template>
            <!-- 用户消息纯文本 -->
            <template v-else>
              {{ msg.content }}
            </template>
          </div>
        </div>

        <!-- 用户头像 -->
        <div v-if="msg.role === 'user'" class="avatar user-avatar">我</div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="error-bar">
      {{ errorMsg }}
      <span class="close-err" @click="errorMsg = ''">✕</span>
    </div>

    <!-- 输入框 -->
    <div class="input-bar">
      <textarea
        ref="inputEl"
        v-model="inputText"
        class="input-textarea"
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        rows="1"
        :disabled="isStreaming"
        @keydown="handleKeydown"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || isStreaming"
        @click="sendMessage"
      >
        <span v-if="isStreaming" class="sending-icon">⏳</span>
        <span v-else>发送</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f6fa;
  position: relative;
}

/* 顶部栏 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.session-selector {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  color: #222;
  max-width: 240px;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  color: #999;
  font-size: 12px;
}

.new-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: background 0.15s;
}
.new-btn:hover { background: #f0f0f0; }

/* 会话选择器 */
.session-picker {
  position: absolute;
  top: 53px;
  left: 0;
  right: 0;
  z-index: 200;
  background: rgba(0,0,0,0.3);
  bottom: 0;
}

.picker-inner {
  background: #fff;
  border-radius: 0 0 16px 16px;
  max-height: 60vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
}

.picker-header {
  padding: 12px 16px;
  font-size: 13px;
  color: #999;
  border-bottom: 1px solid #f0f0f0;
}

.picker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}
.picker-item:hover { background: #f8f8f8; }
.picker-item.active { background: #eef3ff; color: #4f8ef7; }
.picker-item.new-item { color: #4f8ef7; font-weight: 500; }

.picker-title {
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-time { font-size: 12px; color: #bbb; margin-left: 8px; }
.picker-empty { padding: 24px; text-align: center; color: #ccc; font-size: 14px; }

/* 消息列表 */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-hint {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bbb;
  gap: 8px;
  padding-top: 60px;
}
.hint-icon { font-size: 48px; }
.empty-hint p { font-size: 15px; }

/* 消息行 */
.message-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.message-row.user { flex-direction: row-reverse; }

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.ai-avatar { background: #4f8ef7; color: #fff; }
.user-avatar { background: #e8f0fe; color: #4f8ef7; }

.bubble-wrap { max-width: 75%; }

.bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-row.user .bubble {
  background: #4f8ef7;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .bubble {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* 流式打字点 */
.typing-dots {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  height: 16px;
}
.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #bbb;
  animation: bounce 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

/* Markdown 样式 */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(pre) {
  background: #f4f4f5;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
  margin: 6px 0;
}
.markdown-body :deep(code) {
  background: #f4f4f5;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 13px;
}
.markdown-body :deep(pre code) { background: none; padding: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #ddd;
  padding-left: 10px;
  color: #888;
  margin: 4px 0;
}

/* 错误提示 */
.error-bar {
  background: #fff2f0;
  color: #ff4d4f;
  padding: 8px 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.close-err { cursor: pointer; font-size: 16px; }

/* 输入区 */
.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  background: #fff;
  border-top: 1px solid #eee;
  flex-shrink: 0;
}

.input-textarea {
  flex: 1;
  resize: none;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  padding: 9px 14px;
  font-size: 14px;
  line-height: 1.5;
  outline: none;
  max-height: 120px;
  overflow-y: auto;
  font-family: inherit;
  background: #f8f8f8;
  transition: border-color 0.2s;
}
.input-textarea:focus { border-color: #4f8ef7; background: #fff; }
.input-textarea:disabled { opacity: 0.6; }

.send-btn {
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 20px;
  padding: 9px 18px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s, opacity 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { background: #3b7de8; }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
