<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSessionStore } from '@/stores/session'
import { getUserInfo } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()
const sessionStore = useSessionStore()

const loading = ref(false)

const userInfo = computed(() => userStore.userInfo)

const DEFAULT_AVATAR = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'

const avatarUrl = computed(() => userInfo.value?.avatar || DEFAULT_AVATAR)

async function refreshUserInfo() {
  loading.value = true
  try {
    const res = await getUserInfo()
    userStore.setUserInfo(res.data)
  } catch (e) {
    console.error('获取用户信息失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(refreshUserInfo)

function handleLogout() {
  if (!confirm('确定退出登录吗？')) return
  userStore.logout()
  sessionStore.clearSession()
  router.replace({ name: 'login' })
}

const menuItems = [
  { icon: '✏️', label: '编辑资料', action: () => router.push({ name: 'editProfile' }) },
  { icon: '🔒', label: '修改密码', action: () => router.push({ name: 'changePassword' }) },
]
</script>

<template>
  <div class="profile-view">
    <!-- 顶部栏 -->
    <header class="header">
      <h1 class="title">我的</h1>
    </header>

    <div class="content">
      <!-- 用户信息卡片 -->
      <div class="user-card">
        <img
          :src="avatarUrl"
          class="avatar avatar-img"
          @error="$event.target.src = DEFAULT_AVATAR"
        />
        <div class="user-detail">
          <div class="username">{{ userInfo?.nickname || userInfo?.username || '用户' }}</div>
          <div class="user-id">@{{ userInfo?.username }}</div>
          <div v-if="userInfo?.bio" class="user-bio">{{ userInfo.bio }}</div>
        </div>
      </div>

      <!-- 功能菜单 -->
      <div class="menu-section">
        <div class="section-title">账号管理</div>
        <div class="menu-list">
          <div
            v-for="item in menuItems"
            :key="item.label"
            class="menu-item"
            @click="item.action()"
          >
            <span class="menu-icon">{{ item.icon }}</span>
            <span class="menu-label">{{ item.label }}</span>
            <span class="menu-arrow">›</span>
          </div>
        </div>
      </div>

      <!-- 退出登录 -->
      <div class="logout-section">
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f6fa;
}

.header {
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

.content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

/* 用户信息卡片 */
.user-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  margin: 0 12px 16px;
  padding: 20px 16px;
  border-radius: 16px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f8ef7, #6fa8ff);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
  flex-shrink: 0;
}

.avatar-img {
  object-fit: cover;
}

.user-detail {
  flex: 1;
  min-width: 0;
}

.username {
  font-size: 18px;
  font-weight: 700;
  color: #222;
}

.user-id {
  font-size: 13px;
  color: #999;
  margin-top: 2px;
}

.user-bio {
  font-size: 13px;
  color: #666;
  margin-top: 6px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 功能菜单 */
.menu-section {
  margin: 0 12px 16px;
}

.section-title {
  font-size: 12px;
  color: #aaa;
  padding: 0 4px;
  margin-bottom: 6px;
  font-weight: 500;
}

.menu-list {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 15px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}
.menu-item:last-child { border-bottom: none; }
.menu-item:hover { background: #f8f8f8; }

.menu-icon { font-size: 20px; margin-right: 12px; }
.menu-label { flex: 1; font-size: 15px; color: #333; }
.menu-arrow { color: #ccc; font-size: 18px; }

/* 退出登录 */
.logout-section {
  margin: 0 12px;
}

.logout-btn {
  width: 100%;
  padding: 14px;
  background: #fff;
  color: #ff4d4f;
  border: none;
  border-radius: 16px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  transition: background 0.15s;
}
.logout-btn:hover { background: #fff2f0; }
</style>
