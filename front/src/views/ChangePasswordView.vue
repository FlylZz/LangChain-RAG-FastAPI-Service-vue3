<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSessionStore } from '@/stores/session'
import { changePassword } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()
const sessionStore = useSessionStore()

const form = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const showOld = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

function validate() {
  if (!form.value.old_password) {
    errorMsg.value = '请输入当前密码'
    return false
  }
  if (!form.value.new_password) {
    errorMsg.value = '请输入新密码'
    return false
  }
  if (form.value.new_password.length < 6) {
    errorMsg.value = '新密码至少6位'
    return false
  }
  if (form.value.new_password !== form.value.confirm_password) {
    errorMsg.value = '两次输入的密码不一致'
    return false
  }
  return true
}

async function handleSubmit() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validate()) return
  saving.value = true
  try {
    await changePassword({
      old_password: form.value.old_password,
      new_password: form.value.new_password,
    })
    successMsg.value = '密码修改成功，请重新登录'
    setTimeout(() => {
      userStore.logout()
      sessionStore.clearSession()
      router.replace({ name: 'login' })
    }, 1500)
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '修改失败，请检查当前密码是否正确'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="change-password-view">
    <!-- 顶部栏 -->
    <header class="header">
      <button class="back-btn" @click="router.back()">‹</button>
      <h1 class="title">修改密码</h1>
      <div style="width: 60px" />
    </header>

    <div class="content">
      <div class="form-section">
        <!-- 当前密码 -->
        <div class="form-item">
          <label class="form-label">当前密码</label>
          <div class="input-wrap">
            <input
              v-model="form.old_password"
              :type="showOld ? 'text' : 'password'"
              class="form-input"
              placeholder="请输入当前密码"
              autocomplete="current-password"
            />
            <button class="eye-btn" @click="showOld = !showOld">
              {{ showOld ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <!-- 新密码 -->
        <div class="form-item">
          <label class="form-label">新密码</label>
          <div class="input-wrap">
            <input
              v-model="form.new_password"
              :type="showNew ? 'text' : 'password'"
              class="form-input"
              placeholder="至少6位"
              autocomplete="new-password"
            />
            <button class="eye-btn" @click="showNew = !showNew">
              {{ showNew ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <!-- 确认密码 -->
        <div class="form-item">
          <label class="form-label">确认新密码</label>
          <div class="input-wrap">
            <input
              v-model="form.confirm_password"
              :type="showConfirm ? 'text' : 'password'"
              class="form-input"
              placeholder="再次输入新密码"
              autocomplete="new-password"
            />
            <button class="eye-btn" @click="showConfirm = !showConfirm">
              {{ showConfirm ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 提示 -->
      <div v-if="errorMsg" class="msg error">{{ errorMsg }}</div>
      <div v-if="successMsg" class="msg success">{{ successMsg }}</div>

      <!-- 提交按钮 -->
      <button
        class="submit-btn"
        :disabled="saving"
        @click="handleSubmit"
      >
        {{ saving ? '提交中...' : '确认修改' }}
      </button>

      <p class="tip">修改密码后将需要重新登录</p>
    </div>
  </div>
</template>

<style scoped>
.change-password-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f6fa;
}

.header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.back-btn {
  background: none;
  border: none;
  font-size: 26px;
  cursor: pointer;
  color: #333;
  padding: 0 8px 0 0;
  line-height: 1;
}

.title {
  flex: 1;
  font-size: 17px;
  font-weight: 700;
  color: #222;
  margin: 0;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 12px;
}

.form-section {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  margin-bottom: 16px;
}

.form-item {
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
}
.form-item:last-child { border-bottom: none; }

.form-label {
  display: block;
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.input-wrap {
  display: flex;
  align-items: center;
}

.form-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: #333;
  font-family: inherit;
  background: transparent;
  min-width: 0;
}

.eye-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 0 0 0 8px;
}

.msg {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  text-align: center;
  margin-bottom: 12px;
}
.msg.error { background: #fff2f0; color: #ff4d4f; }
.msg.success { background: #f6ffed; color: #52c41a; }

.submit-btn {
  width: 100%;
  padding: 14px;
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}
.submit-btn:hover:not(:disabled) { background: #3b7de8; }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.tip {
  text-align: center;
  font-size: 12px;
  color: #bbb;
  margin-top: 12px;
}
</style>
