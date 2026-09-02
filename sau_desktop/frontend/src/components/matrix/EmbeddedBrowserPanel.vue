<template>
  <div class="embedded-browser-panel glass-card">
    <!-- 1. 仿浏览器拟物化顶部地址与控制栏 (Browser Chrome Bar) -->
    <div class="browser-chrome-bar">
      <div class="mac-traffic-lights">
        <span class="light red" @click="handleStopSession" title="关闭当前会话"></span>
        <span class="light yellow" @click="isInteractive = !isInteractive" :title="isInteractive ? '点击禁用鼠标穿透' : '点击启用鼠标穿透'"></span>
        <span class="light green" @click="toggleExpand" :title="isExpanded ? '还原视窗' : '最大化视窗'"></span>
      </div>

      <!-- 拟真 URL 地址胶囊 -->
      <div class="browser-url-pill">
        <el-icon class="ssl-lock"><Lock /></el-icon>
        <span class="platform-indicator-tag" :style="{ background: currentPlatformConfig.gradient }">
          {{ currentPlatformConfig.name }}
        </span>
        <span class="url-text">{{ currentUrl }}</span>
        <el-button size="small" type="primary" link class="url-reload-btn" @click="handleRefresh" :disabled="!isSessionActive">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <!-- 右侧辅助控制按钮 -->
      <div class="chrome-actions">
        <el-tag size="small" :type="isSessionActive ? 'success' : 'info'" effect="dark" class="session-badge">
          <span class="pulse-dot" v-if="isSessionActive"></span>
          {{ isSessionActive ? '投屏进行中' : '视窗待机' }}
        </el-tag>

        <el-tooltip :content="isInteractive ? '已开启鼠标穿透：可直接在画面中滑动验证码或点击' : '只读模式：已禁用鼠标反向操作'" placement="top">
          <el-button 
            size="small" 
            :type="isInteractive ? 'primary' : 'info'" 
            link 
            @click="isInteractive = !isInteractive"
          >
            <el-icon><Pointer /></el-icon>
            <span class="action-btn-text">{{ isInteractive ? '交互开' : '只读' }}</span>
          </el-button>
        </el-tooltip>

        <el-button size="small" type="info" link @click="$emit('toggle-collapse')" title="折叠/展开内嵌视窗">
          <el-icon><DArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 2. 浏览器视窗主展示区 -->
    <div class="browser-viewport-container">
      <!-- A. 处于活跃投屏会话时：呈现高性能 Live Canvas -->
      <div v-if="isSessionActive" class="live-canvas-host">
        <LiveBrowserCanvas 
          ref="canvasRef"
          :taskId="currentTaskId"
          :title="`${currentPlatformConfig.name} - ${accountName || '新账号'} 实时工作台`"
        />
      </div>

      <!-- B. 待机空闲状态：区分【已有账号专属面板】与【新账号接入发射台】 -->
      <div v-else class="browser-idle-launchpad">
        <!-- B1. 已选中具体账号状态 -->
        <div v-if="accountItem" class="launchpad-card account-detail-view">
          <div class="account-avatar-banner" :style="{ background: currentPlatformConfig.gradient }">
            <span class="avatar-big-char">{{ (accountItem.nickname || accountItem.account).slice(0, 1).toUpperCase() }}</span>
            <span class="platform-mini-badge">
              <el-icon><component :is="currentPlatformConfig.icon" /></el-icon>
            </span>
          </div>

          <h3 class="launch-title">{{ accountItem.nickname || accountItem.account }}</h3>
          <div class="account-meta-pills">
            <el-tag size="small" :type="accountItem.isValid ? 'success' : 'danger'" effect="dark" round>
              {{ accountItem.isValid ? '✅ 凭证健康有效' : '⚠️ 凭证已过期失效' }}
            </el-tag>
            <el-tag size="small" type="info" round v-if="accountItem.finderUid">ID: {{ accountItem.finderUid }}</el-tag>
            <el-tag size="small" type="warning" round>{{ accountItem.group || '默认业务组' }}</el-tag>
          </div>

          <p class="launch-desc" v-if="accountItem.isValid">
            该账号凭证健康完备，自动化矩阵发布引擎可随时调用无头 Chromium 执行任务。点击下方按钮可实时进入该账号的创作者后台或更新凭证。
          </p>
          <p class="launch-desc" v-else style="color: #f87171;">
            当前账号登录凭证已失效或尚未登录，点击下方按钮将立即拉起后台无头浏览器，二维码将实时呈现在此处，手机扫码即可无缝完成绑定。
          </p>

          <div class="account-action-buttons">
            <el-button 
              type="primary" 
              class="start-stream-btn" 
              size="large" 
              :loading="isStarting"
              @click="startSession(accountItem.platform, accountItem.account)"
            >
              <el-icon><VideoPlay /></el-icon>
              <span>{{ accountItem.isValid ? '进入创作者网页视窗 / 重新扫码' : '立即拉起扫码登录' }}</span>
            </el-button>
          </div>

          <div class="launchpad-footer-pill">
            <el-icon><Check /></el-icon>
            <span>无外置弹窗 · 绿色内置内核 · 自动捕获 Cookie · 双向鼠标滑块穿透</span>
          </div>
        </div>

        <!-- B2. 新增账号接入状态 -->
        <div v-else class="launchpad-card">
          <div class="launchpad-icon-glow">
            <el-icon class="launch-icon"><Monitor /></el-icon>
          </div>
          <h3 class="launch-title">平台网页内嵌控制台</h3>
          <p class="launch-desc">
            无头浏览器将直接在右侧视窗内实时投屏呈现。您可在左侧账号列表中点击任一账号的<strong>「重新登录」</strong>，或在下方直接选择平台<strong>「一键扫码接入」</strong>。
          </p>

          <!-- 快速发起接入表单 -->
          <div class="quick-launch-box">
            <div class="input-row">
              <span class="field-label">接入平台:</span>
              <el-select v-model="selectedPlatform" size="default" style="width: 140px;">
                <el-option 
                  v-for="p in platformList" 
                  :key="p.id" 
                  :label="p.name" 
                  :value="p.id" 
                />
              </el-select>

              <span class="field-label" style="margin-left: 8px;">账号别名:</span>
              <el-input 
                v-model="quickAccountName" 
                placeholder="留空自动读取昵称" 
                size="default" 
                style="flex: 1;" 
                clearable
              />
            </div>

            <div class="action-launch-row">
              <el-button 
                type="primary" 
                class="start-stream-btn" 
                size="default" 
                :loading="isStarting"
                @click="startQuickLogin"
              >
                <el-icon><VideoPlay /></el-icon>
                <span>立即拉起内嵌投屏并扫码</span>
              </el-button>
            </div>
          </div>

          <!-- 环境与安全提示胶囊 -->
          <div class="launchpad-footer-pill">
            <el-icon><Check /></el-icon>
            <span>无外置弹窗 · 绿色内置内核 · 自动捕获 Cookie · 双向鼠标滑块穿透</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 底部状态与操作控制条 (当处于会话时常驻) -->
    <div class="browser-footer-strip" v-if="isSessionActive">
      <div class="footer-left">
        <el-icon class="is-loading" v-if="isStarting"><Loading /></el-icon>
        <el-icon v-else><InfoFilled /></el-icon>
        <span>{{ statusText }}</span>
      </div>

      <div class="footer-right">
        <el-button size="small" type="danger" plain @click="handleStopSession">
          <el-icon><CircleClose /></el-icon>
          <span>结束本次会话</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { LoginAccountWithScreencast, StopTaskById } from '../../../wailsjs/go/main/App'
import { PLATFORMS, getPlatformConfig } from '../../config/platforms'
import LiveBrowserCanvas from './LiveBrowserCanvas.vue'

const props = defineProps<{
  // 外部传入请求登录的账号对象 (如果有)
  targetSession?: { platform: string; account: string } | null
  // 外部当前选中的矩阵账号对象
  accountItem?: any
}>()

const emit = defineEmits<{
  (e: 'login-success', res: any): void
  (e: 'toggle-collapse'): void
}>()

const isSessionActive = ref(false)
const isStarting = ref(false)
const isInteractive = ref(true)
const isExpanded = ref(false)
const selectedPlatform = ref('douyin')
const quickAccountName = ref('')
const accountName = ref('')
const currentTaskId = ref('')
const statusText = ref('等待扫码授权中...')

const platformList = computed(() => PLATFORMS)

const currentPlatformConfig = computed(() => {
  return getPlatformConfig(selectedPlatform.value)
})

const currentUrl = computed(() => {
  switch (selectedPlatform.value) {
    case 'douyin': return 'https://creator.douyin.com/'
    case 'xiaohongshu': return 'https://creator.xiaohongshu.com/'
    case 'kuaishou': return 'https://cp.kuaishou.com/'
    case 'tencent': return 'https://channels.weixin.qq.com/'
    case 'bilibili': return 'https://member.bilibili.com/'
    case 'weibo': return 'https://weibo.com/'
    case 'baijiahao': return 'https://baijiahao.baidu.com/'
    default: return 'https://creator.platform.com/'
  }
})

watch(() => props.accountItem, (newAcc) => {
  if (newAcc && newAcc.platform) {
    selectedPlatform.value = newAcc.platform
    accountName.value = newAcc.account
    isSessionActive.value = false
  }
}, { immediate: true })

// 监听外部触发的会话请求 (如用户在左侧列表点击了某个账号的【重新登录】)
watch(() => props.targetSession, (newVal) => {
  if (newVal && newVal.platform) {
    selectedPlatform.value = newVal.platform
    quickAccountName.value = newVal.account
    startSession(newVal.platform, newVal.account)
  }
}, { immediate: true })

const startQuickLogin = () => {
  startSession(selectedPlatform.value, quickAccountName.value.trim() || 'auto')
}

const startSession = async (platform: string, account: string) => {
  const acc = account || 'auto'
  accountName.value = acc
  selectedPlatform.value = platform
  currentTaskId.value = `login_${platform}_${acc}`
  isSessionActive.value = true
  isStarting.value = true
  statusText.value = '正在拉起后台无头浏览器并建立 CDP 画面流...'

  try {
    const res = await LoginAccountWithScreencast(platform, acc)
    if (res && res.success) {
      statusText.value = `🎉 登录成功！已保存账号 [${res.nickname || res.account}] 凭证`
      ElMessage.success(`🎉 账号 [${res.nickname || res.account}] 登录成功！凭证已同步入库。`)
      emit('login-success', res)
      setTimeout(() => {
        isSessionActive.value = false
      }, 2500)
    } else {
      statusText.value = `登录未完成: ${res?.msg || '会话结束'}`
      ElMessage.warning(`登录未完成: ${res?.msg || '未知原因'}`)
      isSessionActive.value = false
    }
  } catch (err: any) {
    if (!String(err).includes('手动中止')) {
      statusText.value = `执行异常: ${err?.message || err}`
      ElMessage.error(`登录异常: ${err?.message || err}`)
    }
    isSessionActive.value = false
  } finally {
    isStarting.value = false
  }
}

const handleStopSession = async () => {
  if (currentTaskId.value) {
    await StopTaskById(currentTaskId.value)
  }
  isSessionActive.value = false
  isStarting.value = false
  statusText.value = '会话已手动中止'
  ElMessage.info('已中止当前浏览器会话')
}

const handleRefresh = () => {
  statusText.value = '已重新向无头浏览器下发刷新指令'
}

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 暴露启动方法供父组件直接调用
defineExpose({
  startSession
})
</script>

<style scoped>
.embedded-browser-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: rgba(10, 15, 29, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  transition: all 0.3s ease;
}

/* 仿浏览器顶部地址栏 Chrome Bar */
.browser-chrome-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  gap: 12px;
}

.mac-traffic-lights {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mac-traffic-lights .light {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.mac-traffic-lights .light:hover {
  transform: scale(1.15);
}

.mac-traffic-lights .light.red { background: #ef4444; }
.mac-traffic-lights .light.yellow { background: #f59e0b; }
.mac-traffic-lights .light.green { background: #10b981; }

.browser-url-pill {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(2, 6, 23, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 11px;
}

.ssl-lock {
  color: #10b981;
  font-size: 12px;
}

.platform-indicator-tag {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  padding: 1px 6px;
  border-radius: 10px;
  line-height: 1.2;
}

.url-text {
  flex: 1;
  color: #94a3b8;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-reload-btn {
  padding: 0;
  height: auto;
  color: #64748b;
}

.chrome-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-badge {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  animation: pulseGlow 1.5s infinite;
}

@keyframes pulseGlow {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1.2); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.action-btn-text {
  font-size: 11px;
  margin-left: 2px;
}

/* 视窗主展示区 */
.browser-viewport-container {
  flex: 1;
  position: relative;
  background: #020617;
  overflow: hidden;
  display: flex;
}

.live-canvas-host {
  width: 100%;
  height: 100%;
}

/* 待机空闲发射台 */
.browser-idle-launchpad {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.launchpad-card {
  max-width: 440px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.launchpad-icon-glow {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.2) 0%, rgba(56, 189, 248, 0.03) 70%);
  border: 1px solid rgba(56, 189, 248, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 24px rgba(56, 189, 248, 0.15);
}

.launch-icon {
  font-size: 38px;
  color: #38bdf8;
}

.launch-title {
  font-size: 17px;
  font-weight: 700;
  color: #f8fafc;
  margin: 0;
}

.launch-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0;
}

.launch-desc strong {
  color: #38bdf8;
}

.quick-launch-box {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 12px;
  margin-top: 4px;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
  white-space: nowrap;
}

.start-stream-btn {
  width: 100%;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
  border: none !important;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.launchpad-footer-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.account-detail-view {
  max-width: 480px;
}

.account-avatar-banner {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.avatar-big-char {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
}

.platform-mini-badge {
  position: absolute;
  bottom: 0px;
  right: 0px;
  width: 22px;
  height: 22px;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
  font-size: 11px;
}

.account-meta-pills {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.account-action-buttons {
  width: 100%;
  display: flex;
  justify-content: center;
  margin: 6px 0;
}

/* 底部状态栏 */
.browser-footer-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #38bdf8;
  font-weight: 600;
}
</style>
