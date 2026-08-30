<template>
  <div class="app-layout">
    <!-- 1. 侧边导航栏 -->
    <aside class="sidebar">
      <!-- 品牌区域 -->
      <div class="brand">
        <div class="logo-box">
          <span class="logo-text">SAU</span>
        </div>
        <div class="brand-info">
          <div class="brand-title">Social Auto</div>
          <div class="brand-desc">矩阵发布桌面端</div>
        </div>
      </div>

      <!-- 导航项列表 -->
      <nav class="nav-menu">
        <router-link to="/" class="nav-link" exact-active-class="active">
          <div class="nav-icon">
            <el-icon><Upload /></el-icon>
          </div>
          <span class="nav-text">发布中心</span>
        </router-link>

        <router-link to="/accounts" class="nav-link" exact-active-class="active">
          <div class="nav-icon">
            <el-icon><User /></el-icon>
          </div>
          <span class="nav-text">平台账号管理</span>
        </router-link>

        <router-link to="/dashboard" class="nav-link" exact-active-class="active">
          <div class="nav-icon">
            <el-icon><DataLine /></el-icon>
          </div>
          <span class="nav-text">数据大盘</span>
        </router-link>

        <router-link to="/settings" class="nav-link" exact-active-class="active">
          <div class="nav-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <span class="nav-text">系统设置</span>
        </router-link>
      </nav>

      <!-- 侧边栏底部状态指示器 -->
      <div class="sidebar-footer">
        <div class="engine-status">
          <div class="status-indicator">
            <span class="pulse-dot"></span>
          </div>
          <div class="status-info">
            <span class="status-title">Sidecar 引擎</span>
            <span class="status-sub">Patchright 就绪</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 2. 主页面工作区 -->
    <main class="main-wrapper">
      <!-- 顶部 Header 状态栏 -->
      <header class="top-nav">
        <div class="nav-breadcrumb">
          <span class="parent">工作台</span>
          <span class="separator">/</span>
          <span class="current">{{ currentRouteTitle }}</span>
        </div>

        <div class="nav-actions">
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

      <!-- 3. 底部终端控制台抽屉 -->
      <div class="console-drawer" :class="{ collapsed: !showConsole }">
        <div class="console-header" @click="showConsole = !showConsole">
          <div class="console-header-left">
            <el-icon><Monitor /></el-icon>
            <span class="console-title">引擎实时控制台日志 (Stdout Event Bridge)</span>
            <el-tag size="small" effect="dark" round class="log-tag">
              {{ logs.length }} 条记录
            </el-tag>
          </div>
          <div class="console-header-right">
            <el-button link size="small" type="danger" @click.stop="clearLogs">清空</el-button>
            <el-icon class="toggle-icon">{{ showConsole ? '▼' : '▲' }}</el-icon>
          </div>
        </div>

        <div class="console-body" ref="logContainer" v-show="showConsole">
          <div v-if="logs.length === 0" class="empty-logs">
            <el-icon><InfoFilled /></el-icon>
            <span>暂无后台任务运行日志，点击发布后将在此处实时打出执行细节</span>
          </div>
          <div v-for="(log, idx) in logs" :key="idx" class="log-item" :class="log.type">
            <span class="time">{{ log.time }}</span>
            <span class="content">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './stores/themeStore'
import { useAuthStore } from './stores/authStore'
import { Medal, Lock, Monitor, Moon, Sunny, InfoFilled } from '@element-plus/icons-vue'
import AuthModal from './components/AuthModal.vue'
import { EventsOn, EventsOff } from '../wailsjs/runtime/runtime'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const currentRouteTitle = computed(() => (route.meta.title as string) || '控制台')

const showConsole = ref(true)
const logs = ref<Array<{ time: string; type: string; message: string }>>([])
const logContainer = ref<HTMLElement | null>(null)

const clearLogs = () => {
  logs.value = []
}

// 清洗 ANSI Escape 颜色转义字符
const cleanAnsiString = (str: string): string => {
  if (!str) return ''
  return str
    .replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
    .replace(/\r/g, '')
    .trim()
}

onMounted(() => {
  // 初始化云端授权数据
  authStore.refreshAuth()

  EventsOn('sau-log', (evt: any) => {
    const timeStr = new Date().toLocaleTimeString()
    let type = 'log'
    let rawMsg = ''

    if (typeof evt === 'string') {
      rawMsg = evt
    } else if (evt && evt.message) {
      rawMsg = evt.message
      type = evt.type || 'log'
    }

    const cleanMsg = cleanAnsiString(rawMsg)
    if (!cleanMsg) return

    logs.value.push({
      time: timeStr,
      type: type,
      message: cleanMsg
    })

    if (logs.value.length > 500) {
      logs.value.shift()
    }

    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  })
})

onUnmounted(() => {
  EventsOff('sau-log')
})
</script>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  background-color: var(--bg-app);
}

/* 侧边栏 */
.sidebar {
  width: 240px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: background-color 0.25s ease, border-color 0.25s ease;
}

.brand {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo-box {
  width: 42px;
  height: 42px;
  background: var(--primary-gradient);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
}

.logo-text {
  font-weight: 800;
  font-size: 15px;
  color: #fff;
  letter-spacing: -0.5px;
}

.brand-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.brand-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.nav-menu {
  flex: 1;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-icon {
  font-size: 18px;
  display: flex;
  align-items: center;
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
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
}

.engine-status {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 10px 14px;
  border-radius: 10px;
}

.pulse-dot {
  display: block;
  width: 8px;
  height: 8px;
  background: var(--status-success);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--status-success);
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.status-sub {
  font-size: 10px;
  color: var(--status-success);
}

/* 主内容区 */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-nav {
  height: 56px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-header);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: background-color 0.25s ease, border-color 0.25s ease;
}

.nav-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
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
  gap: 12px;
}

.auth-status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.auth-status-pill:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}

.pill-active {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(5, 150, 105, 0.1));
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #10b981;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15);
}

.pill-inactive {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.16), rgba(220, 38, 38, 0.08));
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #ef4444;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.12);
  animation: pulse-border 2s infinite ease-in-out;
}

@keyframes pulse-border {
  0%, 100% {
    border-color: rgba(239, 68, 68, 0.35);
  }
  50% {
    border-color: rgba(239, 68, 68, 0.7);
  }
}

.theme-toggle-btn {
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-main) !important;
  background: var(--bg-card) !important;
  transition: all 0.2s ease;
}

.theme-toggle-btn:hover {
  transform: rotate(15deg);
  border-color: var(--primary-color) !important;
  color: var(--primary-color) !important;
}

.page-content {
  flex: 1;
  padding: 24px 28px;
  overflow-y: auto;
}

/* 底部终端控制台 */
.console-drawer {
  background: var(--bg-console);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  height: 220px;
  transition: height 0.25s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.25s ease;
}

.console-drawer.collapsed {
  height: 38px;
}

.console-header {
  height: 38px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-console-header);
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
  transition: background-color 0.25s ease;
}

.console-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

.log-tag {
  background: rgba(99, 102, 241, 0.15) !important;
  border: 1px solid rgba(99, 102, 241, 0.35) !important;
  color: var(--primary-color) !important;
}

.console-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-icon {
  font-size: 10px;
  color: var(--text-muted);
}

.console-body {
  flex: 1;
  padding: 12px 18px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  color: var(--text-disabled);
  font-size: 12px;
}

.log-item {
  display: flex;
  gap: 10px;
  color: var(--text-console);
  margin-bottom: 2px;
}

.log-item.error {
  color: var(--status-danger) !important;
}

.log-item.success {
  color: var(--status-success) !important;
}

.log-item .time {
  color: var(--text-console-time);
  user-select: none;
}
</style>
