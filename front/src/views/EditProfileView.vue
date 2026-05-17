<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { updateUserInfo, uploadAvatar } from '@/api/user'
import request from '@/api/request'

const router = useRouter()
const userStore = useUserStore()

const form = ref({
  nickname: '',
  bio: '',
})
const saving = ref(false)
const uploading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// 默认头像
const DEFAULT_AVATAR = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'

// 当前显示的头像URL
const currentAvatar = computed(() => userStore.userInfo?.avatar || DEFAULT_AVATAR)

onMounted(() => {
  const info = userStore.userInfo
  if (info) {
    form.value.nickname = info.nickname || ''
    form.value.bio = info.bio || ''
  }
})

// 触发文件选择
const fileInput = ref(null)
function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return

  // 前端校验
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    errorMsg.value = '仅支持 JPG/PNG/GIF/WebP 格式的图片'
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    errorMsg.value = '图片大小不能超过 2MB'
    return
  }

  errorMsg.value = ''
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    // 直接用 axios 发送 multipart/form-data
    const res = await request.post('/user/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    // 更新本地用户信息
    userStore.setUserInfo({
      ...userStore.userInfo,
      avatar: res.data?.avatar || res.data?.userInfo?.avatar,
    })
    successMsg.value = '头像上传成功'
    setTimeout(() => { successMsg.value = '' }, 2000)
  } catch (e) {
    errorMsg.value = e.message || '头像上传失败，请重试'
  } finally {
    uploading.value = false
    // 重置 input 以便同一文件可再次选择
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function handleSave() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!form.value.nickname.trim()) {
    errorMsg.value = '昵称不能为空'
    return
  }
  saving.value = true
  try {
    const res = await updateUserInfo({
      nickname: form.value.nickname.trim(),
      bio: form.value.bio.trim(),
    })
    // 更新本地用户信息
    userStore.setUserInfo({
      ...userStore.userInfo,
      nickname: form.value.nickname.trim(),
      bio: form.value.bio.trim(),
    })
    successMsg.value = '保存成功'
    setTimeout(() => router.back(), 800)
  } catch (e) {
    errorMsg.value = e.message || '保存失败，请重试'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="edit-profile-view">
    <!-- 顶部栏 -->
    <header class="header">
      <button class="back-btn" @click="router.back()">‹</button>
      <h1 class="title">编辑资料</h1>
      <button class="save-btn" :disabled="saving" @click="handleSave">
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </header>

    <div class="content">
      <!-- 头像区域：点击上传 -->
      <div class="avatar-section" @click="triggerUpload">
        <div class="avatar-wrap">
          <img :src="currentAvatar" class="avatar avatar-img" />
          <div class="avatar-overlay">
            <span v-if="uploading" class="upload-spinner">⏳</span>
            <span v-else class="upload-icon">📷</span>
          </div>
        </div>
        <div class="avatar-label">{{ uploading ? '上传中...' : '点击更换头像' }}</div>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          class="hidden-input"
          @change="handleFileChange"
        />
      </div>

      <!-- 表单 -->
      <div class="form-section">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <div class="form-value disabled">{{ userStore.userInfo?.username }}</div>
        </div>
        <div class="form-item">
          <label class="form-label">昵称</label>
          <input
            v-model="form.nickname"
            class="form-input"
            placeholder="请输入昵称"
            maxlength="20"
          />
        </div>
        <div class="form-item">
          <label class="form-label">个人简介</label>
          <textarea
            v-model="form.bio"
            class="form-textarea"
            placeholder="介绍一下自己吧..."
            rows="3"
            maxlength="100"
          />
          <div class="char-count">{{ form.bio.length }}/100</div>
        </div>
      </div>

      <!-- 消息提示 -->
      <div v-if="errorMsg" class="msg error">{{ errorMsg }}</div>
      <div v-if="successMsg" class="msg success">{{ successMsg }}</div>
    </div>
  </div>
</template>

<style scoped>
.edit-profile-view {
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

.save-btn {
  background: #4f8ef7;
  color: #fff;
  border: none;
  border-radius: 16px;
  padding: 7px 16px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}
.save-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

/* 头像区域 */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
  cursor: pointer;
}

.avatar-wrap {
  position: relative;
  width: 80px;
  height: 80px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f8ef7, #6fa8ff);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
}

.avatar-img {
  object-fit: cover;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-wrap:hover .avatar-overlay {
  opacity: 1;
}

.upload-icon,
.upload-spinner {
  font-size: 24px;
}

.avatar-label {
  margin-top: 8px;
  font-size: 13px;
  color: #4f8ef7;
}

.hidden-input {
  display: none;
}

/* 表单 */
.form-section {
  background: #fff;
  margin: 0 12px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
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

.form-input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  color: #333;
  font-family: inherit;
  background: transparent;
  box-sizing: border-box;
}

.form-value.disabled {
  font-size: 15px;
  color: #aaa;
}

.form-textarea {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  color: #333;
  font-family: inherit;
  resize: none;
  line-height: 1.6;
  background: transparent;
  box-sizing: border-box;
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #ccc;
  margin-top: 4px;
}

.msg {
  margin: 16px 12px 0;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  text-align: center;
}
.msg.error { background: #fff2f0; color: #ff4d4f; }
.msg.success { background: #f6ffed; color: #52c41a; }
</style>
