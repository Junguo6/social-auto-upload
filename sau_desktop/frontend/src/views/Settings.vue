<template>
  <div class="settings-workspace">
    <!-- 头部标题 -->
    <div class="workspace-header">
      <div class="header-left">
        <h2 class="workspace-title">系统参数与运行设置</h2>
        <span class="workspace-subtitle">配置全局自动化并发窗口、浏览器引擎内核与系统缓存数据维护</span>
      </div>
      <div class="header-right">
        <el-button size="default" type="info" plain @click="handleReset">
          <el-icon><RefreshRight /></el-icon>
          <span>恢复默认设置</span>
        </el-button>
        <el-button size="default" type="primary" class="gradient-btn" @click="handleSave">
          <el-icon><Check /></el-icon>
          <span>保存配置</span>
        </el-button>
      </div>
    </div>

    <div class="settings-body">
      <!-- 1. 并发与自动化调度设置 -->
      <el-card class="glass-card setting-section">
        <template #header>
          <div class="section-title">
            <el-icon><Cpu /></el-icon>
            <span>自动化调度与并发性能</span>
          </div>
        </template>

        <div class="setting-list">
          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">同时发布窗口数 (并发数)</span>
              <span class="desc">控制矩阵发布时同时自动操作的浏览器窗口数量。数值越大分发越快，建议根据电脑内存配置调整（推荐 2~3）。</span>
            </div>
            <div class="setting-control slider-box">
              <el-slider 
                v-model="form.concurrency" 
                :min="1" 
                :max="5" 
                :step="1" 
                show-stops 
                style="width: 160px"
              />
              <span class="slider-val">{{ form.concurrency }} 个窗口</span>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">默认运行模式</span>
              <span class="desc">后台静默执行可大幅节省图形渲染显存；弹出可见窗口便于调试和观察自动化模拟行为。</span>
            </div>
            <div class="setting-control">
              <el-switch 
                v-model="form.headless" 
                active-text="后台无头静默 (推荐日常批量)" 
                inactive-text="弹出可见浏览器 (推荐初次调试)" 
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">发布遇阻自动重试次数</span>
              <span class="desc">当因网络抖动或页面元素加载偶发超时时，自动重新尝试执行的次数。</span>
            </div>
            <div class="setting-control">
              <el-input-number v-model="form.autoRetryCount" :min="0" :max="3" size="default" />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">自动化浏览器内核与运行环境</span>
              <span class="desc">{{ browserInfo?.summary || '正在探测本地自动化浏览器内核环境...' }}</span>
            </div>
            <div class="setting-control" style="display: flex; align-items: center; gap: 8px;">
              <el-tag :type="browserInfo?.isReady ? 'success' : 'danger'" size="default" effect="dark">
                {{ browserInfo?.isReady ? (browserInfo.browserType === 'bundled_chromium' ? '✅ 内置绿色 Chromium' : '✅ 系统原生浏览器') : '❌ 未就绪' }}
              </el-tag>
              <el-button size="small" type="primary" link @click="checkBrowser">
                <el-icon><RefreshRight /></el-icon> 重新检测
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 2. 本地存储与关于 -->
      <el-card class="glass-card setting-section">
        <template #header>
          <div class="section-title">
            <el-icon><InfoFilled /></el-icon>
            <span>关于软件与数据维护</span>
          </div>
        </template>

        <div class="setting-list">
          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">软件版本信息</span>
              <span class="desc">Social Auto Upload Matrix Client - Wails 原生桌面端</span>
            </div>
            <div class="setting-control">
              <el-tag size="default" type="success" effect="dark">v1.2.0 Pro Edition</el-tag>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">设备识别码 (NewSN) 与授权</span>
              <span class="desc">机器唯一标识：<code style="color: #38bdf8; font-weight: bold;">{{ authStore.overview.new_sn || '加载中...' }}</code></span>
            </div>
            <div class="setting-control">
              <el-button type="primary" plain size="small" @click="authStore.openAuthModal">
                <el-icon><Key /></el-icon>
                <span>管理授权 / 激活</span>
              </el-button>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-meta">
              <span class="title">清除本地缓存数据</span>
              <span class="desc">清空本地历史发布任务记录与界面缓存，不会删除已保存的 Cookie 凭证。</span>
            </div>
            <div class="setting-control">
              <el-button type="danger" plain size="small" @click="handleClearHistory">
                清空任务历史
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Key } from '@element-plus/icons-vue'
import { DetectBrowserStatus } from '../../wailsjs/go/main/App'
import { useSettingsStore } from '../stores/settingsStore'
import { usePublishStore } from '../stores/publishStore'
import { useAuthStore } from '../stores/authStore'

const settingsStore = useSettingsStore()
const publishStore = usePublishStore()
const authStore = useAuthStore()

const browserInfo = ref<any>(null)

const checkBrowser = async () => {
  try {
    browserInfo.value = await DetectBrowserStatus()
  } catch (err) {
    console.error('检测浏览器内核失败:', err)
  }
}

const form = reactive({
  concurrency: 3,
  headless: false,
  autoRetryCount: 1,
  chromePath: ''
})

onMounted(() => {
  form.concurrency = settingsStore.settings.concurrency
  form.headless = settingsStore.settings.headless
  form.autoRetryCount = settingsStore.settings.autoRetryCount
  form.chromePath = settingsStore.settings.chromePath
  checkBrowser()
})

const handleSave = () => {
  settingsStore.updateSettings({
    concurrency: form.concurrency,
    headless: form.headless,
    autoRetryCount: form.autoRetryCount,
    chromePath: form.chromePath
  })
  ElMessage.success('🎉 系统设置已成功保存并立即生效！')
}

const handleReset = () => {
  ElMessageBox.confirm('确定要将所有设置恢复为出厂默认值吗？', '提示', {
    type: 'warning'
  }).then(() => {
    settingsStore.resetSettings()
    form.concurrency = settingsStore.settings.concurrency
    form.headless = settingsStore.settings.headless
    form.autoRetryCount = settingsStore.settings.autoRetryCount
    form.chromePath = settingsStore.settings.chromePath
    ElMessage.success('已恢复为默认设置')
  }).catch(() => {})
}

const handleClearHistory = () => {
  ElMessageBox.confirm('确定要清空所有历史发布记录吗？', '警告', {
    type: 'warning'
  }).then(() => {
    publishStore.taskHistory = []
    ElMessage.success('历史发布记录已清空')
  }).catch(() => {})
}
</script>

<style scoped>
.settings-workspace {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.workspace-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
}

.workspace-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  display: block;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.setting-section {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.setting-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  transition: all 0.2s ease;
}

.setting-item:hover {
  border-color: var(--border-highlight);
}

.setting-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-right: 24px;
}

.setting-meta .title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.setting-meta .desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.5;
}

.setting-control {
  flex-shrink: 0;
}

.slider-box {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-color);
  min-width: 60px;
}
</style>
