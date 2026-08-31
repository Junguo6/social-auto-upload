<template>
  <div class="matrix-studio-workspace">
    <!-- 1. 顶部工作台状态与操作栏 -->
    <StudioTopBar 
      :saved-templates="savedTemplates"
      @template-command="handleTemplateCommand"
      @fill-demo="fillDemoContent"
      @reset-all="resetAllForm"
    />

    <!-- 2. 主体左右双驱全景工作区 -->
    <div class="studio-body">
      <!-- ◀ 左侧：全局基础通用主模板 -->
      <MasterPanel 
        :master-form="masterForm"
        @sync-all="syncAllPlatformsToMaster"
      />

      <!-- ▶ 右侧：矩阵账号与平台差异化调优 -->
      <div class="matrix-panel glass-card">
        <!-- 头部精简导航栏：账号选择触发器 -->
        <div class="matrix-top-header">
          <div class="header-summary-box">
            <span class="badge-dot matrix-dot"></span>
            <span class="summary-title">2. 矩阵平台与账号差异化调优</span>
            <div class="target-account-badge" @click="showAccountModal = true">
              <el-icon><UserFilled /></el-icon>
              <span>已选 <strong>{{ selectedTargets.length }}</strong> 个有效矩阵账号 (覆盖 {{ activePlatformCount }} 个平台)</span>
              <el-icon class="arrow-icon"><ArrowRight /></el-icon>
            </div>
          </div>

          <div class="header-right-actions">
            <el-button class="manage-accounts-btn gradient-btn-sm" type="primary" size="small" @click="showAccountModal = true">
              <el-icon><Operation /></el-icon> 选择/调整矩阵账号
            </el-button>
          </div>
        </div>

        <!-- 现代极简平台图标 Dock 栏 (Icon Dock，智能跟随已选账号平台呈现) -->
        <PlatformIconDock 
          v-model="currentPlatformTab"
          :platform-overrides="platformOverrides"
          :selected-target-keys="selectedTargetKeys"
          @open-account-modal="showAccountModal = true"
        />

        <!-- 选中平台的专属差异化配置卡片 (包含二级账号分段控制器与插件表单) -->
        <PlatformCustomCard 
          v-if="selectedTargets.length > 0 && currentPlatformTab"
          :platform-id="currentPlatformTab"
          :platform-override="currentPlatformOverride"
          :account-overrides="accountOverrides"
          :master-form="masterForm"
          :account-list="currentPlatformAccounts"
          @open-sync-modal="openSyncConfigModal"
        />

        <!-- 无选中账号时的空状态提示 -->
        <div v-else class="matrix-empty-placeholder">
          <div class="empty-glow-box">
            <el-icon><UserFilled /></el-icon>
          </div>
          <div class="empty-title">当前尚未选择矩阵发布账号</div>
          <div class="empty-sub">请先勾选需要发布的平台账号，系统将自动展示对应平台的专属差异化调优卡片</div>
          <el-button type="primary" class="gradient-btn-matrix" @click="showAccountModal = true">
            <el-icon><Operation /></el-icon> 立即选择矩阵账号
          </el-button>
        </div>
      </div>
    </div>

    <!-- 3. 底部常驻调度执行控制栏 (Dock Bar) -->
    <StudioBottomDock 
      v-model:concurrency="concurrency"
      v-model:is-headless="isHeadless"
      :active-platform-count="activePlatformCount"
      :selected-count="selectedTargets.length"
      @start="handleStartPublish"
    />

    <!-- 4. 弹窗：选择矩阵目标账号 (健康检测 + 业务分组) -->
    <AccountSelectModal 
      v-model="showAccountModal"
      :selected-keys="selectedTargetKeys"
      @select-platform="currentPlatformTab = $event"
    />

    <!-- 5. 弹窗：跨账号/跨平台一键同步配置克隆器 -->
    <SyncConfigModal 
      v-model="showSyncModal"
      :source-description="syncSourceDesc"
      :current-platform="syncSourcePlatform"
      :current-account-key="syncSourceAccountKey"
      :selected-targets="selectedTargets"
      @confirm-sync="handleExecuteSyncConfig"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PLATFORMS } from '../config/platforms'
import { useAccountStore } from '../stores/accountStore'
import { useMatrixPresets } from '../composables/useMatrixPresets'
import { useMatrixPublish } from '../composables/useMatrixPublish'
import type { MasterForm, PlatformOverrideSetting, SyncConfigFields } from '../types/matrix'

// 模块化子组件引入
import StudioTopBar from '../components/matrix/StudioTopBar.vue'
import MasterPanel from '../components/matrix/MasterPanel.vue'
import PlatformIconDock from '../components/matrix/PlatformIconDock.vue'
import PlatformCustomCard from '../components/matrix/PlatformCustomCard.vue'
import AccountSelectModal from '../components/matrix/AccountSelectModal.vue'
import SyncConfigModal from '../components/matrix/SyncConfigModal.vue'
import StudioBottomDock from '../components/matrix/StudioBottomDock.vue'

// 1. 全局 Stores
const accountStore = useAccountStore()

// 2. 主模板表单 (Master Form)
const masterForm = reactive<MasterForm>({
  action: 'upload-video',
  filePath: '',
  images: [],
  title: '',
  desc: '',
  tags: '',
  thumbnail: '',
  schedule: ''
})

// 3. 多平台独立覆盖参数字典 (Platform Overrides)
const platformOverrides = reactive<Record<string, PlatformOverrideSetting>>({})
PLATFORMS.forEach(p => {
  platformOverrides[p.id] = {
    isCustomized: false,
    title: '',
    desc: '',
    tags: '',
    thumbnail: '',
    thumbnailLandscape: '',
    thumbnailPortrait: '',
    tid: p.id === 'bilibili' ? 230 : 0,
    shortTitle: '',
    category: '',
    draft: false,
    schedule: '',
    declaration: '',
    collection: '',
    productLink: '',
    productTitle: '',
    visibility: '0',
    playlist: '',
    bgm: '',
    note: '',
    notef: ''
  }
})

// 4. 账号级独立覆盖字典 (Account Overrides)
const accountOverrides = reactive<Record<string, PlatformOverrideSetting>>({})

// 5. 工作台视图状态机
const currentPlatformTab = ref<string>('tencent')
const concurrency = ref<number>(3)
const isHeadless = ref<boolean>(false)
const showAccountModal = ref<boolean>(false)
const selectedTargetKeys = ref<Set<string>>(new Set())

// 同步弹窗状态
const showSyncModal = ref<boolean>(false)
const syncSourceDesc = ref<string>('')
const syncSourcePlatform = ref<string>('')
const syncSourceAccountKey = ref<string>('')

// 6. Composables 业务逻辑抽离
const { savedTemplates, loadTemplatesFromStorage, handleTemplateCommand } = useMatrixPresets(
  masterForm,
  platformOverrides,
  accountOverrides
)
const { createPublishBatch } = useMatrixPublish()

// -----------------------------------------------------------------------------
// 计算属性
// -----------------------------------------------------------------------------
const selectedTargets = computed(() => {
  const list: Array<{ platform: string; account: string; nickname?: string }> = []
  selectedTargetKeys.value.forEach(key => {
    const [plat, acc] = key.split(':')
    const found = accountStore.accounts.find(a => a.platform === plat && a.account === acc)
    if (found && !(found.checked === true && found.isValid === false)) {
      list.push({
        platform: plat,
        account: acc,
        nickname: found.nickname || acc
      })
    }
  })
  return list
})

const activePlatformCount = computed(() => {
  const set = new Set<string>()
  selectedTargets.value.forEach(t => set.add(t.platform))
  return set.size
})

const currentPlatformOverride = computed(() => {
  return platformOverrides[currentPlatformTab.value] || platformOverrides['tencent']
})

const currentPlatformAccounts = computed(() => {
  const list: Array<{ account: string; nickname?: string }> = []
  selectedTargetKeys.value.forEach(k => {
    if (k.startsWith(currentPlatformTab.value + ':')) {
      const acc = k.split(':')[1]
      const found = accountStore.accounts.find(a => a.platform === currentPlatformTab.value && a.account === acc)
      if (found && !(found.checked === true && found.isValid === false)) {
        list.push({
          account: acc,
          nickname: found.nickname || acc
        })
      }
    }
  })
  return list
})

// -----------------------------------------------------------------------------
// 同步与重置操作
// -----------------------------------------------------------------------------
const syncAllPlatformsToMaster = () => {
  PLATFORMS.forEach(p => {
    platformOverrides[p.id].isCustomized = false
    platformOverrides[p.id].title = masterForm.title
    platformOverrides[p.id].desc = masterForm.desc
    platformOverrides[p.id].tags = masterForm.tags
    platformOverrides[p.id].thumbnail = masterForm.thumbnail
  })
  ElMessage.success('已将全局通用配置同步至所有平台')
}

const openSyncConfigModal = (payload: { sourceDesc: string; currentPlatform: string; currentAccountKey: string }) => {
  syncSourceDesc.value = payload.sourceDesc
  syncSourcePlatform.value = payload.currentPlatform
  syncSourceAccountKey.value = payload.currentAccountKey
  showSyncModal.value = true
}

const handleExecuteSyncConfig = ({ fields, targetKeys }: { fields: SyncConfigFields; targetKeys: string[] }) => {
  // 获取源配置对象
  let sourceObj: PlatformOverrideSetting
  if (syncSourceAccountKey.value === '__platform__') {
    sourceObj = platformOverrides[syncSourcePlatform.value]
  } else {
    sourceObj = accountOverrides[syncSourceAccountKey.value] || platformOverrides[syncSourcePlatform.value]
  }

  targetKeys.forEach(key => {
    if (!accountOverrides[key]) {
      const [plat] = key.split(':')
      accountOverrides[key] = {
        isCustomized: true,
        title: '',
        desc: '',
        tags: '',
        thumbnail: '',
        thumbnailLandscape: '',
        thumbnailPortrait: '',
        tid: plat === 'bilibili' ? 230 : 0,
        shortTitle: '',
        category: '',
        draft: false,
        schedule: '',
        declaration: '',
        collection: '',
        productLink: '',
        productTitle: '',
        visibility: '0',
        playlist: '',
        bgm: '',
        note: '',
        notef: ''
      }
    }

    const target = accountOverrides[key]
    target.isCustomized = true

    if (fields.title) target.title = sourceObj.title || masterForm.title
    if (fields.desc) target.desc = sourceObj.desc || masterForm.desc
    if (fields.tags) target.tags = sourceObj.tags || masterForm.tags
    if (fields.thumbnail) target.thumbnail = sourceObj.thumbnail || masterForm.thumbnail
    if (fields.schedule) target.schedule = sourceObj.schedule || masterForm.schedule

    if (fields.platformExclusive) {
      target.thumbnailLandscape = sourceObj.thumbnailLandscape
      target.thumbnailPortrait = sourceObj.thumbnailPortrait
      target.tid = sourceObj.tid
      target.shortTitle = sourceObj.shortTitle
      target.category = sourceObj.category
      target.draft = sourceObj.draft
      target.declaration = sourceObj.declaration
      target.collection = sourceObj.collection
      target.productLink = sourceObj.productLink
      target.productTitle = sourceObj.productTitle
      target.visibility = sourceObj.visibility
      target.playlist = sourceObj.playlist
      target.bgm = sourceObj.bgm
      target.note = sourceObj.note
      target.notef = sourceObj.notef
    }
  })
}

const fillDemoContent = () => {
  masterForm.title = '2026 最新 AI 智能自动化矩阵发布系统实测'
  masterForm.desc = '全平台自媒体矩阵高并发一键发布体验！支持微信视频号、抖音、快手、小红书、B站等各大主流平台。\n\n全流程自动化调度，提升自媒体运营效率 10 倍以上！'
  masterForm.tags = '自媒体黑科技,AI工具,视频号运营,自动化分发,爆款技巧'
  ElMessage.success('已填入标准演示作品文案')
}

const resetAllForm = () => {
  ElMessageBox.confirm('确定要清空当前所有通用文案与各平台差异化设置吗？', '重置确认', {
    type: 'warning'
  }).then(() => {
    masterForm.title = ''
    masterForm.desc = ''
    masterForm.tags = ''
    masterForm.filePath = ''
    masterForm.thumbnail = ''
    masterForm.images = []
    masterForm.schedule = ''

    PLATFORMS.forEach(p => {
      platformOverrides[p.id].isCustomized = false
      platformOverrides[p.id].title = ''
      platformOverrides[p.id].desc = ''
      platformOverrides[p.id].tags = ''
      platformOverrides[p.id].thumbnail = ''
    })

    Object.keys(accountOverrides).forEach(k => {
      delete accountOverrides[k]
    })

    ElMessage.success('配置已重置')
  }).catch(() => {})
}

const handleStartPublish = () => {
  createPublishBatch({
    selectedTargets: selectedTargets.value,
    masterForm,
    platformOverrides,
    accountOverrides,
    concurrency: concurrency.value,
    isHeadless: isHeadless.value
  })
}

// -----------------------------------------------------------------------------
// 生命周期与事件监听
// -----------------------------------------------------------------------------
onMounted(() => {
  loadTemplatesFromStorage()

  // 默认全选所有可用账号
  selectedTargetKeys.value.clear()
  accountStore.accounts.forEach(a => {
    if (!(a.checked === true && a.isValid === false)) {
      selectedTargetKeys.value.add(`${a.platform}:${a.account}`)
    }
  })
})
</script>

<style scoped>
.matrix-studio-workspace {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 84px);
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

.studio-body {
  display: grid;
  grid-template-columns: minmax(460px, 4.4fr) minmax(560px, 5.6fr);
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.matrix-panel {
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  min-width: 0;
}

.matrix-top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.header-summary-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.matrix-dot {
  background: #a855f7;
  box-shadow: 0 0 10px #a855f7;
}

.target-account-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  font-size: 12px;
  color: var(--text-main);
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-account-badge:hover {
  background: rgba(99, 102, 241, 0.22);
  border-color: var(--primary-light);
  transform: translateY(-1px);
}

.target-account-badge strong {
  color: #818cf8;
  font-weight: 700;
}

.arrow-icon {
  font-size: 11px;
  color: #94a3b8;
}

.gradient-btn-sm {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
  border: none !important;
  font-weight: 600;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.matrix-empty-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-glow-box {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #818cf8;
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.2);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 6px;
}

.empty-sub {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 420px;
  line-height: 1.6;
  margin-bottom: 20px;
}

.gradient-btn-matrix {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%) !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
  font-weight: 700;
  padding: 10px 24px;
  border-radius: 8px;
}
</style>
