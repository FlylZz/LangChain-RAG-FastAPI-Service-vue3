<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { name: 'chat',     label: 'AI问答',   icon: '💬' },
  { name: 'sessions', label: '会话管理', icon: '📋' },
  { name: 'profile',  label: '我的',     icon: '👤' },
]

const activeTab = computed(() => route.name)

function goTab(name) {
  if (activeTab.value !== name) router.push({ name })
}
</script>

<template>
  <div class="home-layout">
    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 底部 TabBar -->
    <nav class="tab-bar">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        class="tab-item"
        :class="{ active: activeTab === tab.name }"
        @click="goTab(tab.name)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>
  </div>
</template>

<style scoped>
.home-layout {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: #f5f6fa;
  max-width: 480px;
  margin: 0 auto;
  position: relative;
  overflow: hidden;
}

.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-bar {
  display: flex;
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding: 6px 0 env(safe-area-inset-bottom, 6px);
  flex-shrink: 0;
  z-index: 100;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: 4px 0;
  transition: color 0.2s;
  color: #999;
  user-select: none;
}

.tab-item.active {
  color: #4f8ef7;
}

.tab-icon {
  font-size: 22px;
  line-height: 1;
}

.tab-label {
  font-size: 11px;
  font-weight: 500;
}
</style>
