<template>
  <!-- ① 主弹窗：授权与开通（一屏到底） -->
  <el-dialog
    v-model="authStore.authModalVisible"
    title="软件授权"
    width="600px"
    destroy-on-close
    align-center
    class="auth-dialog"
  >
    <div class="auth-modal-content">
      <!-- 1. 状态：3px 竖条 + 右侧常驻试用余额 -->
      <div class="auth-status" :class="authStore.overview.is_activated ? 'is-active' : 'is-inactive'">
        <div class="status-text">
          <div class="status-title">
            {{
              authStore.overview.is_activated
                ? '已授权 · 正式版'
                : (authStore.trialRemaining > 0 ? '未激活' : '试用次数已用尽')
            }}
          </div>
          <div class="status-desc">
            <template v-if="authStore.overview.is_activated">
              有效期至 {{ authStore.overview.deadline || '永久有效' }}
            </template>
            <template v-else-if="authStore.trialRemaining > 0">
              当前为试用模式，开通后可长期使用
            </template>
            <template v-else>
              开通后可继续发布任务
            </template>
          </div>
        </div>

        <span
          v-if="authStore.overview.is_activated && authStore.overview.days_remaining > 0"
          class="status-side"
          :class="{ warn: authStore.overview.days_remaining <= 30 }"
        >
          剩余 {{ authStore.overview.days_remaining }} 天
        </span>
        <span
          v-else-if="!authStore.overview.is_activated && authStore.trialRemaining > 0"
          class="trial-chip"
        >
          可试用 {{ authStore.trialRemaining }} 次
        </span>
      </div>

      <!-- 2. 已激活：续期 / 换设备 -->
      <div v-if="authStore.overview.is_activated" class="renew-row">
        <span class="renew-label">本机已绑定授权</span>
        <el-button size="small" plain @click="showRenew = !showRenew">
          {{ showRenew ? '收起' : '续期 / 换设备' }}
        </el-button>
      </div>

      <!-- 3. 未激活：微信扫码开通（主路径） -->
      <template v-if="!authStore.overview.is_activated">
        <div class="sec-title">微信扫码开通</div>

        <div class="package-grid">
          <div
            v-for="p in packages"
            :key="p.package_type"
            class="package-card"
            :class="{ on: selectedPackage === p.package_type }"
            @click="selectedPackage = p.package_type"
          >
            <div class="pkg-label">{{ p.label }}</div>
            <div class="pkg-price"><span class="pkg-unit">¥</span>{{ p.price_yuan }}</div>
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
          <span>{{ selectedPrice > 0 ? `微信扫码开通 · ¥${selectedPrice}` : '立即开通' }}</span>
        </el-button>
      </template>

      <!-- 4. 激活码 + 设备识别码（未激活时展示；已激活时点开续期才展示） -->
      <template v-if="!authStore.overview.is_activated || showRenew">
        <div class="sec-title">
          {{ authStore.overview.is_activated ? '输入续期卡密' : '已有激活码 / 兑换卡' }}
        </div>
        <div class="code-input-row">
          <el-input
            v-model="activationCode"
            placeholder="粘贴授权激活码"
            size="large"
            clearable
            @input="activateError = ''"
            @keyup.enter="handleActivate"
          />
          <el-button
            plain
            size="large"
            class="activate-btn"
            :loading="authStore.loading"
            @click="handleActivate"
          >
            <span>{{ authStore.overview.is_activated ? '续期' : '兑换' }}</span>
          </el-button>
        </div>
        <div v-if="activateError" class="err-line">{{ activateError }}</div>

        <div class="sn-row">
          <span class="sn-label">设备识别码</span>
          <code class="sn-code">{{ authStore.overview.new_sn || '正在生成…' }}</code>
          <el-button
            size="small"
            plain
            :disabled="!authStore.overview.new_sn"
            @click="copySN"
          >
            {{ copied ? '已复制' : '复制' }}
          </el-button>
        </div>
        <div class="sn-note">需要人工开通时，把识别码发给管理员即可</div>
      </template>

      <!-- 5. 公告 -->
      <div v-if="authStore.overview.announcement" class="announcement-box">
        <el-alert
          :title="authStore.overview.announcement"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <a class="foot-link" @click="showHelp">开通遇到问题？</a>
        <div class="foot-actions">
          <el-button @click="authStore.refreshAuth" :loading="authStore.loading" plain size="default">
            刷新状态
          </el-button>
          <el-button text size="default" @click="authStore.closeAuthModal">
            关闭
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>

  <!-- ② 支付二维码 -->
  <el-dialog
    v-model="payVisible"
    title="微信扫码支付"
    width="380px"
    append-to-body
    align-center
    :close-on-click-modal="false"
    @closed="stopPolling"
  >
    <div class="pay-qr-wrap">
      <QrcodeVue v-if="codeUrl" :value="codeUrl" :size="190" level="M" />
      <div class="pay-amount"><span class="pay-unit">¥</span>{{ payAmount }}</div>
      <div class="pay-plan">{{ payPlanLabel }}</div>
      <div class="pay-status" :class="{ ok: paySuccess }">
        <span v-if="!paySuccess" class="pulse-dot"></span>{{ payStatusText }}
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <span class="order-no">订单号 {{ outTradeNo || '—' }}</span>
        <div class="foot-actions">
          <el-button plain size="small" @click="showHelp">遇到问题</el-button>
          <el-button text size="small" @click="payVisible = false">取消订单</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import QrcodeVue from 'qrcode.vue'
import { GetOrderPackages, CreateOrder, QueryOrder } from '../../wailsjs/go/main/App'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()
const activationCode = ref('')
const showRenew = ref(false)
const activateError = ref('')
const copied = ref(false)

// ---- 在线开通 ----
const packages = ref<any[]>([])
const selectedPackage = ref('')
const ordering = ref(false)

/** 当前选中档位的价格（用于主按钮文案，0 表示未选中） */
const selectedPrice = computed(() => {
  const hit = packages.value.find((x: any) => x.package_type === selectedPackage.value)
  return hit?.price_yuan ?? 0
})

/** 支付弹窗里的套餐名 */
const payPlanLabel = computed(() => {
  const hit = packages.value.find((x: any) => x.package_type === selectedPackage.value)
  return hit ? `${hit.label}` : ''
})

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
    payStatusText.value = '等待支付 · 剩余 03:00'
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

    payStatusText.value = `等待支付 · 剩余 ${String(Math.floor(Math.max(0, 180 - elapsed / 1000) / 60)).padStart(2, '0')}:${String(Math.floor(Math.max(0, 180 - elapsed / 1000)) % 60).padStart(2, '0')}`

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
    ElMessage.success('设备识别码已复制')
    copied.value = true
    setTimeout(() => { copied.value = false }, 1600)
  } catch (err) {
    ElMessage.warning('复制失败，请手动划选复制：' + sn)
  }
}

const handleActivate = async () => {
  const code = activationCode.value.trim()
  if (!code) {
    activateError.value = '请输入有效的激活码'
    return
  }
  activateError.value = ''
  const res = await authStore.activate(code)
  if (res.success) {
    ElMessage.success(res.msg)
    activationCode.value = ''
    showRenew.value = false
  } else {
    activateError.value = res.msg
  }
}

/** 底部帮助入口：不引入新的网络依赖，直接把识别码与说明复制给用户 */
function showHelp() {
  const sn = authStore.overview.new_sn || '（识别码尚未生成）'
  ElMessage.info(`如需人工开通，请把设备识别码 ${sn} 发送给管理员`)
}
</script>

<style scoped>
.auth-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 2px 0;
}

/* ---- 状态：3px 竖条，无底色无边框 ---- */
.auth-status {
  display: flex;
  align-items: center;
  gap: 13px;
  padding-left: 13px;
  position: relative;
}

.auth-status::before {
  content: '';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 3px;
  border-radius: 2px;
  background: var(--status-warning);
}

.auth-status.is-active::before {
  background: var(--status-success);
}

.status-text {
  flex: 1;
  min-width: 0;
}

.status-title {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-main);
}

.status-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.status-side {
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.status-side.warn {
  color: var(--status-warning);
}

.trial-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--primary-color);
  background: rgba(79, 70, 229, 0.10);
  white-space: nowrap;
}

/* ---- 已激活折叠行 ---- */
.renew-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
}

.renew-label {
  font-size: 12.5px;
  color: var(--text-secondary);
}

/* ---- 区块标题（右侧带一条淡分隔线）---- */
.sec-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.sec-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}

/* ---- 套餐卡：选中态用主色 ---- */
.package-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.package-card {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg-detail);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.package-card:hover {
  border-color: var(--border-highlight);
}

.package-card.on {
  border-color: var(--primary-color);
  background: rgba(79, 70, 229, 0.06);
}

.pkg-label {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.pkg-price {
  font-size: 22px;
  font-weight: 700;
  margin-top: 6px;
  letter-spacing: -0.5px;
  color: var(--text-main);
}

.pkg-unit {
  font-size: 13px;
  font-weight: 600;
  margin-right: 2px;
}

.order-btn {
  width: 100%;
  height: 42px;
  font-size: 14px;
  font-weight: 600;
}

/* ---- 激活码行 ---- */
.code-input-row {
  display: flex;
  gap: 10px;
}

.activate-btn {
  padding: 0 20px;
  font-weight: 600;
}

.err-line {
  font-size: 12px;
  line-height: 1.5;
  color: var(--status-danger);
}

/* ---- 设备识别码：压缩成一行弱信息 ---- */
.sn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
}

.sn-label {
  font-size: 11.5px;
  color: var(--text-muted);
  white-space: nowrap;
}

.sn-code {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--text-main);
}

.sn-note {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: -8px;
}

.announcement-box {
  margin-top: 2px;
}

/* ---- 底部 ---- */
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.foot-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.foot-link {
  font-size: 12.5px;
  color: var(--primary-color);
  cursor: pointer;
}

/* ---- 支付二维码 ---- */
.pay-qr-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.pay-amount {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: var(--text-main);
}

.pay-unit {
  font-size: 14px;
  font-weight: 600;
  margin-right: 3px;
}

.pay-plan {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: -6px;
}

.pay-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.pay-status.ok {
  color: var(--status-success);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-warning);
  animation: pulse-fade 1.4s ease-in-out infinite;
}

@keyframes pulse-fade {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

.order-no {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
</style>
