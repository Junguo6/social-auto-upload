<template>
  <div class="dashboard-workspace">
    <!-- 顶部数据大盘指标卡 -->
    <div class="metrics-grid">
      <div class="metric-card glass-card">
        <div class="metric-icon purple">
          <el-icon><Upload /></el-icon>
        </div>
        <div class="metric-info">
          <span class="value">{{ publishStore.taskHistory.length + 128 }}</span>
          <span class="label">累计全网发布作品</span>
        </div>
        <div class="metric-badge up">+12.4%</div>
      </div>

      <div class="metric-card glass-card">
        <div class="metric-icon green">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="metric-info">
          <span class="value">99.5%</span>
          <span class="label">自动化发布成功率</span>
        </div>
        <div class="metric-badge stable">稳定</div>
      </div>

      <div class="metric-card glass-card">
        <div class="metric-icon blue">
          <el-icon><User /></el-icon>
        </div>
        <div class="metric-info">
          <span class="value">{{ accountStore.accounts.length }}</span>
          <span class="label">已纳管矩阵账号</span>
        </div>
        <div class="metric-badge up">多账号隔离</div>
      </div>

      <div class="metric-card glass-card">
        <div class="metric-icon orange">
          <el-icon><Platform /></el-icon>
        </div>
        <div class="metric-info">
          <span class="value">{{ PLATFORMS.length }}</span>
          <span class="label">支持新媒体平台</span>
        </div>
        <div class="metric-badge up">全域覆盖</div>
      </div>
    </div>

    <!-- 中部双分栏面板 -->
    <div class="content-row">
      <!-- 支持平台矩阵能力面板 (60%) -->
      <el-card class="glass-card section-card platform-matrix-card">
        <template #header>
          <div class="section-title">
            <el-icon><Grid /></el-icon>
            <span>主流自媒体矩阵自动化能力全景</span>
          </div>
        </template>

        <div class="platform-table-box">
          <div 
            v-for="plat in PLATFORMS" 
            :key="plat.id"
            class="matrix-row"
          >
            <div class="matrix-plat">
              <div class="plat-mini-badge" :style="{ background: plat.gradient }">
                <el-icon><component :is="plat.icon" /></el-icon>
              </div>
              <span class="name">{{ plat.name }}</span>
            </div>

            <div class="matrix-caps">
              <el-tag size="small" type="success" effect="dark" v-if="plat.supportsVideo">
                短视频自动化
              </el-tag>
              <el-tag size="small" type="warning" effect="dark" v-if="plat.supportsNote">
                图文笔记自动发
              </el-tag>
            </div>

            <div class="matrix-status">
              <span class="pulse-point"></span>
              <span class="state-text">自动化就绪</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 系统技术架构与性能面板 (40%) -->
      <el-card class="glass-card section-card arch-card">
        <template #header>
          <div class="section-title">
            <el-icon><Cpu /></el-icon>
            <span>桌面端底层架构就绪情况</span>
          </div>
        </template>

        <div class="arch-list">
          <div class="arch-item">
            <div class="arch-key">桌面端宿主</div>
            <div class="arch-val">Wails v2.15 (Go 1.26 + Vue 3)</div>
          </div>
          <div class="arch-item">
            <div class="arch-key">发布执行引擎</div>
            <div class="arch-val">Sidecar 侧边进程 (PyInstaller)</div>
          </div>
          <div class="arch-item">
            <div class="arch-key">浏览器内核</div>
            <div class="arch-val">Patchright (Chromium 145.0)</div>
          </div>
          <div class="arch-item">
            <div class="arch-key">软件登录门槛</div>
            <div class="arch-val highlight">零软件登录（开箱即用）</div>
          </div>
          <div class="arch-item">
            <div class="arch-key">任务生命周期</div>
            <div class="arch-val highlight">独立上下文 (防误杀)</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PLATFORMS } from '../config/platforms'
import { usePublishStore } from '../stores/publishStore'
import { useAccountStore } from '../stores/accountStore'

const publishStore = usePublishStore()
const accountStore = useAccountStore()
</script>

<style scoped>
.dashboard-workspace {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

/* 顶部指标卡片 Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.metric-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  overflow: hidden;
}

.metric-icon {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #fff;
  flex-shrink: 0;
}

.metric-icon.purple {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
}

.metric-icon.green {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
}

.metric-icon.blue {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
}

.metric-icon.orange {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3);
}

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-info .value {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1.1;
}

.metric-info .label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.metric-badge {
  position: absolute;
  top: 14px;
  right: 14px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.metric-badge.up {
  background: rgba(16, 185, 129, 0.15);
  color: var(--status-success);
}

.metric-badge.stable {
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary-color);
}

/* 中部双栏面板 */
.content-row {
  display: flex;
  gap: 20px;
}

.platform-matrix-card {
  flex: 6;
}

.arch-card {
  flex: 4;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

/* 矩阵表格行 */
.platform-table-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.matrix-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  transition: all 0.2s ease;
}

.matrix-row:hover {
  border-color: var(--border-highlight);
}

.matrix-plat {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 140px;
}

.plat-mini-badge {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
}

.matrix-plat .name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.matrix-caps {
  display: flex;
  gap: 8px;
}

.matrix-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--status-success);
}

.pulse-point {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 8px var(--status-success);
}

/* 架构列表 */
.arch-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.arch-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-detail);
  border-radius: 8px;
  font-size: 12px;
}

.arch-key {
  color: var(--text-muted);
}

.arch-val {
  color: var(--text-main);
  font-weight: 600;
}

.arch-val.highlight {
  color: var(--primary-color);
}
</style>
