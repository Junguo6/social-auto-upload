<template>
  <el-dialog
    v-model="visible"
    :title="`应用内安全扫码登录 — ${getPlatformName(currentPlatform)}`"
    width="860px"
    class="glass-dialog in-app-login-dialog"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="handleClosed"
  >
    <div class="login-modal-content">
      <!-- 顶部配置与说明 -->
      <div class="login-control-strip">
        <div class="strip-left">
          <span class="strip-label">目标平台:</span>
          <el-select v-model="currentPlatform" size="default" style="width: 140px;" :disabled="isLoggingIn">
            <el-option 
              v-for="plat in platformOptions" 
              :key="plat.id" 
              :label="plat.name" 
              :value="plat.id" 
            />
          </el-select>

          <span class="strip-label" style="margin-left: 12px;">账号标识:</span>
          <el-input 
            v-model="accountName" 
            placeholder="自定义账号别名 (留空自动生成)" 
            size="default" 
            style="width: 200px;"
            :disabled="isLoggingIn"
          />
        </div>

        <div class="strip-right">
          <el-button 
            v-if="!isLoggingIn" 
            type="primary" 
            class="gradient-btn-start"
            @click="startLogin"
          >
            <el-icon><VideoPlay /></el-icon>
            <span>开启扫码登录</span>
          </el-button>
          <el-button 
            v-else 
            type="danger" 
            plain 
            @click="cancelLogin"
          >
            <el-icon><CircleClose /></el-icon>
            <span>中止登录</span>
          </el-button>
        </div>
      </div>

      <!-- 实时画布主呈现区 -->
      <div class="login-canvas-area">
        <LiveBrowserCanvas 
          v-if="isLoggingIn"
          :taskId="currentTaskId"
          :title="`${getPlatformName(currentPlatform)} 网页登录实时画面`"
        />
        <div class="login-idle-splash" v-else>
          <div class="splash-center">
            <div class="splash-icon-box">
              <el-icon class="huge-icon"><Iphone /></el-icon>
            </div>
            <h3>点击上方「开启扫码登录」</h3>
            <p>系统将自动在后台拉起无头浏览器并以 CDP 实时画面投屏至此处，手机打开对应 App 扫码即可瞬间完成授权，全程无需弹出外置浏览器窗口。</p>
          </div>
        </div>
      </div>

      <!-- 底部辅助状态栏 -->
      <div class="login-status-footer" v-if="isLoggingIn">
        <div class="status-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ statusMsg }}</span>
        </div>
        <div class="tips-badge">
          <span>提示：若遇拼图或安全滑块，可直接在画面内拖动鼠标过验</span>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { LoginAccountWithScreencast, StopTaskById } from '../../../wailsjs/go/main/App'
import { useAccountStore } from '../../stores/accountStore'
import LiveBrowserCanvas from './LiveBrowserCanvas.vue'

const props = defineProps<{
  modelValue: boolean
  defaultPlatform?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'success', account: any): void
}>()

const accountStore = useAccountStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentPlatform = ref(props.defaultPlatform || 'douyin')
const accountName = ref('')
const isLoggingIn = ref(false)
const statusMsg = ref('正在拉起登录页并生成二维码...')
const currentTaskId = ref('')

watch(() => props.defaultPlatform, (val) => {
  if (val) currentPlatform.value = val
})

const platformOptions = [
  { id: 'douyin', name: '抖音' },
  { id: 'xiaohongshu', name: '小红书' },
  { id: 'kuaishou', name: '快手' },
  { id: 'tencent', name: '微信视频号' },
  { id: 'bilibili', name: '哔哩哔哩' },
  { id: 'weibo', name: '微博' },
  { id: 'baijiahao', name: '百家号' }
]

const getPlatformName = (pid: string) => {
  return platformOptions.find(p => p.id === pid)?.name || pid
}

const startLogin = async () => {
  const acc = accountName.value.trim() || 'auto'
  currentTaskId.value = `login_${currentPlatform.value}_${acc}`
  isLoggingIn.value = true
  statusMsg.value = '正在拉起登录会话并建立 CDP 画面通道...'

  try {
    const res = await LoginAccountWithScreencast(currentPlatform.value, acc)
    if (res && res.success) {
      ElMessage.success(`🎉 账号 [${res.nickname || res.account}] 扫码登录成功！`)
      emit('success', res)
      visible.value = false
      accountStore.fetchAccounts()
    } else {
      ElMessage.error(`登录未完成: ${res?.msg || '未知错误'}`)
    }
  } catch (err: any) {
    if (!String(err).includes('手动中止')) {
      ElMessage.error(`登录异常: ${err?.message || err}`)
    }
  } finally {
    isLoggingIn.value = false
  }
}

const cancelLogin = async () => {
  if (currentTaskId.value) {
    await StopTaskById(currentTaskId.value)
  }
  isLoggingIn.value = false
  statusMsg.value = '登录已中止'
}

const handleClosed = () => {
  if (isLoggingIn.value) {
    cancelLogin()
  }
}
</script>

<style scoped>
.login-modal-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login-control-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.strip-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strip-label {
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
}

.gradient-btn-start {
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
  border: none !important;
  font-weight: 700;
}

.login-canvas-area {
  height: 480px;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: #020617;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-idle-splash {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 40px;
  text-align: center;
}

.splash-center {
  max-width: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.splash-icon-box {
  width: 68px;
  height: 68px;
  border-radius: 20px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.huge-icon {
  font-size: 36px;
  color: #38bdf8;
}

.splash-center h3 {
  margin: 0;
  font-size: 16px;
  color: #f8fafc;
}

.splash-center p {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
}

.login-status-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.8);
  border-radius: 6px;
  font-size: 11px;
}

.status-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #38bdf8;
  font-weight: 600;
}

.tips-badge {
  color: #94a3b8;
}
</style>
