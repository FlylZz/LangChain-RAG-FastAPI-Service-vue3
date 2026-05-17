<template>
  <div class="auth-page">
    <div class="auth-header">
      <div class="logo">🤖</div>
      <h1 class="app-title">AI 智扫通</h1>
      <p class="app-sub">智能对话助手</p>
    </div>

    <div class="auth-card">
      <h2>注册账号</h2>

      <div class="form-group">
        <label>用户名</label>
        <input v-model="form.username" type="text" placeholder="2-20位用户名" />
      </div>

      <div class="form-group">
        <label>密码</label>
        <div class="input-wrap">
          <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="至少6位密码" />
          <span class="eye-btn" @click="showPassword = !showPassword">{{ showPassword ? '👁' : '👁‍🗨' }}</span>
        </div>
      </div>

      <div class="form-group">
        <label>确认密码</label>
        <div class="input-wrap">
          <input v-model="form.confirmPassword" :type="showConfirm ? 'text' : 'password'" placeholder="再次输入密码" @keyup.enter="handleRegister" />
          <span class="eye-btn" @click="showConfirm = !showConfirm">{{ showConfirm ? '👁' : '👁‍🗨' }}</span>
        </div>
      </div>

      <p v-if="errMsg" class="err-msg">{{ errMsg }}</p>

      <button class="btn-primary" :disabled="loading" @click="handleRegister">
        {{ loading ? '注册中...' : '注册' }}
      </button>

      <p class="auth-link">已有账号？<router-link to="/login">立即登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { userRegister } from '@/api/user.js'
import { useUserStore } from '@/stores/user.js'

const router = useRouter()
const userStore = useUserStore()
const form = reactive({ username: '', password: '', confirmPassword: '' })
const showPassword = ref(false)
const showConfirm = ref(false)
const loading = ref(false)
const errMsg = ref('')

async function handleRegister() {
  if (!form.username.trim() || !form.password.trim()) {
    errMsg.value = '请填写用户名和密码'
    return
  }
  if (form.username.length < 2) {
    errMsg.value = '用户名至少2位'
    return
  }
  if (form.password.length < 6) {
    errMsg.value = '密码至少6位'
    return
  }
  if (form.password !== form.confirmPassword) {
    errMsg.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  errMsg.value = ''
  try {
    const res = await userRegister({ username: form.username, password: form.password })
    userStore.setToken(res.data.token)
    userStore.setUserInfo(res.data.userInfo)
    router.replace('/home/chat')
  } catch (e) {
    errMsg.value = e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1677ff 0%, #4096ff 100%);
  padding: 20px;
}
.auth-header {
  text-align: center;
  margin-bottom: 32px;
  color: #fff;
}
.logo { font-size: 56px; margin-bottom: 8px; }
.app-title { font-size: 26px; font-weight: 700; margin: 0 0 4px; }
.app-sub { font-size: 14px; opacity: 0.85; margin: 0; }
.auth-card {
  background: #fff;
  border-radius: 16px;
  padding: 28px 24px 20px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.auth-card h2 { margin: 0 0 24px; font-size: 20px; color: #1a1a1a; text-align: center; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 6px; }
.form-group input {
  width: 100%; height: 44px; border: 1px solid #e0e0e0;
  border-radius: 10px; padding: 0 14px; font-size: 15px;
  outline: none; transition: border-color 0.2s; box-sizing: border-box;
}
.form-group input:focus { border-color: #1677ff; }
.input-wrap { position: relative; }
.input-wrap input { padding-right: 44px; }
.eye-btn {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  cursor: pointer; font-size: 18px; user-select: none; line-height: 1;
}
.err-msg { color: #ff4d4f; font-size: 13px; margin: -8px 0 12px; }
.btn-primary {
  width: 100%; height: 46px; background: #1677ff; color: #fff;
  border: none; border-radius: 10px; font-size: 16px; font-weight: 600;
  cursor: pointer; margin-top: 8px; transition: opacity 0.2s;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary:hover:not(:disabled) { opacity: 0.88; }
.auth-link { text-align: center; font-size: 14px; color: #666; margin: 16px 0 0; }
.auth-link a { color: #1677ff; text-decoration: none; font-weight: 500; }
</style>
