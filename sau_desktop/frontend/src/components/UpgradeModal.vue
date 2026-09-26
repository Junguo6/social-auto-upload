<template>
  <el-dialog
    v-model="upgradeStore.modalVisible"
    :title="dialogTitle"
    width="540px"
    :close-on-click-modal="!upgradeStore.isForced && !upgradeStore.isDownloading"
    :close-on-press-escape="!upgradeStore.isForced && !upgradeStore.isDownloading"
    :show-close="!upgradeStore.isForced && !upgradeStore.isDownloading"
    :before-close="handleBeforeClose"
    align-center
    class="upgrade-dialog"
  >
    <div class="upgrade-modal-content">
      <!-- 1. 版本对比卡片 -->
      <div class="version-banner">
        <div class="version-header-icon">
          <el-icon :size="28"><Promotion /></el-icon>
        </div>
        <div class="version-meta">
          <div class="version-title-row">
            <span class="version-text">v{{ upgradeStore.latestVersion }}</span>
            <el-tag v-if="upgradeStore.isForced" type="danger" size="small" effect="dark">
              重要更新
            </el-tag>
            <el-tag v-else type="success" size="small" effect="dark">
              新版可用
            </el-tag>
          </div>
          <div class="version-sub">
            当前版本: <code>v{{ upgradeStore.currentVersion }}</code>
            <span v-if="upgradeStore.versionInfo?.created_at" class="release-date">
              · 发布于 {{ formatDate(upgradeStore.versionInfo.created_at) }}
            </span>
          </div>
        </div>
      </div>

      <!-- 2. 更新日志描述 -->
      <div class="changelog-box" v-if="!upgradeStore.isDownloading && !upgradeStore.isCompleted">
        <div class="changelog-title">
          <el-icon><Document /></el-icon>
          <span>更新内容说明</span>
        </div>
        <div 
          class="changelog-content" 
          v-if="changelogHtml" 
          v-html="changelogHtml"
        ></div>
        <div class="changelog-content empty-desc" v-else>
          {{ upgradeStore.versionInfo?.brief || '本次更新包含性能提升与已知缺陷修复，建议升级。' }}
        </div>
      </div>

      <!-- 3. 下载进度状态展示 -->
      <div class="downloading-box" v-if="upgradeStore.isDownloading || upgradeStore.isCompleted">
        <div class="download-header">
          <div class="download-status-text">
            <span class="status-name" v-if="upgradeStore.isCompleted">
              🎉 升级包下载完成
            </span>
            <span class="status-name" v-else>
              正在下载更新包...
            </span>
            <span class="status-size" v-if="upgradeStore.downloadProgress.total_mb > 0">
              {{ upgradeStore.downloadProgress.downloaded_mb }} MB / {{ upgradeStore.downloadProgress.total_mb }} MB
            </span>
          </div>
          <span class="percent-tag">{{ upgradeStore.downloadProgress.percentage }}%</span>
        </div>

        <div class="progress-bar-wrap">
          <el-progress 
            :percentage="upgradeStore.downloadProgress.percentage" 
            :stroke-width="10" 
            :status="upgradeStore.isCompleted ? 'success' : undefined"
            :show-text="false" 
          />
        </div>

        <div class="download-tip">
          <template v-if="upgradeStore.isCompleted">
            升级安装包已准备就绪，点击下方按钮将自动解压替换并重启应用。
          </template>
          <template v-else>
            {{ upgradeStore.downloadProgress.message || '请保持网络通畅，下载完成后将自动提示安装...' }}
          </template>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <!-- 稍后更新（非强制更新且非下载中时显示） -->
        <el-button 
          v-if="!upgradeStore.isForced && !upgradeStore.isDownloading" 
          @click="upgradeStore.closeModal"
          size="default"
        >
          稍后提醒
        </el-button>

        <!-- 取消下载（下载中可取消） -->
        <el-button 
          v-if="upgradeStore.isDownloading" 
          type="info" 
          plain 
          @click="upgradeStore.cancelDownload"
          size="default"
        >
          取消下载
        </el-button>

        <!-- 立即更新（初始状态） -->
        <el-button 
          v-if="!upgradeStore.isDownloading && !upgradeStore.isCompleted" 
          type="primary" 
          class="gradient-btn"
          @click="upgradeStore.startDownload"
          size="default"
        >
          <el-icon><Download /></el-icon>
          <span>立即更新</span>
        </el-button>

        <!-- 立即安装重启（下载完成） -->
        <el-button 
          v-if="upgradeStore.isCompleted" 
          type="success" 
          :loading="upgradeStore.isInstalling"
          class="gradient-btn-success"
          @click="upgradeStore.applyUpdate"
          size="default"
        >
          <el-icon><Check /></el-icon>
          <span>立即安装生效</span>
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Promotion, Document, Download, Check } from '@element-plus/icons-vue'
import { useUpgradeStore } from '../stores/upgradeStore'

const upgradeStore = useUpgradeStore()

const dialogTitle = computed(() => {
  if (upgradeStore.isForced) {
    return '版本强制升级提醒'
  }
  return '发现新版本'
})

const changelogHtml = computed(() => {
  const desc = upgradeStore.versionInfo?.desc || ''
  return desc.trim()
})

const formatDate = (dateStr?: string) => {
  if (!dateStr) return ''
  return dateStr.split(' ')[0]
}

const handleBeforeClose = (done: () => void) => {
  if (upgradeStore.isForced || upgradeStore.isDownloading) {
    return
  }
  done()
}
</script>

<style scoped>
.upgrade-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

/* 版本卡片 */
.version-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}

.version-header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--primary-gradient, linear-gradient(135deg, #6366f1 0%, #a855f7 100%));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.version-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.version-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.version-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
}

.version-sub {
  font-size: 13px;
  color: var(--text-muted);
}

.version-sub code {
  color: var(--primary-color, #6366f1);
  font-weight: 600;
}

.release-date {
  color: var(--text-muted);
  margin-left: 4px;
}

/* 更新日志 */
.changelog-box {
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px;
  max-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.changelog-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.changelog-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-regular);
  overflow-y: auto;
  max-height: 170px;
  padding-right: 6px;
}

.changelog-content :deep(p),
.changelog-content :deep(span),
.changelog-content :deep(div),
.changelog-content :deep(li) {
  color: var(--text-regular);
  margin: 4px 0;
}

.changelog-content :deep(strong),
.changelog-content :deep(b),
.changelog-content :deep(h1),
.changelog-content :deep(h2),
.changelog-content :deep(h3),
.changelog-content :deep(h4) {
  color: var(--text-main);
  font-weight: 600;
}

.changelog-content :deep(ul), .changelog-content :deep(ol) {
  padding-left: 18px;
  margin: 4px 0;
}

.empty-desc {
  color: var(--text-muted);
  font-style: italic;
}

/* 下载中进度 */
.downloading-box {
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.download-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.download-status-text {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.status-size {
  font-size: 12px;
  color: var(--text-muted);
}

.percent-tag {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary-color, #6366f1);
}

.progress-bar-wrap {
  width: 100%;
}

.download-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.gradient-btn {
  background: var(--primary-gradient, linear-gradient(135deg, #6366f1 0%, #a855f7 100%)) !important;
  border: none !important;
  color: #fff !important;
}

.gradient-btn-success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  color: #fff !important;
}
</style>
