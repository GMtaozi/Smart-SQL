<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside :width="isCollapsed ? '64px' : '240px'" class="sidebar">
      <div class="logo-area">
        <div class="logo-icon">SQL</div>
        <span v-show="!isCollapsed" class="logo-text">智能SQL助手</span>
      </div>

      <el-menu
        :default-active="currentRoute"
        class="sidebar-menu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能问答</template>
        </el-menu-item>

        <el-menu-item index="/datasource">
          <el-icon><Connection /></el-icon>
          <template #title>数据源</template>
        </el-menu-item>

        <el-menu-item index="/ai-model">
          <el-icon><Cpu /></el-icon>
          <template #title>AI 模型</template>
        </el-menu-item>

        <el-menu-item index="/terminology">
          <el-icon><Notebook /></el-icon>
          <template #title>术语管理</template>
        </el-menu-item>

        <el-menu-item index="/training">
          <el-icon><DocumentCopy /></el-icon>
          <template #title>SQL 训练</template>
        </el-menu-item>

        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <template #title>历史记录</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-tooltip :content="isCollapsed ? '展开' : '收起'" placement="right">
          <el-button text @click="toggleCollapse">
            <el-icon v-if="isCollapsed"><DArrowRight /></el-icon>
            <el-icon v-else><DArrowLeft /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </el-aside>

    <!-- Main Content -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleUserCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  ChatDotRound,
  Connection,
  Cpu,
  Notebook,
  DocumentCopy,
  Clock,
  DArrowLeft,
  DArrowRight,
  ArrowDown,
  SwitchButton,
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isCollapsed = ref(false)

const currentRoute = computed(() => route.path)
const username = computed(() => authStore.user?.username || 'User')

const pageTitles: Record<string, string> = {
  '/chat': '智能问答',
  '/datasource': '数据源管理',
  '/ai-model': 'AI 模型配置',
  '/terminology': '术语管理',
  '/training': 'SQL 训练',
  '/history': '查询历史',
}

const pageTitle = computed(() => pageTitles[currentRoute.value] || '智能SQL助手')

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const handleMenuSelect = (index: string) => {
  router.push(index)
}

const handleUserCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  background: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #1cba90, #2dd4bf);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: bold;
  font-size: 14px;
}

.logo-text {
  margin-left: 12px;
  font-size: 18px;
  font-weight: 600;
  color: #1cba90;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 12px 0;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 240px;
}

.sidebar-menu .el-menu-item {
  margin: 4px 12px;
  border-radius: 8px;
  height: 48px;
}

.sidebar-menu .el-menu-item:hover {
  background: #f0fdf7;
}

.sidebar-menu .el-menu-item.is-active {
  background: #e6f7f2;
  color: #1cba90;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1cba90;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #333;
}

.main-content {
  padding: 24px;
  overflow-y: auto;
}
</style>
