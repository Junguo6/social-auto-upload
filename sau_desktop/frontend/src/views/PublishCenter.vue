<template>
  <div class="matrix-studio-workspace custom-scrollbar">
    <!-- 1. 顶部操作栏与预设模板 -->
    <StudioTopBar
      :saved-templates="savedTemplates"
      @template-command="handleTemplateCommand"
      @fill-demo="fillDemoContent"
      @reset-all="resetAllForm"
    />

    <!-- 步骤导航指示条 -->
    <div class="step-guide-bar glass-card">
      <div class="guide-step" :class="{ done: mediaList.length > 0, active: mediaList.length === 0 }">
        <span class="step-num">{{ mediaList.length > 0 ? '✓' : '1' }}</span>
        <span class="step-text">添加待发视频 ({{ mediaList.length }})</span>
      </div>
      <div class="step-connector"></div>
      <div class="guide-step" :class="{ done: selectedAccountKeys.length > 0, active: mediaList.length > 0 && selectedAccountKeys.length === 0 }">
        <span class="step-num">{{ selectedAccountKeys.length > 0 ? '✓' : '2' }}</span>
        <span class="step-text">选择矩阵账号 ({{ selectedAccountKeys.length }})</span>
      </div>
      <div class="step-connector"></div>
      <div class="guide-step" :class="{ done: !!masterForm.title, active: selectedAccountKeys.length > 0 && !masterForm.title }">
        <span class="step-num">{{ masterForm.title ? '✓' : '3' }}</span>
        <span class="step-text">规则与批量变量</span>
      </div>
      <div class="step-connector"></div>
      <div class="guide-step" :class="{ active: mediaList.length > 0 && selectedAccountKeys.length > 0 }">
        <span class="step-num">4</span>
        <span class="step-text">透视矩阵确认</span>
      </div>
    </div>

    <!-- 2. 主体工作区 (四步线性与矩阵流) -->
    <div class="studio-content-flow">
      <!-- 上半区：步骤 1 与 步骤 2 (双列并排) -->
      <div class="two-col-grid">
        <!-- 步骤 1: 待发视频素材清单 -->
        <MediaListCard
          v-model:media-list="mediaList"
          v-model:selected-media-ids="selectedMediaIds"
        />

        <!-- 步骤 2: 目标矩阵账号选择 -->
        <AccountCardPicker
          v-model:selected-keys="selectedAccountKeys"
        />
      </div>

      <!-- 中间区：步骤 3 全局信息与批量变量规则 -->
      <PublishRuleForm
        v-model:master-form="masterForm"
        v-model:rule-config="ruleConfig"
        :media-list="activeMediaList"
      />

      <!-- 下半区：步骤 4 视频 × 账号双视角交叉透视矩阵 -->
      <CrossPublishMatrix
        :media-list="activeMediaList"
        :selected-accounts="activeAccounts"
        v-model:matrix-map="matrixMap"
        :master-form="masterForm"
        :rule-config="ruleConfig"
        @open-sync="handleOpenSyncModal"
      />
    </div>

    <!-- 3. 底部常驻调度执行控制 Dock -->
    <div class="studio-bottom-bar glass-card">
      <div class="summary-info">
        <span class="summary-dot"></span>
        <span class="summary-main">
          已就绪 <strong>{{ activeMediaList.length }}</strong> 个待发视频 ·
          共激活 <strong>{{ totalActivatedTaskCount }}</strong> 次独立发布 ·
          涉及 <strong>{{ activeAccounts.length }}</strong> 个矩阵账号
        </span>
      </div>

      <div class="dock-controls">
        <div class="control-item">
          <span class="control-label">并发 Goroutines:</span>
          <el-input-number
            v-model="concurrency"
            :min="1"
            :max="8"
            size="small"
            class="concurrency-input"
          />
        </div>

        <div class="control-item">
          <el-tooltip content="静默在后台以无头无窗模式运行浏览器发布" placement="top">
            <el-switch
              v-model="isHeadless"
              active-text="静默无头执行"
              inactive-text="前台可见"
            />
          </el-tooltip>
        </div>

        <el-button
          type="primary"
          class="gradient-btn-lg publish-submit-btn"
          :disabled="activeMediaList.length === 0 || activeAccounts.length === 0 || totalActivatedTaskCount === 0"
          @click="handleStartPublish"
        >
          <el-icon><Promotion /></el-icon>
          <span>立即执行矩阵发布 ({{ totalActivatedTaskCount }})</span>
        </el-button>
      </div>
    </div>

    <!-- 4. 弹窗：跨账号/跨平台一键同步配置克隆器 -->
    <SyncConfigModal
      v-model="showSyncModal"
      :source-description="syncSourceDesc"
      :current-platform="syncSourcePlatform"
      :current-account-key="syncSourceAccountKey"
      :selected-targets="activeAccounts"
      @confirm-sync="handleExecuteSyncConfig"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAccountStore } from '../stores/accountStore'
import { useSettingsStore } from '../stores/settingsStore'
import { useMatrixPresets } from '../composables/useMatrixPresets'
import { useMatrixPublish } from '../composables/useMatrixPublish'
import type {
  MediaItem,
  MasterForm,
  BatchRuleConfig,
  MatrixCellConfig,
  PlatformOverrideSetting,
  SyncConfigFields
} from '../types/matrix'

// 子组件引入
import StudioTopBar from '../components/matrix/StudioTopBar.vue'
import MediaListCard from '../components/matrix/MediaListCard.vue'
import AccountCardPicker from '../components/matrix/AccountCardPicker.vue'
import PublishRuleForm from '../components/matrix/PublishRuleForm.vue'
import CrossPublishMatrix from '../components/matrix/CrossPublishMatrix.vue'
import SyncConfigModal from '../components/matrix/SyncConfigModal.vue'

const router = useRouter()
const accountStore = useAccountStore()
const settingsStore = useSettingsStore()
const { savedTemplates, saveAsTemplate, loadTemplate } = useMatrixPresets()
const { createCrossMatrixPublishBatch } = useMatrixPublish()

// 1. 待发视频清单与已选 ID
const mediaList = ref<MediaItem[]>([])
const selectedMediaIds = ref<string[]>([])

// 2. 目标矩阵账号 keys ("platform:account")
const selectedAccountKeys = ref<string[]>([])

// 3. 通用基础主模板 (Master Form)
const masterForm = reactive<MasterForm>({
  action: 'upload-video',
  filePath: '',
  images: [],
  title: '{视频名}',
  desc: '',
  tags: '',
  thumbnail: '',
  schedule: ''
})

// 批量排期与变量规则配置
const ruleConfig = reactive<BatchRuleConfig>({
  titleTemplate: '{视频名}',
  episodeMode: 'auto',
  startEpisode: 1,
  episodeStep: 1,
  padZero: false,
  scheduleType: 'immediate',
  startScheduleTime: '',
  intervalMinutes: 30
})

// 4. 视频 × 账号 交叉透视矩阵字典: mediaId -> "platform:account" -> CellConfig
const matrixMap = reactive<Record<string, Record<string, MatrixCellConfig>>>({})

// 底部调度控制
const concurrency = ref(settingsStore.concurrency || 3)
const isHeadless = ref(true)

// 同步克隆弹窗状态
const showSyncModal = ref(false)
const syncSourceDesc = ref('')
const syncSourcePlatform = ref('')
const syncSourceAccountKey = ref('')
const activeSyncCell = ref<any>(null)

// 活跃的有效待发视频清单 (勾选项优先，若未勾选单项则默认全部)
const activeMediaList = computed(() => {
  if (selectedMediaIds.value.length > 0) {
    return mediaList.value.filter(m => selectedMediaIds.value.includes(m.id))
  }
  return mediaList.value
})

// 活跃的目标账号列表
const activeAccounts = computed(() => {
  return selectedAccountKeys.value.map(k => {
    const [plat, acc] = k.split(':')
    const item = accountStore.accounts.find(a => a.platform === plat && a.account === acc)
    return {
      platform: plat,
      account: acc,
      nickname: item?.nickname || acc,
      isValid: item?.isValid
    }
  })
})

// 计算当前矩阵中已启用的有效发布任务总数
const totalActivatedTaskCount = computed(() => {
  let count = 0
  activeMediaList.value.forEach(m => {
    activeAccounts.value.forEach(acc => {
      const accKey = `${acc.platform}:${acc.account}`
      const cell = matrixMap[m.id]?.[accKey]
      if (!cell || cell.enabled) {
        count++
      }
    })
  })
  return count
})

// 顶部模板操作
const handleTemplateCommand = (cmd: string) => {
  if (cmd === '__save__') {
    ElMessageBox.prompt('请输入该预设模板名称 (如：通用矩阵发布模板)', '保存为矩阵发布模板', {
      confirmButtonText: '确定保存',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '模板名称不能为空'
    }).then(({ value }) => {
      saveAsTemplate(value.trim(), masterForm, {}, {})
      ElMessage.success(`模板 [${value.trim()}] 保存成功`)
    }).catch(() => {})
    return
  }

  const found = loadTemplate(cmd)
  if (found) {
    Object.assign(masterForm, found.master)
    ElMessage.success(`已应用预设模板: ${found.name}`)
  }
}

// 示例数据填充
const fillDemoContent = () => {
  masterForm.title = 'AI科技实测 - 第{集数}集 | {视频名}'
  masterForm.desc = '今天给大家深度测试最新自动化发布工作流，效率直接翻倍！点赞关注获取更多黑科技。'
  masterForm.tags = 'AI工具, 效率提升, 黑科技, 自动化'
  ElMessage.success('已填入常用示例规则')
}

// 一键重置
const resetAllForm = () => {
  mediaList.value = []
  selectedMediaIds.value = []
  selectedAccountKeys.value = []
  masterForm.title = ''
  masterForm.desc = ''
  masterForm.tags = ''
  masterForm.schedule = ''
  ElMessage.info('已清空当前工作台内容')
}

// 打开克隆同步弹窗
const handleOpenSyncModal = (cellData: any) => {
  if (!cellData) return
  activeSyncCell.value = cellData
  syncSourcePlatform.value = cellData.platform
  syncSourceAccountKey.value = `${cellData.platform}:${cellData.account}`
  syncSourceDesc.value = `视频 [${cellData.mediaName}] · ${cellData.platform} @${cellData.nickname || cellData.account}`
  showSyncModal.value = true
}

// 执行配置克隆同步
const handleExecuteSyncConfig = (payload: { targetAccountKeys: string[]; fields: SyncConfigFields }) => {
  if (!activeSyncCell.value) return
  const srcCell = activeSyncCell.value.cell
  const srcMediaId = activeSyncCell.value.mediaId

  payload.targetAccountKeys.forEach(targetKey => {
    // 确保目标单元格存在
    if (!matrixMap[srcMediaId]) matrixMap[srcMediaId] = {}
    if (!matrixMap[srcMediaId][targetKey]) {
      const [p, a] = targetKey.split(':')
      matrixMap[srcMediaId][targetKey] = {
        enabled: true,
        scheduleMode: 'inherit',
        isCustomized: true,
        override: {
          isCustomized: true,
          title: '',
          desc: '',
          tags: '',
          thumbnail: '',
          thumbnailLandscape: '',
          thumbnailPortrait: '',
          tid: p === 'bilibili' ? 230 : 0,
          shortTitle: '',
          category: '',
          draft: false,
          schedule: '',
          declaration: '',
          collection: '',
          productLink: '',
          productTitle: '',
          visibility: 'public',
          playlist: '',
          bgm: '',
          note: '',
          notef: ''
        }
      }
    }

    const tgt = matrixMap[srcMediaId][targetKey]
    if (payload.fields.title && srcCell.customTitle) {
      tgt.customTitle = srcCell.customTitle
    }
    if (payload.fields.desc && srcCell.override.desc) {
      tgt.override.desc = srcCell.override.desc
    }
    if (payload.fields.tags && srcCell.override.tags) {
      tgt.override.tags = srcCell.override.tags
    }
    if (payload.fields.schedule && srcCell.customSchedule) {
      tgt.scheduleMode = 'scheduled'
      tgt.customSchedule = srcCell.customSchedule
    }
  })

  ElMessage.success(`已将配置一键同步至 ${payload.targetAccountKeys.length} 个账号`)
  showSyncModal.value = false
}

// 提交矩阵批量发布
const handleStartPublish = async () => {
  if (activeMediaList.value.length === 0) {
    ElMessage.warning('请先在步骤 ① 导入待发布视频')
    return
  }
  if (activeAccounts.value.length === 0) {
    ElMessage.warning('请先在步骤 ② 勾选目标矩阵账号')
    return
  }

  try {
    const batchId = createCrossMatrixPublishBatch({
      mediaList: activeMediaList.value,
      selectedAccounts: activeAccounts.value,
      matrixMap,
      masterForm,
      ruleConfig,
      concurrency: concurrency.value,
      isHeadless: isHeadless.value
    })

    if (batchId) {
      // 延迟引导跳转到任务管理中心
      setTimeout(() => {
        router.push('/tasks')
      }, 600)
    }
  } catch (err: any) {
    console.error('发布任务提交失败:', err)
    ElMessage.error(`任务提交失败: ${err?.message || '未知异常'}`)
  }
}

// 页面挂载默认选中有效账号
onMounted(() => {
  if (accountStore.accounts.length > 0 && selectedAccountKeys.value.length === 0) {
    // 默认勾选前 4 个凭证正常的账号
    const valids = accountStore.accounts
      .filter(a => a.isValid)
      .slice(0, 4)
      .map(a => `${a.platform}:${a.account}`)
    selectedAccountKeys.value = valids
  }
})
</script>

<style scoped>
.matrix-studio-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 64px);
  overflow-y: auto;
  padding: 16px 20px 100px;
  box-sizing: border-box;
}

/* 步骤指示条 */
.step-guide-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}

.guide-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
  transition: all 0.25s ease;
}

.guide-step.active {
  color: var(--text-main);
  font-weight: 700;
}

.guide-step.done {
  color: var(--status-success);
}

.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-input);
  border: 1.5px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.guide-step.active .step-num {
  background: var(--primary-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.guide-step.done .step-num {
  background: rgba(16, 185, 129, 0.15);
  border-color: var(--status-success);
  color: var(--status-success);
}

.step-connector {
  flex: 1;
  height: 2px;
  background: var(--border-subtle);
  margin: 0 16px;
}

/* 四步流布局 */
.studio-content-flow {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.two-col-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 1080px) {
  .two-col-grid {
    grid-template-columns: 1fr;
  }
}

/* 底部执行 Dock */
.studio-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 220px;
  right: 0;
  height: 68px;
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  z-index: 99;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
  transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.summary-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 10px var(--status-success);
}

.summary-main {
  font-size: 13px;
  color: var(--text-secondary);
}

.summary-main strong {
  color: var(--primary-color);
  font-size: 15px;
}

.dock-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 12px;
  color: var(--text-muted);
}

.concurrency-input {
  width: 90px;
}

.publish-submit-btn {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 700;
  border-radius: 9px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
