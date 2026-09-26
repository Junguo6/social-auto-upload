<template>
  <div class="matrix-studio-workspace custom-scrollbar">
    <!-- ===== 第一块：发布设置（3 个 Tab） ===== -->
    <div class="config-block glass-card">
      <div class="block-head">
        <div class="block-title"><span class="idx">1</span>发布设置</div>
      </div>

      <div class="config-tabs">
        <!-- 第一步：上传视频（默认焦点） -->
        <div
          class="config-tab"
          :class="{ active: activeTab === 'media', done: mediaList.length > 0 }"
          @click="activeTab = 'media'"
        >
          <span class="tab-num">{{ mediaList.length > 0 ? '✓' : '1' }}</span>
          <span>上传视频</span>
          <span class="tab-cnt" v-if="mediaList.length > 0">{{ mediaList.length }}</span>
        </div>
        <!-- 第二步：选择账号 -->
        <div
          class="config-tab"
          :class="{ active: activeTab === 'account', done: selectedAccountKeys.length > 0 }"
          @click="activeTab = 'account'"
        >
          <span class="tab-num">{{ selectedAccountKeys.length > 0 ? '✓' : '2' }}</span>
          <span>选择账号</span>
          <span class="tab-cnt" v-if="selectedAccountKeys.length > 0">{{ selectedAccountKeys.length }}</span>
        </div>
        <!-- 第三步：发布信息 -->
        <div
          class="config-tab"
          :class="{ active: activeTab === 'info', done: step3Done }"
          @click="activeTab = 'info'"
        >
          <span class="tab-num">{{ step3Done ? '✓' : '3' }}</span>
          <span>发布信息</span>
          <span class="tab-cnt" v-if="configuredPlatformCount > 0">{{ configuredPlatformCount }}</span>
        </div>
      </div>

      <div class="config-body">
        <!-- 第一步：上传视频 -->
        <MediaListCard
          v-show="activeTab === 'media'"
          v-model:media-list="mediaList"
          v-model:selected-media-ids="selectedMediaIds"
          v-model:unit-level="unitLevel"
        />
        <!-- 第二步：选择账号 -->
        <AccountCardPicker
          v-show="activeTab === 'account'"
          v-model:selected-keys="selectedAccountKeys"
        />
        <!-- 第三步：发布信息 (直接按平台 Tab 独立配置) -->
        <PublishInfoHub
          v-show="activeTab === 'info'"
          v-model:platform-configs="platformOverrides"
          v-model:rule-config="ruleConfig"
          :selected-accounts="activeAccounts"
          :media-count="activeMediaList.length"
          @switch-to-account="activeTab = 'account'"
        />
      </div>
    </div>

    <!-- ===== 第二块：账号 × 视频 对应关系 ===== -->
    <div class="matrix-block glass-card">
      <div class="block-head">
        <div class="block-title"><span class="idx">2</span>内容与账号对应表</div>
        <div class="block-tools">
          <el-button
            size="small"
            class="matrix-view-btn"
            @click="crossMatrixModalVisible = true"
          >
            <el-icon><Grid /></el-icon>
            <span>全景矩阵透视与微调</span>
          </el-button>
        </div>
      </div>

      <!-- 下半区：内容与账号对应表（层级表格） -->
      <ContentAccountTable
        :media-list="activeMediaList"
        :selected-accounts="activeAccounts"
        :matrix-map="matrixMap"
        :unit-level="unitLevel"
        @update:matrix-map="onMatrixMapUpdate"
      />
    </div>

    <!-- 3. 底部常驻调度执行控制 Dock -->
    <div class="studio-bottom-bar glass-card">
      <div class="summary-info">
        <span class="summary-main">
          待发 <strong>{{ activeMediaList.length }}</strong> ·
          激活 <strong>{{ totalActivatedTaskCount }}</strong> ·
          账号 <strong>{{ activeAccounts.length }}</strong>
        </span>
      </div>

      <div class="dock-controls">
        <el-popover placement="top" :width="250" trigger="click">
          <template #reference>
            <el-button size="small" class="glass-btn">
              高级设置 · 同时发布 {{ concurrency }} · {{ isHeadless ? '后台静默运行' : '显示浏览器' }}
            </el-button>
          </template>
          <div class="adv-row">
            <span class="adv-label">同时发布数</span>
            <el-input-number v-model="concurrency" :min="1" :max="8" size="small" />
          </div>
          <div class="adv-row">
            <span class="adv-label">后台静默运行</span>
            <el-tooltip content="在后台静默运行，不弹出浏览器窗口（推荐）" placement="top">
              <el-switch v-model="isHeadless" />
            </el-tooltip>
          </div>
        </el-popover>

        <el-tooltip content="按当前对应关系生成发布计划，创建后前往计划管理中心执行" placement="top">
          <el-button
            type="primary"
            class="gradient-btn-lg publish-submit-btn"
            :disabled="activeMediaList.length === 0 || activeAccounts.length === 0 || totalActivatedTaskCount === 0"
            @click="handleStartPublish"
          >
            <el-icon><Promotion /></el-icon>
            <span>创建发布计划 ({{ totalActivatedTaskCount }})</span>
          </el-button>
        </el-tooltip>
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

    <!-- 5. 全景矩阵透视与微调大弹窗 -->
    <el-dialog
      v-model="crossMatrixModalVisible"
      title="全景矩阵透视与差异化微调"
      width="94vw"
      top="4vh"
      append-to-body
      :z-index="2500"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      class="cross-matrix-dialog"
    >
      <div class="cross-matrix-modal-wrap custom-scrollbar">
        <CrossPublishMatrix
          :media-list="activeMediaList"
          :selected-accounts="activeAccounts"
          :matrix-map="matrixMap"
          :master-form="masterForm"
          :rule-config="ruleConfig"
          :platform-overrides="platformOverrides"
          @update:matrix-map="onMatrixMapUpdate"
        />
      </div>
      <template #footer>
        <div class="matrix-dialog-foot">
          <span class="foot-tip">💡 在上方流水线或透视表中可针对单个视频 × 单个账号独立修改标题、独立定时排期或覆盖参数。所有微调实时生效。</span>
          <el-button type="primary" @click="crossMatrixModalVisible = false">
            完成微调并返回
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建发布计划确认框 -->
    <el-dialog
      v-model="createConfirmVisible"
      title="确认创建发布计划"
      width="440px"
      align-center
      :close-on-click-modal="false"
      @close="handleCancelCreate"
    >
      <div class="create-confirm-body">
        <div class="confirm-field">
          <label>计划名称</label>
          <el-input
            v-model="batchName"
            placeholder="给这批计划起个名字，方便日后查找"
            maxlength="30"
            show-word-limit
            @keyup.enter="handleConfirmCreate"
          />
        </div>

        <div class="confirm-summary">
          <div class="summary-row">
            <span>内容</span>
            <span><b>{{ createSummary.medias }}</b> 组</span>
          </div>
          <div class="summary-row">
            <span>账号</span>
            <span><b>{{ createSummary.acctCount }}</b> 个（{{ createSummary.platformText }}）</span>
          </div>
          <div class="summary-row highlight" :class="{ 'limit-exceeded': isTrialTaskLimitExceeded }">
            <span>合计</span>
            <span>将创建 <b>{{ createSummary.total }}</b> 个发布计划</span>
          </div>
          <div class="summary-row">
            <span>间隔</span>
            <span>每条 {{ concurrency }} 并发 · 间隔见计划管理中心</span>
          </div>
        </div>
        <!-- 试用版超标警告 -->
        <div v-if="isTrialTaskLimitExceeded" class="trial-limit-warn">
          <el-icon><WarningFilled /></el-icon>
          <div>
            <b>超出试用版任务数上限</b><br />
            试用版单次最多 {{ authStore.TRIAL_TASK_LIMIT }} 个发布计划，开通后可解除限制
            <el-button type="primary" link size="small" @click="authStore.openAuthModal(); createConfirmVisible = false">
              了解详情
            </el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="handleCancelCreate">取消</el-button>
        <el-button
          type="primary"
          :disabled="!batchName.trim() || isTrialTaskLimitExceeded"
          @click="handleConfirmCreate"
        >
          确认创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, WarningFilled, Grid } from '@element-plus/icons-vue'
import { useAccountStore } from '../stores/accountStore'
import { useSettingsStore } from '../stores/settingsStore'
import { useAuthStore } from '../stores/authStore'
import { useMatrixPresets } from '../composables/useMatrixPresets'
import { useMatrixPublish } from '../composables/useMatrixPublish'
import { getPlatformConfig } from '../config/platforms'
import type {
  MediaItem,
  MasterForm,
  BatchRuleConfig,
  MatrixCellConfig,
  PlatformOverrideSetting,
  SyncConfigFields
} from '../types/matrix'

// 子组件引入
import MediaListCard from '../components/matrix/MediaListCard.vue'
import AccountCardPicker from '../components/matrix/AccountCardPicker.vue'
import PublishInfoHub from '../components/matrix/PublishInfoHub.vue'
import CrossPublishMatrix from '../components/matrix/CrossPublishMatrix.vue'
import ContentAccountTable from '../components/matrix/ContentAccountTable.vue'
import SyncConfigModal from '../components/matrix/SyncConfigModal.vue'

const router = useRouter()
const accountStore = useAccountStore()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const { createCrossMatrixPublishBatch } = useMatrixPublish()

// ---- 创建确认框与矩阵透视弹窗状态 ----
const batchName = ref('')
const createConfirmVisible = ref(false)
const crossMatrixModalVisible = ref(false)
let confirmResolve: ((v: boolean) => void) | null = null

/**
 * 默认计划名：用「被拖入的根文件夹名」（folderCrumbs[0]）。
 * · 用户刚才拖入的就是这个文件夹，命名与动作一一对应，最直观
 * · 不要用 folderCrumbs 的最后一节（那是内容子目录，一次创建可能含多个）
 * · 多个根文件夹时用「主名 等 N 个」
 */
function defaultBatchName(): string {
  const list = activeMediaList.value || []
  if (list.length === 0) return `发布计划 ${fmtToday()}`

  // 收集所有出现过的根文件夹名（保持出现顺序、去重）
  const roots: string[] = []
  list.forEach((m) => {
    const root = m.folderCrumbs?.[0]
    if (root && !roots.includes(root)) roots.push(root)
  })

  if (roots.length === 1) return roots[0]                           // 单根：直接用
  if (roots.length > 1)  return `${roots[0]} 等 ${roots.length} 个` // 多根

  // 没有目录层级（拖入的是单个文件）：退回文件名（去扩展名）
  const name = list[0]?.fileName || ''
  if (name) return name.replace(/\.[^.]+$/, '')

  // 最后兜底
  return `发布计划 ${fmtToday()}`
}

/** 今天 MM-DD */
function fmtToday(): string {
  const d = new Date()
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 打开确认框，返回用户是否确认 */
function confirmBatchCreation(): Promise<boolean> {
  batchName.value = defaultBatchName()
  createConfirmVisible.value = true
  return new Promise((resolve) => { confirmResolve = resolve })
}

function handleConfirmCreate() {
  createConfirmVisible.value = false
  confirmResolve?.(true)
  confirmResolve = null
}

function handleCancelCreate() {
  createConfirmVisible.value = false
  confirmResolve?.(false)
  confirmResolve = null
}

/** 摘要：内容组数 / 账号数与平台分布 / 任务总数 */
const createSummary = computed(() => {
  const medias = activeMediaList.value.length
  const accts = activeAccounts.value
  const byPlatform = new Map<string, number>()
  accts.forEach((a) => byPlatform.set(a.platform, (byPlatform.get(a.platform) || 0) + 1))
  const platformText = Array.from(byPlatform.entries())
    .map(([p, n]) => `${platformName(p)} ${n}`)
    .join(' · ')
  let total = 0
  Object.values(matrixMap || {}).forEach((cells: any) => { total += Object.keys(cells || {}).length })
  if (total === 0) total = medias * accts.length
  return { medias, acctCount: accts.length, platformText, total }
})

function platformName(pid: string): string {
  return getPlatformConfig(pid)?.name || pid
}

// 1. 待发视频清单与已选 ID
const mediaList = ref<MediaItem[]>([])
const selectedMediaIds = ref<string[]>([])

/** 分配/汇总的单位层级（由上传区设定，对应表据此汇总与分配） */
const unitLevel = ref(2)

/** 素材被清空时，「以第几层为单位」回归默认（第 2 层），
 *  避免上一批素材的层级选择残留到下一批 */
watch(mediaList, (list) => {
  if (list.length === 0) {
    unitLevel.value = 2
  }
})

// 2. 目标矩阵账号 keys ("platform:account")
const selectedAccountKeys = ref<string[]>([])

// 发布设置当前 Tab：media=上传视频 / account=选择账号 / info=发布信息
const activeTab = ref<'media' | 'account' | 'info'>('media')

// 3. 通用基础主模板 (保留作为全局安全兜底)
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

// 步骤完成状态统一计算源
const step1Done = computed(() => selectedAccountKeys.value.length > 0)
const step2Done = computed(() => step1Done.value && mediaList.value.length > 0)
const configuredPlatformCount = computed(() => {
  const platforms = Array.from(new Set(activeAccounts.value.map(a => a.platform)))
  return platforms.filter(p => !!platformOverrides[p]?.title?.trim()).length
})
const step3Done = computed(() => step2Done.value && (configuredPlatformCount.value > 0 || !!masterForm.title.trim()))

// 预设模板（必须在 masterForm 之后创建，否则 TDZ 运行时崩溃）
// 顶栏预设模板 UI 已下线；仅保留历史模板的加载（onMounted 调用，避免残留数据引发的状态不一致）
const { loadTemplatesFromStorage } = useMatrixPresets(masterForm, {}, {})

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

/**
 * 对应表回传整份分配表时，保持 matrixMap 的 reactive 引用不被替换。
 * 直接 matrixMap = newMap 会断开响应式（且 const 变量赋值会报错），
 * 导致子组件再次收到 props.matrixMap 时拿不到更新，界面表现为"第一次分配不显示"。
 */
function onMatrixMapUpdate(map: Record<string, Record<string, MatrixCellConfig>>) {
  // 先清空旧 key，再合并新内容（原地更新，引用不变）
  Object.keys(matrixMap).forEach((k) => delete matrixMap[k])
  Object.assign(matrixMap, map)
}

// 底部调度控制
const concurrency = ref(settingsStore.settings.concurrency || 3)
const isHeadless = ref(settingsStore.settings.headless)

watch(isHeadless, (v) => settingsStore.updateSettings({ headless: v }))

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

// 试用版任务数是否超标（单次最多 10 个发布任务）
const isTrialTaskLimitExceeded = computed(() =>
  authStore.isTrialTaskLimitExceeded(createSummary.value.total)
)

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

// 平台差异化微调配置字典: platform -> PlatformOverrideSetting
const platformOverrides = reactive<Record<string, PlatformOverrideSetting>>({})

// 提取当前步骤 ② 所选账号涉及的平台列表
const selectedPlatforms = computed<string[]>(() => {
  const set = new Set<string>()
  activeAccounts.value.forEach(acc => {
    if (acc.platform) set.add(acc.platform)
  })
  return Array.from(set)
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

// 一键重置（当前 UI 已无入口，保留函数以便后续挂到执行栏）
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

  // 前置鉴权校验，未激活友好拦截
  const authorized = await authStore.ensurePublishAuth('创建发布计划')
  if (!authorized) {
    return
  }

  // 试用版任务数上限拦截（在确认框之前拦截，避免弹了框才发现超限）
  if (isTrialTaskLimitExceeded.value) {
    ElMessage.warning(`试用版单次最多 ${authStore.TRIAL_TASK_LIMIT} 个发布计划，请精简内容或账号组合后重试`)
    return
  }

  // 弹出确认框：命名 + 摘要确认（创建不可逆，值得停一下）
  const confirmed = await confirmBatchCreation()
  if (!confirmed) return

  try {
    const batchId = createCrossMatrixPublishBatch({
      mediaList: activeMediaList.value,
      selectedAccounts: activeAccounts.value,
      matrixMap,
      masterForm,
      ruleConfig,
      platformOverrides,
      concurrency: concurrency.value,
      isHeadless: isHeadless.value,
      batchName: batchName.value
    })

    if (batchId) {
      ElMessage.success(`已创建 ${totalActivatedTaskCount.value} 个发布计划，正在前往计划管理中心…`)
      // 延迟引导跳转到计划管理中心
      setTimeout(() => {
        router.push('/tasks')
      }, 600)
    } else {
      ElMessage.warning('未能创建发布计划，请检查配置后重试')
    }
  } catch (err: any) {
    console.error('发布计划提交失败:', err)
    ElMessage.error(`计划提交失败: ${err?.message || '未知异常'}`)
  }
}

// 页面挂载初始化
onMounted(() => {
  // 加载预设模板
  loadTemplatesFromStorage()
})
</script>

<style scoped>
.matrix-studio-workspace {
  display: flex;
  flex-direction: row;      /* 左：发布设置 / 右：内容与账号对应表 */
  align-items: stretch;
  gap: 20px;
  height: calc(100vh - 64px);
  overflow: hidden;         /* 由左右两个区块各自内部滚动 */
  padding: 20px 24px 96px;  /* 底部 96px 避开固定执行栏 */
  box-sizing: border-box;
}

/* ===== 两大块（左右并排） ===== */
.config-block,
.matrix-block {
  display: flex;
  flex-direction: column;
  overflow-y: auto;         /* 各自内部滚动 */
  min-width: 0;             /* 防止 flex 子项被内容撑破 */
}

/* 左侧：发布设置（窄一些，表单够用即可） */
.config-block {
  flex: 0 0 45%;
  max-width: 860px;         /* 超宽屏时不让左侧无限变宽 */
}

/* 右侧：内容与账号对应表（占满剩余空间） */
.matrix-block {
  flex: 1;
  overflow: hidden;
}

/* 左右并排时兜底圆角，避免窄宽度下被裁切 */
.config-block,
.matrix-block {
  border-radius: 12px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* 下边框从灰线改为主色细线：强化左右两块的分区感，同时不抢视线 */
  padding: 13px 18px 11px;                      /* 底边加粗 1px，补回高度差 */
  border-bottom: 2px solid rgba(79, 70, 229, 0.32);
}

.block-title {
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-main);
}

/* 区块编号：方形小标（圆角 6px）。
   刻意与「发布设置」页签里的圆形数字徽标（.tab-num，radius 50%）区分：
   同一屏里出现两种数字时，靠「方 vs 圆」+ 颜色层次就能分清谁是章节、谁是步骤 */
.block-title .idx {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-right: 7px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(79, 70, 229, 0.10);
  border: 1px solid rgba(79, 70, 229, 0.28);
  vertical-align: -2px;
}

/* ===== Tab ===== */
.config-tabs {
  display: flex;
  gap: 4px;
  padding: 12px 18px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.config-tab {
  font-size: 13px;
  padding: 9px 18px;
  border-radius: 10px 10px 0 0;
  cursor: pointer;
  color: var(--text-muted);
  border: 1px solid transparent;
  border-bottom: none;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  top: 1px;
  transition: all 0.2s ease;
}

.config-tab:hover {
  color: var(--text-main);
}

.config-tab.active {
  background: var(--bg-detail);
  color: var(--text-main);
  font-weight: 700;
  border-color: var(--border-subtle);
  border-bottom: 1px solid var(--bg-detail);
}

.tab-num {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--bg-input);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
}

/* 选中 / 完成态：徽标底色变深 → 数字必须转白，否则灰字在主色/绿底上看不清 */
.config-tab.active .tab-num {
  background: var(--primary-color);
  color: #fff;
}

.config-tab.done .tab-num {
  background: var(--status-success);
  color: #fff;
}

.tab-cnt {
  font-size: 11px;
  background: rgba(79, 70, 229, 0.16);
  color: var(--primary-color);
  padding: 0 6px;
  border-radius: 9px;
  font-weight: 600;
}

.tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--status-danger);
}

.config-body {
  flex: 1 1 auto;           /* 吃掉 config-block 的剩余高度 */
  min-height: 360px;        /* 兜底：内容区至少这么高，避免整块塌陷不可见 */
  display: flex;
  flex-direction: column;
  padding: 16px 18px 18px;
}

/* 三个 Tab 组件（v-show 切换，同时只有一个可见）撑满这份高度 */
.config-body > * {
  flex: 1 1 auto;
  min-height: 320px;   /* 兜底：避免 flex-basis:0 在高度不确定时被压成 0，导致内容整块不可见 */
}

/* Tab 内组件自带 glass-card 边框，去掉重复外框避免"卡片套卡片" */
.config-body :deep(.glass-card) {
  border: none;
  background: transparent;
  box-shadow: none;
  /* padding: 0; */
}

/* 底部执行 Dock */
.studio-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 220px;
  right: 0;
  height: 52px;
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
  gap: 12px;
}

.adv-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.adv-label {
  font-size: 12.5px;
  color: var(--text-secondary);
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

/* 创建确认框 */
.create-confirm-body { display: flex; flex-direction: column; gap: 14px; }
.confirm-field { display: flex; flex-direction: column; gap: 6px; }
.confirm-field label { font-size: 12px; color: var(--text-muted); }

.confirm-summary {
  background: var(--bg-input); border: 1px solid var(--border-subtle);
  border-radius: 10px; padding: 10px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.summary-row { display: flex; justify-content: space-between; font-size: 12.5px; color: var(--text-muted); }
.summary-row b { color: var(--text-main); }
.summary-row.highlight b { color: var(--primary-color); font-size: 14px; }

/* 超标时合计行变红 */
.summary-row.limit-exceeded {
  color: var(--status-danger);
}
.summary-row.limit-exceeded b {
  color: var(--status-danger) !important;
}

/* 矩阵弹窗按钮与全景透视弹窗 */
.matrix-view-btn {
  background: rgba(64, 158, 255, 0.08);
  border: 1px solid rgba(64, 158, 255, 0.3);
  color: var(--el-color-primary, #409eff);
  font-weight: 500;
  transition: all 0.2s ease;
}

.matrix-view-btn:hover {
  background: rgba(64, 158, 255, 0.16);
  border-color: var(--el-color-primary, #409eff);
  transform: translateY(-1px);
}

.cross-matrix-modal-wrap {
  max-height: 75vh;
  overflow-y: auto;
  padding: 4px 6px;
}

:global(.cross-matrix-dialog) {
  border-radius: 14px !important;
  background: var(--bg-card, #1e293b) !important;
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1)) !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5) !important;
  overflow: hidden !important;
}

:global(.cross-matrix-dialog .el-dialog__header) {
  padding: 16px 20px !important;
  margin-right: 0 !important;
  border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08)) !important;
}

:global(.cross-matrix-dialog .el-dialog__title) {
  font-size: 16px !important;
  font-weight: 700 !important;
  color: var(--text-main, #f8fafc) !important;
}

:global(.cross-matrix-dialog .el-dialog__body) {
  padding: 16px 20px !important;
  background: transparent !important;
}

:global(.cross-matrix-dialog .el-dialog__footer) {
  padding: 14px 20px !important;
  border-top: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08)) !important;
  background: rgba(0, 0, 0, 0.15) !important;
}

.matrix-dialog-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.matrix-dialog-foot .foot-tip {
  font-size: 12px;
  color: var(--text-secondary, #909399);
}

/* 试用版超标警告 */
.trial-limit-warn {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(245, 108, 108, 0.08);
  border: 1px solid rgba(245, 108, 108, 0.3);
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--status-danger);
  line-height: 1.5;
}
.trial-limit-warn .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}
.trial-limit-warn b {
  color: var(--status-danger);
}
</style>
