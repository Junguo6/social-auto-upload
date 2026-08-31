<template>
  <div class="app-layout">
    <!-- 1. 侧边导航栏 (可折叠) -->
    <aside class="sidebar" :class="{ collapsed: isSidebarCollapsed }">
      <!-- 品牌区域 -->
      <div class="brand">
        <div class="logo-box">
          <span class="logo-text">SAU</span>
        </div>
        <div class="brand-info" v-if="!isSidebarCollapsed">
          <div class="brand-title">Social Auto</div>
          <div class="brand-desc">矩阵发布桌面端</div>
        </div>
      </div>

      <!-- 导航项列表 -->
      <nav class="nav-menu">
        <!-- 发布中心 -->
        <el-tooltip :content="'发布工作台'" placement="right" :disabled="!isSidebarCollapsed">
          <router-link to="/" class="nav-link" exact-active-class="active">
            <div class="nav-icon">
              <el-icon><Upload /></el-icon>
            </div>
            <span class="nav-text" v-if="!isSidebarCollapsed">发布工作台</span>
          </router-link>
        </el-tooltip>

        <!-- 任务管理中心 -->
        <el-tooltip :content="'任务管理中心'" placement="right" :disabled="!isSidebarCollapsed">
          <router-link to="/tasks" class="nav-link" exact-active-class="active">
            <div class="nav-icon nav-icon-badge-box">
              <el-icon><List /></el-icon>
              <span class="task-badge-dot" v-if="taskStore.activeTasksCount > 0"></span>
            </div>
            <span class="nav-text" v-if="!isSidebarCollapsed">任务管理中心</span>
            <span class="nav-badge" v-if="!isSidebarCollapsed && taskStore.activeTasksCount > 0">
              {{ taskStore.activeTasksCount }}
            </span>
          </router-link>
        </el-tooltip>

        <!-- 平台账号管理 -->
        <el-tooltip :content="'平台账号管理'" placement="right" :disabled="!isSidebarCollapsed">
          <router-link to="/accounts" class="nav-link" exact-active-class="active">
            <div class="nav-icon">
              <el-icon><User /></el-icon>
            </div>
            <span class="nav-text" v-if="!isSidebarCollapsed">平台账号管理</span>
          </router-link>
        </el-tooltip>

        <!-- 数据大盘 -->
        <el-tooltip :content="'数据概览大盘'" placement="right" :disabled="!isSidebarCollapsed">
          <router-link to="/dashboard" class="nav-link" exact-active-class="active">
            <div class="nav-icon">
              <el-icon><DataLine /></el-icon>
            </div>
            <span class="nav-text" v-if="!isSidebarCollapsed">数据概览大盘</span>
          </router-link>
        </el-tooltip>

        <!-- 系统设置 -->
        <el-tooltip :content="'系统运行设置'" placement="right" :disabled="!isSidebarCollapsed">
          <router-link to="/settings" class="nav-link" exact-active-class="active">
            <div class="nav-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <span class="nav-text" v-if="!isSidebarCollapsed">系统运行设置</span>
          </router-link>
        </el-tooltip>
      </nav>

      <!-- 侧边栏底部：引擎状态与折叠开关 -->
      <div class="sidebar-footer">
        <div class="engine-status" v-if="!isSidebarCollapsed">
          <div class="status-indicator">
            <span class="pulse-dot"></span>
          </div>
          <div class="status-info">
            <span class="status-title">Sidecar 引擎</span>
            <span class="status-sub">Patchright 就绪</span>
          </div>
        </div>

        <button 
          class="collapse-toggle-btn" 
          :title="isSidebarCollapsed ? '展开导航栏' : '收起导航栏'"
          @click="toggleSidebar"
        >
          <el-icon v-if="isSidebarCollapsed"><DArrowRight /></el-icon>
          <el-icon v-else><DArrowLeft /></el-icon>
        </button>
      </div>
    </aside>

    <!-- 2. 主页面工作区 (移除了底部笨重抽屉，空间最大化释放) -->
    <main class="main-wrapper">
      <!-- 顶部 Header 状态栏 -->
      <header class="top-nav">
        <div class="nav-breadcrumb">
          <span class="parent">工作台</span>
          <span class="separator">/</span>
          <span class="current">{{ currentRouteTitle }}</span>
        </div>

        <div class="nav-actions">
          <!-- 任务状态快捷胶囊 -->
          <router-link 
            to="/tasks" 
            class="top-task-pill" 
            v-if="taskStore.activeTasksCount > 0"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>后台执行中 ({{ taskStore.activeTasksCount }})</span>
          </router-link>

          <!-- 授权状态胶囊标签 -->
          <div 
            class="auth-status-pill" 
            :class="authStore.overview.is_activated ? 'pill-active' : 'pill-inactive'"
            @click="authStore.openAuthModal"
          >
            <el-icon v-if="authStore.overview.is_activated"><Medal /></el-icon>
            <el-icon v-else><Lock /></el-icon>
            <span class="pill-text">
              <template v-if="authStore.overview.is_activated">
                PRO 授权版 <span v-if="authStore.overview.days_remaining > 0">({{ authStore.overview.days_remaining }}天)</span>
              </template>
              <template v-else>
                未激活 (点击开通)
              </template>
            </span>
          </div>

          <!-- 明暗主题一键切换按钮 -->
          <el-tooltip :content="themeStore.isDark ? '切换至明亮浅色主题' : '切换至暗黑深色主题'" placement="bottom">
            <el-button 
              size="small" 
              class="theme-toggle-btn" 
              circle 
              @click="themeStore.toggleTheme"
            >
              <el-icon v-if="themeStore.isDark"><Sunny /></el-icon>
              <el-icon v-else><Moon /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </header>

      <!-- 页面主视图 -->
      <div class="page-content">
        <router-view />
      </div>

      <!-- 全局授权与激活弹窗 -->
      <AuthModal />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './stores/themeStore'
import { useAuthStore } from './stores/authStore'
import { useTaskStore } from './stores/taskStore'
import { Medal, Lock, Moon, Sunny } from '@element-plus/icons-vue'
import AuthModal from './components/AuthModal.vue'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const taskStore = useTaskStore()

const currentRouteTitle = computed(() => (route.meta.title as string) || '控制台')

// 侧边栏折叠状态持久化
const isSidebarCollapsed = ref(localStorage.getItem('sau_sidebar_collapsed') === 'true')

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem('sau_sidebar_collapsed', String(isSidebarCollapsed.value))
}

onMounted(() => {
  // 初始化云端授权数据
  authStore.refreshAuth()
  // 初始化任务事件监听
  taskStore.initEventListener()
})
</script>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  background-color: var(--bg-app);
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  width: 220px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.25s ease, border-color 0.25s ease;
  z-index: 10;
}

.sidebar.collapsed {
  width: 64px;
}

.brand {
  padding: 18px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 56px;
  box-sizing: border-box;
}

.logo-box {
  width: 36px;
  height: 36px;
  background: var(--primary-gradient);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.logo-text {
  font-weight: 800;
  font-size: 13px;
  color: #fff;
  letter-spacing: -0.5px;
}

.brand-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
  white-space: nowrap;
}

.brand-desc {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
  position: relative;
}

.sidebar.collapsed .nav-link {
  justify-content: center;
  padding: 10px 0;
}

.nav-icon {
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon-badge-box {
  position: relative;
}

.task-badge-dot {
  position: absolute;
  top: -2px;
  right: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  box-shadow: 0 0 6px #3b82f6;
}

.nav-text {
  white-space: nowrap;
  flex: 1;
}

.nav-badge {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: #3b82f6;
  padding: 0 6px;
  border-radius: 10px;
  line-height: 16px;
}

.nav-link:hover {
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
}

.nav-link.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
  color: var(--primary-color);
  font-weight: 700;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.sidebar-footer {
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar.collapsed .sidebar-footer {
  padding: 10px 6px;
}

.engine-status {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 6px 10px;
  border-radius: 8px;
}

.pulse-dot {
  display: block;
  width: 6px;
  height: 6px;
  background: var(--status-success);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--status-success);
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-main);
}

.status-sub {
  font-size: 9px;
  color: var(--status-success);
}

.collapse-toggle-btn {
  width: 100%;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.collapse-toggle-btn:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--primary-light);
  color: var(--primary-light);
}

/* 主内容区 */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.top-nav {
  height: 52px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-header);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  flex-shrink: 0;
}

.nav-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.nav-breadcrumb .parent {
  color: var(--text-muted);
}

.nav-breadcrumb .separator {
  color: var(--text-disabled);
}

.nav-breadcrumb .current {
  color: var(--text-main);
  font-weight: 700;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.top-task-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 16px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.35);
  color: #60a5fa;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}

.top-task-pill:hover {
  background: rgba(59, 130, 246, 0.25);
}

.auth-status-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.pill-active {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #10b981;
}

.pill-inactive {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #ef4444;
}

.theme-toggle-btn {
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-main) !important;
  background: var(--bg-card) !important;
}

.page-content {
  flex: 1;
  padding: 18px 24px;
  overflow: hidden;
  box-sizing: border-box;
}
</style>
