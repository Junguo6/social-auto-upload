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

      <!-- 3. 在线开通（未激活时显示；价格与可购性来自服务端配置） -->
      <div v-if="!authStore.overview.is_activated" class="online-order-section">
        <div class="section-title">在线开通：</div>

        <div class="package-grid">
          <div
            v-for="p in packages"
            :key="p.package_type"
            class="package-card"
            :class="{ on: selectedPackage === p.package_type }"
            @click="selectedPackage = p.package_type"
          >
            <div class="pkg-label">{{ p.label }}</div>
            <div class="pkg-price">
              <span class="pkg-unit">¥</span>{{ p.price_yuan }}
            </div>
          </div>
        </div>

        <el-button
          type="primary"
          size="large"
          class="order-btn"
          :disabled="!selectedPackage || ordering"
          :loading="ordering"
          @click="handleCreateOrder"
        >
          <span>立即开通</span>
        </el-button>

        <div class="order-tip">微信扫码支付，支付成功后自动开通，无需等待管理员</div>
      </div>

      <!-- 4. 激活码输入与兑换 -->
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

      <!-- 5. 公告与客服支持 -->
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

  <!-- 支付二维码弹窗 -->
  <el-dialog
    v-model="payVisible"
    title="微信扫码支付"
    width="360px"
    append-to-body
    align-center
    :close-on-click-modal="false"
    @closed="stopPolling"
  >
    <div class="pay-qr-wrap">
      <QrcodeVue v-if="codeUrl" :value="codeUrl" :size="220" level="M" />
      <div class="pay-amount">应付：<b>¥{{ payAmount }}</b></div>
      <div class="pay-hint">请使用微信「扫一扫」完成支付</div>
      <div class="pay-status" :class="{ ok: paySuccess }">{{ payStatusText }}</div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Medal, Lock, CopyDocument, Key, Refresh } from '@element-plus/icons-vue'
import QrcodeVue from 'qrcode.vue'
import { GetOrderPackages, CreateOrder, QueryOrder } from '../../wailsjs/go/main/App'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const activationCode = ref('')

// ---- 在线开通 ----
const packages = ref<any[]>([])
const selectedPackage = ref('')
const ordering = ref(false)

const payVisible = ref(false)
const codeUrl = ref('')
const outTradeNo = ref('')
const payAmount = ref(0)
const payStatusText = ref('等待扫码支付…')
const paySuccess = ref(false)
let pollTimer: number | null = null

/**
 * 加载套餐。
 * 只展示「可购买」的档位 —— 服务端把不卖的档价格置 0 → purchasable=false，
 * 因此季卡/永久档会被自动过滤，前端不写死白名单（以后加回档位只改服务端价格）。
 */
async function loadPackages() {
  try {
    // 先刷新授权信息拿最新价格（本组件常驻，不能只靠启动时那一次）
    await authStore.refreshAuth()

    const list = await GetOrderPackages()
    packages.value = (list || []).filter((p: any) => p.purchasable)

    // 上次选中的档若已不可购买，回退到第一个可购买的档
    if (!packages.value.some((p: any) => p.package_type === selectedPackage.value)) {
      selectedPackage.value = packages.value[0]?.package_type || ''
    }
  } catch (e) {
    console.warn('加载套餐失败:', e)
  }
}

async function handleCreateOrder() {
  if (!selectedPackage.value || ordering.value) return
  ordering.value = true
  try {
    const res = await CreateOrder(selectedPackage.value)
    if (!res?.success) {
      ElMessage.error(res?.message || '下单失败，请稍后重试')
      return
    }
    outTradeNo.value = res.out_trade_no
    codeUrl.value = res.code_url
    const p = packages.value.find((x: any) => x.package_type === selectedPackage.value)
    payAmount.value = p?.price_yuan ?? 0
    payStatusText.value = '等待扫码支付…'
    paySuccess.value = false
    payVisible.value = true
    startPolling()
  } catch (e: any) {
    ElMessage.error('下单失败：' + (e?.message || e))
  } finally {
    ordering.value = false
  }
}

/** 轮询支付状态：2.5s 一次，3 分钟超时（微信 Native 二维码有效期） */
function startPolling() {
  stopPolling()
  let elapsed = 0
  pollTimer = window.setInterval(async () => {
    elapsed += 2500

    if (elapsed > 3 * 60 * 1000) {
      stopPolling()
      payStatusText.value = '订单已过期，请关闭后重新下单'
      return
    }

    try {
      const res = await QueryOrder(outTradeNo.value)
      if (res?.trade_state === 'SUCCESS') {
        stopPolling()
        paySuccess.value = true
        payStatusText.value = '支付成功，正在开通…'
        ElMessage.success('支付成功，授权已开通')
        await authStore.refreshAuth()
        await loadPackages()
        setTimeout(() => { payVisible.value = false }, 1200)
      }
    } catch (e) {
      // 单次查询失败不中断轮询
    }
  }, 2500)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 每次打开授权弹窗都重新拉一次套餐。
// ⚠️ 本组件常驻在 App 上，onMounted 只在应用启动时跑一次，不能依赖它。
watch(
  () => authStore.authModalVisible,
  (visible) => {
    if (!visible) return
    if (!authStore.overview.is_activated) {
      loadPackages()
    } else {
      packages.value = [] // 已激活 → 清空，避免残留上次的套餐卡片
    }
  }
)

onUnmounted(stopPolling)

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
  background: rgba(16, 185, 129, 0.10);
  border: 1px solid rgba(16, 185, 129, 0.28);
  color: var(--status-success);
}

.status-inactive {
  background: rgba(239, 68, 68, 0.10);
  border: 1px solid rgba(239, 68, 68, 0.28);
  color: var(--status-danger);
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
  color: var(--text-muted);
  margin-top: 4px;
}

.days-badge {
  color: var(--status-success);
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
  color: var(--text-main);
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
  color: var(--status-info);
}

.copy-btn {
  font-weight: 600;
}

.sn-tip {
  font-size: 11px;
  color: var(--text-muted);
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
  color: var(--text-main);
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

/* ---- 在线开通 ---- */
.online-order-section {
  margin-bottom: 18px;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.package-card {
  border: 1.5px solid var(--border-subtle);
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-input);
}

.package-card.on {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
}

.pkg-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.pkg-price {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
}

.pkg-unit {
  font-size: 12px;
  margin-right: 1px;
}

.order-btn {
  width: 100%;
}

.order-tip {
  margin-top: 8px;
  font-size: 11.5px;
  color: var(--text-muted);
  text-align: center;
}

/* ---- 支付二维码 ---- */
.pay-qr-wrap {
  text-align: center;
}

.pay-amount {
  margin: 10px 0 4px;
  font-size: 14px;
  color: var(--text-main);
}

.pay-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.pay-status {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--text-muted);
}

.pay-status.ok {
  color: var(--status-success);
  font-weight: 600;
}
</style>
