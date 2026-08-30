<template>
  <el-dialog
    v-model="authStore.authModalVisible"
    title="软件授权与激活管理"
    width="540px"
    destroy-on-close
    align-center
    class="auth-dialog glass-dialog"
  >
    <div class="auth-modal-content">
      <!-- 1. 顶部状态横幅 -->
      <div class="auth-status-banner" :class="authStore.overview.is_activated ? 'status-active' : 'status-inactive'">
        <div class="status-icon-wrap">
          <el-icon v-if="authStore.overview.is_activated" :size="28"><Medal /></el-icon>
          <el-icon v-else :size="28"><Lock /></el-icon>
        </div>
        <div class="status-info">
          <div class="status-title">
            {{ authStore.overview.is_activated ? '正式授权版 (PRO EDITION)' : '未激活 / 试用模式' }}
          </div>
          <div class="status-desc">
            <template v-if="authStore.overview.is_activated">
              <span>到期时间：{{ authStore.overview.deadline || '永久有效' }}</span>
              <span v-if="authStore.overview.days_remaining > 0" class="days-badge">
                (剩余 {{ authStore.overview.days_remaining }} 天)
              </span>
            </template>
            <template v-else>
              <span>未开通全功能授权，发布矩阵任务受限，请激活解锁</span>
            </template>
          </div>
        </div>
      </div>

      <!-- 2. 本机设备识别码卡片 (NewSN) -->
      <div class="device-sn-card">
        <div class="card-label-row">
          <span class="card-label">本机设备识别码 (用于开通与绑定)：</span>
          <el-tag size="small" type="info" effect="plain">NewSN 标准码</el-tag>
        </div>
        <div class="sn-display-box">
          <code class="sn-code">{{ authStore.overview.new_sn || '正在生成识别码...' }}</code>
          <el-button 
            type="primary" 
            size="small" 
            class="copy-btn"
            @click="copySN"
            :disabled="!authStore.overview.new_sn"
          >
            <el-icon><CopyDocument /></el-icon>
            <span>复制识别码</span>
          </el-button>
        </div>
        <div class="sn-tip">
          💡 请将上方 16 位识别码发送给管理员或代理商，开通对应的矩阵发布授权。
        </div>
      </div>

      <!-- 3. 激活码输入与兑换 -->
      <div class="activation-action-section">
        <div class="section-title">输入授权卡密 / 激活码：</div>
        <div class="code-input-row">
          <el-input
            v-model="activationCode"
            placeholder="粘贴您的授权激活码..."
            size="large"
            clearable
            :prefix-icon="Key"
            @keyup.enter="handleActivate"
          />
          <el-button 
            type="success" 
            size="large" 
            class="activate-btn"
            :loading="authStore.loading"
            @click="handleActivate"
          >
            <span>立即激活</span>
          </el-button>
        </div>
      </div>

      <!-- 4. 公告与客服支持 -->
      <div v-if="authStore.overview.announcement" class="announcement-box">
        <el-alert
          :title="'系统公告：' + authStore.overview.announcement"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="authStore.refreshAuth" :loading="authStore.loading" plain size="default">
          <el-icon><Refresh /></el-icon>
          <span>刷新授权状态</span>
        </el-button>
        <el-button type="primary" plain @click="authStore.closeAuthModal" size="default">
          <span>完成 / 关闭</span>
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Medal, Lock, CopyDocument, Key, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const activationCode = ref('')

const copySN = async () => {
  const sn = authStore.overview.new_sn
  if (!sn) return

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(sn)
    } else {
      const ta = document.createElement('textarea')
      ta.value = sn
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('🎉 设备识别码已复制到剪贴板！')
  } catch (err) {
    ElMessage.warning('复制失败，请手动划选复制：' + sn)
  }
}

const handleActivate = async () => {
  const code = activationCode.value.trim()
  if (!code) {
    ElMessage.warning('请输入有效的激活码')
    return
  }

  const res = await authStore.activate(code)
  if (res.success) {
    ElMessage.success(res.msg)
    activationCode.value = ''
  } else {
    ElMessage.error(res.msg)
  }
}
</script>

<style scoped>
.auth-modal-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 0;
}

.auth-status-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.status-active {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.05));
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.status-inactive {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(220, 38, 38, 0.04));
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #ef4444;
}

.status-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.status-desc {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  margin-top: 4px;
}

.days-badge {
  color: #10b981;
  font-weight: bold;
  margin-left: 6px;
}

.device-sn-card {
  background: var(--bg-detail, rgba(30, 41, 59, 0.5));
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main, #f8fafc);
}

.sn-display-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border-highlight, rgba(99, 102, 241, 0.4));
  border-radius: 8px;
  padding: 8px 12px;
}

.sn-code {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #38bdf8;
}

.copy-btn {
  font-weight: 600;
}

.sn-tip {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  line-height: 1.4;
}

.activation-action-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main, #f8fafc);
}

.code-input-row {
  display: flex;
  gap: 10px;
}

.activate-btn {
  padding: 0 24px;
  font-weight: 700;
}

.announcement-box {
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>
