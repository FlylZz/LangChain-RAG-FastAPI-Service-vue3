<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { getSessions, deleteSession, clearAllSessions, updateSessionTitle, searchMessages } from '@/api/session'

const router = useRouter()
const sessionStore = useSessionStore()

const sessions = ref([])
const loading = ref(false)
const errorMsg = ref('')
const showClearConfirm = ref(false)

// 编辑会话标题
const editingId = ref(null)
const editingTitle = ref('')

// 搜索相关
const searchKeyword = ref('')
const searchResults = ref([])
const searchTotal = ref(0)
const isSearching = ref(false)
const searchMode = ref(false) // 是否处于搜索结果模式

async function loadSessions() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await getSessions()
    sessions.value = res.data?.list || res.data?.items || res.data || []
  } catch (e) {
    errorMsg.value = '获取会话列表失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadSessions)

// 搜索
async function handleSearch() {
  const kw = searchKeyword.value.trim()
  if (!kw) {
    exitSearch()
    return
  }
  isSearching.value = true
  searchMode.value = true
  errorMsg.value = ''
  try {
    const res = await searchMessages(kw)
    searchResults.value = res.data?.list || []
    searchTotal.value = res.data?.total || 0
  } catch (e) {
    errorMsg.value = '搜索失败'
  } finally {
    isSearching.value = false
  }
}

function exitSearch() {
  searchMode.value = false
  searchKeyword.value = ''
  searchResults.value = []
  searchTotal.value = 0
}

function goToChat(session) {
  sessionStore.clearMessages()
  sessionStore.setCurrentSession(session.id)
  router.push({ name: 'chat' })
}

function goToSearchResult(item) {
  sessionStore.clearMessages()
  sessionStore.setCurrentSession(item.sessionId)
  router.push({ name: 'chat' })
}

function newSession() {
  sessionStore.clearSession()
  router.push({ name: 'chat' })
}

async function handleDelete(session) {
  if (!confirm(`确定删除会话“${session.title || '未命名'}”吗？`)) return
  try {
    await deleteSession(session.id)
    if (sessionStore.currentSessionId === session.id) {
      sessionStore.clearSession()
    }
    sessions.value = sessions.value.filter(s => s.id !== session.id)
  } catch (e) {
    errorMsg.value = '删除失败，请重试'
  }
}

async function handleClearAll() {
  try {
    await clearAllSessions()
    sessions.value = []
    sessionStore.clearSession()
    showClearConfirm.value = false
  } catch (e) {
    errorMsg.value = '清空失败，请重试'
    showClearConfirm.value = false
  }
}

function startEdit(session) {
  editingId.value = session.id
  editingTitle.value = session.title || ''
}

async function saveEdit(session) {
  if (!editingTitle.value.trim()) {
    cancelEdit()
    return
  }
  try {
    await updateSessionTitle(session.id, editingTitle.value.trim())
    session.title = editingTitle.value.trim()
  } catch (e) {
    errorMsg.value = '修改标题失败'
  }
  cancelEdit()
}

function cancelEdit() {
  editingId.value = null
  editingTitle.value = ''
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 86400000 * 7) return `${Math.floor(diff / 86400000)}天前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function highlightKeyword(text, keyword) {
  if (!keyword || !text) return text
  const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}
</script>

<template>
  <div class="sessions-view">
    <!-- 顶部栏 -->
    <header class="header">
      <h1 class="title">会话管理</h1>
      <div class="header-actions">
        <button v-if="sessions.length > 0 && !searchMode" class="clear-btn" @click="showClearConfirm = true">
          清空
        </button>
        <button v-if="!searchMode" class="new-btn" @click="newSession">＋ 新会话</button>
      </div>
    </header>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchKeyword"
          class="search-input"
          placeholder="搜索会话内容..."
          @keyup.enter="handleSearch"
        />
        <span v-if="searchKeyword" class="search-clear" @click="exitSearch">✕</span>
      </div>
      <button class="search-btn" @click="handleSearch" :disabled="isSearching">
        {{ isSearching ? '搜索中...' : '搜索' }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="error-bar">
      {{ errorMsg }}
      <span class="close-err" @click="errorMsg = ''">✕</span>
    </div>

    <!-- 搜索结果模式 -->
    <template v-if="searchMode">
      <div class="search-header">
        <span>找到 <strong>{{ searchTotal }}</strong> 条匹配结果</span>
        <button class="back-btn" @click="exitSearch">返回列表</button>
      </div>

      <div v-if="isSearching" class="loading-wrap">
        <div class="spinner" />
        <span>搜索中...</span>
      </div>

      <div v-else-if="searchResults.length === 0" class="empty-wrap">
        <div class="empty-icon">🔍</div>
        <p>未找到匹配「{{ searchKeyword }}」的内容</p>
      </div>

      <div v-else class="search-results">
        <div
          v-for="item in searchResults"
          :key="item.messageId"
          class="search-item"
          @click="goToSearchResult(item)"
        >
          <div class="search-item-header">
            <span class="search-session-title">💬 {{ item.sessionTitle }}</span>
            <span class="search-role-tag" :class="item.role">{{ item.role === 'user' ? '我的提问' : 'AI 回复' }}</span>
          </div>
          <div class="search-snippet" v-html="highlightKeyword(item.snippet, searchKeyword)"></div>
          <div class="search-item-time">{{ formatTime(item.createdAt) }}</div>
        </div>
      </div>
    </template>

    <!-- 会话列表模式 -->
    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading" class="loading-wrap">
        <div class="spinner" />
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="sessions.length === 0" class="empty-wrap">
        <div class="empty-icon">💬</div>
        <p>还没有会话记录</p>
        <button class="start-btn" @click="newSession">开始对话</button>
      </div>

      <!-- 会话列表 -->
      <div v-else class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === sessionStore.currentSessionId }"
        >
          <!-- 编辑模式 -->
          <div v-if="editingId === session.id" class="edit-mode" @click.stop>
            <input
              v-model="editingTitle"
              class="edit-input"
              autofocus
              @keydown.enter="saveEdit(session)"
              @keydown.esc="cancelEdit"
            />
            <button class="edit-save" @click="saveEdit(session)">保存</button>
            <button class="edit-cancel" @click="cancelEdit">取消</button>
          </div>

          <!-- 显示模式 -->
          <div v-else class="session-content" @click="goToChat(session)">
            <div class="session-icon">💬</div>
            <div class="session-info">
              <div class="session-title">{{ session.title || '未命名会话' }}</div>
              <div class="session-meta">
                <span class="session-time">{{ formatTime(session.updatedAt || session.updated_at || session.createdAt || session.created_at) }}</span>
                <span v-if="session.messageCount || session.message_count" class="session-count">{{ session.messageCount || session.message_count }} 条消息</span>
              </div>
            </div>
            <div class="session-actions" @click.stop>
              <button class="action-btn edit-btn" @click="startEdit(session)" title="重命名">✏️</button>
              <button class="action-btn del-btn" @click="handleDelete(session)" title="删除">🗑️</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 清空确认弹窗 -->
    <div v-if="showClearConfirm" class="modal-mask" @click.self="showClearConfirm = false">
      <div class="modal">
        <div class="modal-title">清空所有会话</div>
        <div class="modal-body">确定要删除所有会话记录吗？此操作不可撤销。</div>
        <div class="modal-footer">
          <button class="modal-cancel" @click="showClearConfirm = false">取消</button>
          <button class="modal-confirm" @click="handleClearAll">确定清空</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sessions-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f6fa;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.title {
  font-size: 17px;
  font-weight: 700;
  color: #222;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.clear-btn {
  padding: 5px 12px;
  border: 1px solid #ff4d4f;
  border-radius: 14px;
  color: #ff4d4f;
  background: none;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.clear-btn:hover { background: #fff2f0; }

.new-btn {
  padding: 5px 12px;
  border: none;
  border-radius: 14px;
  color: #fff;
  background: #4f8ef7;
  font-size: 13px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}
.new-btn:hover { background: #3b7de8; }

/* 搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.search-input-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 0 12px;
  height: 36px;
}

.search-icon {
  font-size: 14px;
  margin-right: 6px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: 14px;
  color: #333;
}

.search-clear {
  cursor: pointer;
  color: #999;
  font-size: 14px;
  margin-left: 4px;
}

.search-btn {
  padding: 6px 14px;
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
.search-btn:hover:not(:disabled) { background: #3b7de8; }
.search-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 搜索结果头 */
.search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #eef3ff;
  font-size: 13px;
  color: #555;
  flex-shrink: 0;
}

.back-btn {
  padding: 4px 12px;
  background: none;
  border: 1px solid #4f8ef7;
  color: #4f8ef7;
  border-radius: 14px;
  font-size: 12px;
  cursor: pointer;
}

/* 搜索结果列表 */
.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.search-item {
  background: #fff;
  margin: 4px 12px;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  transition: box-shadow 0.2s;
}
.search-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

.search-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.search-session-title {
  font-size: 13px;
  font-weight: 500;
  color: #444;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.search-role-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  flex-shrink: 0;
  margin-left: 8px;
}
.search-role-tag.user {
  background: #e8f0fe;
  color: #4f8ef7;
}
.search-role-tag.assistant {
  background: #e6f7e6;
  color: #52c41a;
}

.search-snippet {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  word-break: break-word;
}

.search-snippet :deep(mark) {
  background: #fff3b0;
  color: #333;
  padding: 0 2px;
  border-radius: 2px;
}

.search-item-time {
  font-size: 11px;
  color: #bbb;
  margin-top: 4px;
}

.error-bar {
  background: #fff2f0;
  color: #ff4d4f;
  padding: 8px 16px;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.close-err { cursor: pointer; }

.loading-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #bbb;
  font-size: 14px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e0e0e0;
  border-top-color: #4f8ef7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #bbb;
}
.empty-icon { font-size: 52px; }
.empty-wrap p { font-size: 15px; margin: 0; }

.start-btn {
  padding: 10px 28px;
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 15px;
  cursor: pointer;
  margin-top: 4px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.session-item {
  background: #fff;
  margin: 4px 12px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  transition: box-shadow 0.2s;
}
.session-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.session-item.active { border-left: 3px solid #4f8ef7; }

.session-content {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  cursor: pointer;
  gap: 10px;
}

.session-icon { font-size: 24px; flex-shrink: 0; }

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: #222;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}
.session-time { font-size: 12px; color: #bbb; }
.session-count { font-size: 12px; color: #aaa; }

.session-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 16px;
  transition: background 0.15s;
}
.action-btn:hover { background: #f0f0f0; }

.edit-mode {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
}

.edit-input {
  flex: 1;
  border: 1px solid #4f8ef7;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
  outline: none;
}

.edit-save {
  padding: 6px 12px;
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.edit-cancel {
  padding: 6px 12px;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal {
  background: #fff;
  border-radius: 16px;
  width: 280px;
  padding: 24px 20px 20px;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #222;
  margin-bottom: 10px;
}

.modal-body {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.modal-footer {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  justify-content: flex-end;
}

.modal-cancel {
  padding: 8px 20px;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  background: none;
  font-size: 14px;
  cursor: pointer;
  color: #666;
}

.modal-confirm {
  padding: 8px 20px;
  border: none;
  border-radius: 20px;
  background: #ff4d4f;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
</style>
