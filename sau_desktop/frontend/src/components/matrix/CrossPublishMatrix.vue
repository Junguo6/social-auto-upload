<template>
  <div class="cross-publish-matrix glass-card">
    <!-- 1. 头部标题与双主视图切换器 -->
    <div class="matrix-header">
      <div class="title-box">
        <span class="step-badge">4</span>
        <div class="title-text-group">
          <div class="main-title">
            <span>视频 × 账号 对应关系矩阵</span>
            <span class="req-star">*</span>
          </div>
          <div class="sub-title">核对每个视频在各账号的发布渠道与时间，支持流水线清单与交叉透视双视图自由切换</div>
        </div>
      </div>

      <!-- 右侧：主视图模式切换 + 子视角控制 -->
      <div class="header-right-tools">
        <!-- 主视图模式切换：流水线清单 vs 交叉大表格 -->
        <el-radio-group v-model="displayMode" size="small" class="mode-radios">
          <el-radio-button value="pipeline">
            <el-icon><Tickets /></el-icon> ☰ 任务流水线 (推荐)
          </el-radio-button>
          <el-radio-button value="grid">
            <el-icon><Grid /></el-icon> ⊞ 交叉透视表
          </el-radio-button>
        </el-radio-group>

        <!-- 仅在交叉大表模式下显示：按视频 / 按账号 视角 -->
        <el-radio-group
          v-if="displayMode === 'grid'"
          v-model="currentView"
          size="small"
          class="sub-view-radios"
          @change="currentPage = 1"
        >
          <el-radio-button value="video">按视频看</el-radio-button>
          <el-radio-button value="account">按账号看</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 视角说明提示条 -->
    <div class="perspective-hint">
      <el-icon class="hint-icon"><InfoFilled /></el-icon>
      <span v-if="displayMode === 'pipeline'">
        <strong>任务流水线视图</strong>：以每个待发视频为主卡片，流式展开各渠道账号，直观清晰、不被横向拉宽，支持单视频一键批量调整。
      </span>
      <span v-else-if="currentView === 'video'">
        <strong>交叉大表 (按视频看)</strong>：行=待发视频，列=矩阵账号。适合横向全局核对跨平台分布。
      </span>
      <span v-else>
        <strong>交叉大表 (按账号看)</strong>：行=矩阵账号，列=待发视频。适合矩阵操盘手核对单号排发计划。
      </span>
      <span class="page-tip">
        (共 {{ totalItemCount }} 项 · 当前第 {{ currentPage }} 页 / 共 {{ totalPages }} 页)
      </span>
    </div>

    <!-- 2. 主体展示区 (双模式) -->
    <div v-if="mediaList.length > 0 && selectedAccounts.length > 0">
      <!-- ========================================== -->
      <!-- 视图 A：【任务流水线清单 (Pipeline Flow)】 -->
      <!-- ========================================== -->
      <div v-if="displayMode === 'pipeline'" class="pipeline-list">
        <div
          v-for="(media, pIdx) in pagedMediaList"
          :key="media.id"
          class="pipeline-card"
        >
          <!-- 视频卡片头部摘要 -->
          <div class="pipeline-card-header">
            <div class="media-title-group">
              <span class="media-num">#{{ (currentPage - 1) * pageSize + pIdx + 1 }}</span>
              <div class="video-info-box">
                <div class="video-file-name" :title="media.fileName">
                  <el-icon><Film /></el-icon>
                  <span>{{ media.fileName }}</span>
                  <span class="ep-tag" v-if="media.parsedEpisode">第 {{ media.parsedEpisode }} 集</span>
                </div>
                <div class="computed-title" :title="resolveTitleTemplate(media, (currentPage - 1) * pageSize + pIdx)">
                  <strong>最终标题:</strong> {{ resolveTitleTemplate(media, (currentPage - 1) * pageSize + pIdx) }}
                </div>
              </div>
            </div>

            <!-- 针对该视频的快捷动作 -->
            <div class="media-batch-actions">
              <el-button size="small" link type="primary" @click="enableAllChannelsForMedia(media.id)">
                全发
              </el-button>
              <el-button size="small" link type="warning" @click="disableAllChannelsForMedia(media.id)">
                全暂停
              </el-button>
            </div>
          </div>

          <!-- 该视频下的所有分发渠道胶囊流 (Channel Capsules) -->
          <div class="channels-flow">
            <div
              v-for="acc in selectedAccounts"
              :key="`${acc.platform}:${acc.account}`"
              class="channel-pill-card"
              :class="{
                disabled: !getCell(media.id, acc).enabled,
                customized: getCell(media.id, acc).isCustomized
              }"
            >
              <!-- 渠道基础信息 (点击切换启用/禁用) -->
              <div class="pill-main" @click="toggleCellEnabled(media.id, acc)">
                <div class="plat-avatar" :style="{ background: getPlatformColor(acc.platform) }">
                  {{ getPlatformShort(acc.platform) }}
                </div>
                <div class="pill-text-col">
                  <div class="pill-acc-name" :title="acc.nickname || acc.account">
                    {{ acc.nickname || acc.account }}
                  </div>
                  <div class="pill-timing-row">
                    <span
                      class="timing-badge"
                      :class="getCellStatusClass(media.id, acc, (currentPage - 1) * pageSize + pIdx)"
                    >
                      <el-icon v-if="getCellStatusText(media.id, acc, (currentPage - 1) * pageSize + pIdx).includes(':')"><Timer /></el-icon>
                      <span>{{ getCellStatusText(media.id, acc, (currentPage - 1) * pageSize + pIdx) }}</span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 精美独立微调胶囊按钮 -->
              <div
                class="pill-tune-btn"
                :class="{ active: getCell(media.id, acc).isCustomized }"
                title="独立微调该发布渠道参数"
                @click.stop="handleOpenDrawer(media, acc)"
              >
                <el-icon><EditPen /></el-icon>
                <span>{{ getCell(media.id, acc).isCustomized ? '已定制' : '微调' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ========================================== -->
      <!-- 视图 B：【交叉透视大表 (Matrix Grid)】    -->
      <!-- ========================================== -->
      <div v-else class="matrix-table-wrap">
        <!-- 视角 1: 按视频看 (行 = 当前页视频, 列 = 全部账号) -->
        <table v-if="currentView === 'video'" class="matrix-table">
          <thead>
            <tr>
              <th class="sticky-col header-corner">
                <span>待发视频 (共 {{ mediaList.length }} 个)</span>
              </th>
              <th
                v-for="acc in selectedAccounts"
                :key="`${acc.platform}:${acc.account}`"
                class="account-header-th"
              >
                <div class="th-content">
                  <span class="plat-mini-tag" :style="{ background: getPlatformColor(acc.platform) }">
                    {{ getPlatformShort(acc.platform) }}
                  </span>
                  <span class="acc-title" :title="acc.nickname || acc.account">
                    {{ acc.nickname || acc.account }}
                  </span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(media, pIdx) in pagedMediaList" :key="media.id">
              <td class="sticky-col media-name-td">
                <div class="media-cell-info">
                  <span class="media-idx">#{{ (currentPage - 1) * pageSize + pIdx + 1 }}</span>
                  <div class="media-text-wrap">
                    <span class="media-title" :title="media.fileName">{{ media.fileName }}</span>
                    <span class="media-sub" v-if="media.parsedEpisode">第 {{ media.parsedEpisode }} 集</span>
                  </div>
                </div>
              </td>

              <td
                v-for="acc in selectedAccounts"
                :key="`${acc.platform}:${acc.account}`"
                class="matrix-cell"
                :class="{ disabled: !getCell(media.id, acc).enabled }"
              >
                <div class="cell-card" @click="handleOpenDrawer(media, acc)">
                  <div class="cell-top-row">
                    <span
                      class="status-pill"
                      :class="getCellStatusClass(media.id, acc, (currentPage - 1) * pageSize + pIdx)"
                    >
                      <el-icon v-if="getCellStatusText(media.id, acc, (currentPage - 1) * pageSize + pIdx).includes(':')"><Timer /></el-icon>
                      <span>{{ getCellStatusText(media.id, acc, (currentPage - 1) * pageSize + pIdx) }}</span>
                    </span>

                    <div
                      class="edit-tune-capsule"
                      :class="{ customized: getCell(media.id, acc).isCustomized }"
                      title="独立微调该单元格参数"
                      @click.stop="handleOpenDrawer(media, acc)"
                    >
                      <el-icon class="tune-icon"><EditPen /></el-icon>
                      <span class="tune-label">{{ getCell(media.id, acc).isCustomized ? '已定制' : '微调' }}</span>
                    </div>
                  </div>

                  <div class="cell-title-preview" :title="resolveCellTitle(media, acc, (currentPage - 1) * pageSize + pIdx)">
                    {{ resolveCellTitle(media, acc, (currentPage - 1) * pageSize + pIdx) }}
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 视角 2: 按账号看 (行 = 当前页账号, 列 = 全部视频) -->
        <table v-else class="matrix-table">
          <thead>
            <tr>
              <th class="sticky-col header-corner">
                <span>矩阵账号 (共 {{ selectedAccounts.length }} 个)</span>
              </th>
              <th
                v-for="(media, mIdx) in mediaList"
                :key="media.id"
                class="media-header-th"
              >
                <div class="th-content">
                  <span class="media-idx">#{{ mIdx + 1 }}</span>
                  <span class="media-th-name" :title="media.fileName">{{ media.fileName }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(acc, pIdx) in pagedAccounts" :key="`${acc.platform}:${acc.account}`">
              <td class="sticky-col account-name-td">
                <div class="acc-cell-info">
                  <span class="plat-mini-tag" :style="{ background: getPlatformColor(acc.platform) }">
                    {{ getPlatformShort(acc.platform) }}
                  </span>
                  <div class="acc-text-wrap">
                    <span class="acc-name-text" :title="acc.nickname || acc.account">
                      {{ acc.nickname || acc.account }}
                    </span>
                    <span class="acc-plat-sub">{{ getPlatformName(acc.platform) }}</span>
                  </div>
                </div>
              </td>

              <td
                v-for="(media, mIdx) in mediaList"
                :key="media.id"
                class="matrix-cell"
                :class="{ disabled: !getCell(media.id, acc).enabled }"
              >
                <div class="cell-card" @click="handleOpenDrawer(media, acc)">
                  <div class="cell-top-row">
                    <span
                      class="status-pill"
                      :class="getCellStatusClass(media.id, acc, mIdx)"
                    >
                      <el-icon v-if="getCellStatusText(media.id, acc, mIdx).includes(':')"><Timer /></el-icon>
                      <span>{{ getCellStatusText(media.id, acc, mIdx) }}</span>
                    </span>

                    <div
                      class="edit-tune-capsule"
                      :class="{ customized: getCell(media.id, acc).isCustomized }"
                      title="独立微调该单元格参数"
                      @click.stop="handleOpenDrawer(media, acc)"
                    >
                      <el-icon class="tune-icon"><EditPen /></el-icon>
                      <span class="tune-label">{{ getCell(media.id, acc).isCustomized ? '已定制' : '微调' }}</span>
                    </div>
                  </div>

                  <div class="cell-title-preview" :title="resolveCellTitle(media, acc, mIdx)">
                    {{ resolveCellTitle(media, acc, mIdx) }}
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 空状态提示 -->
    <div v-else class="matrix-empty">
      <div class="empty-icon"><el-icon><Menu /></el-icon></div>
      <div class="empty-msg">
        {{ mediaList.length === 0 ? '请先在步骤 ① 添加待发布的视频素材' : '请先在步骤 ② 勾选目标矩阵账号' }}
      </div>
      <div class="empty-hint">添加视频和账号后，系统将自动生成对应关系流水线与透视矩阵</div>
    </div>

    <!-- 底部直观分页器 (替代内部滚轮) -->
    <div v-if="totalItemCount > pageSize" class="matrix-pagination-bar">
      <div class="pagination-info">
        <span>当前共 <strong>{{ totalItemCount }}</strong> 项 · 每页展示 {{ pageSize }} 项</span>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5, 10, 15, 20]"
        :total="totalItemCount"
        layout="prev, pager, next, sizes"
        size="small"
        class="custom-pagination"
      />
    </div>

    <!-- 单元格定制抽屉 -->
    <CellConfigDrawer
      v-model="drawerVisible"
      :cell-data="activeCellData"
      @open-sync="$emit('open-sync', activeCellData)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getPlatformConfig } from '../../config/platforms'
import CellConfigDrawer, { type CellDataWrap } from './CellConfigDrawer.vue'
import type { MediaItem, MatrixCellConfig, MasterForm, BatchRuleConfig } from '../../types/matrix'

const props = defineProps<{
  mediaList: MediaItem[]
  selectedAccounts: Array<{ platform: string; account: string; nickname?: string; isValid?: boolean }>
  matrixMap: Record<string, Record<string, MatrixCellConfig>>
  masterForm: MasterForm
  ruleConfig: BatchRuleConfig
}>()

const emit = defineEmits<{
  (e: 'update:matrixMap', map: Record<string, Record<string, MatrixCellConfig>>): void
  (e: 'open-sync', cellData: CellDataWrap | null): void
}>()

// 主展现模式: 'pipeline' (任务流水线清单，默认推荐) | 'grid' (交叉透视大表)
const displayMode = ref<'pipeline' | 'grid'>('pipeline')

// 大表下的子视角: 'video' (行=视频) | 'account' (行=账号)
const currentView = ref<'video' | 'account'>('video')

// 分页状态
const currentPage = ref(1)
const pageSize = ref(5)

// 当前模式/视角的总项数
const totalItemCount = computed(() => {
  if (displayMode.value === 'pipeline' || currentView.value === 'video') {
    return props.mediaList.length
  }
  return props.selectedAccounts.length
})

// 总页数
const totalPages = computed(() => {
  return Math.ceil(totalItemCount.value / pageSize.value) || 1
})

// 当前页的视频列表
const pagedMediaList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return props.mediaList.slice(start, start + pageSize.value)
})

// 当前页的账号列表
const pagedAccounts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return props.selectedAccounts.slice(start, start + pageSize.value)
})

// 抽屉状态
const drawerVisible = ref(false)
const activeCellData = ref<CellDataWrap | null>(null)

// 获取或初始化单元格配置
const getCell = (mediaId: string, acc: { platform: string; account: string }): MatrixCellConfig => {
  const accKey = `${acc.platform}:${acc.account}`
  if (!props.matrixMap[mediaId]) {
    props.matrixMap[mediaId] = {}
  }
  if (!props.matrixMap[mediaId][accKey]) {
    props.matrixMap[mediaId][accKey] = {
      enabled: true,
      scheduleMode: 'inherit',
      isCustomized: false,
      override: {
        isCustomized: false,
        title: '',
        desc: '',
        tags: '',
        thumbnail: '',
        thumbnailLandscape: '',
        thumbnailPortrait: '',
        tid: acc.platform === 'bilibili' ? 230 : 0,
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
  return props.matrixMap[mediaId][accKey]
}

// 解析通用标题模板
const resolveTitleTemplate = (media: MediaItem, mediaIndex: number): string => {
  const tpl = props.masterForm.title || media.fileName
  const ep = media.parsedEpisode || (mediaIndex + 1)
  const baseName = media.fileName.replace(/\.[^/.]+$/, "")
  const todayStr = new Date().toISOString().split('T')[0]

  return tpl
    .replace(/\{集数\}/g, String(ep))
    .replace(/\{视频名\}/g, baseName)
    .replace(/\{日期\}/g, todayStr)
}

// 解析单元格最终标题
const resolveCellTitle = (media: MediaItem, acc: { platform: string; account: string }, mediaIndex: number): string => {
  const cell = getCell(media.id, acc)
  if (cell.customTitle) return cell.customTitle
  return resolveTitleTemplate(media, mediaIndex)
}

// 计算单元格发布时机显示文本
const getCellStatusText = (mediaId: string, acc: { platform: string; account: string }, mediaIndex: number): string => {
  const cell = getCell(mediaId, acc)
  if (!cell.enabled) return '— 不发布'

  if (cell.scheduleMode === 'immediate') return '立即发布'
  if (cell.scheduleMode === 'scheduled' && cell.customSchedule) {
    return cell.customSchedule.substring(5)
  }

  // 继承全局
  if (props.ruleConfig.scheduleType === 'immediate') return '立即发布'
  if (props.ruleConfig.scheduleType === 'interval') {
    if (props.ruleConfig.startScheduleTime) {
      try {
        const start = new Date(props.ruleConfig.startScheduleTime.replace(/-/g, '/'))
        const offset = mediaIndex * (props.ruleConfig.intervalMinutes || 30) * 60 * 1000
        const sched = new Date(start.getTime() + offset)
        const m = String(sched.getMonth() + 1).padStart(2, '0')
        const d = String(sched.getDate()).padStart(2, '0')
        const h = String(sched.getHours()).padStart(2, '0')
        const min = String(sched.getMinutes()).padStart(2, '0')
        return `${m}-${d} ${h}:${min}`
      } catch (e) {}
    }
    return `递增+${mediaIndex * (props.ruleConfig.intervalMinutes || 30)}m`
  }
  if (props.masterForm.schedule) {
    return props.masterForm.schedule.substring(5)
  }
  return '立即发布'
}

// 状态色标
const getCellStatusClass = (mediaId: string, acc: { platform: string; account: string }, mediaIndex: number): string => {
  const cell = getCell(mediaId, acc)
  if (!cell.enabled) return 'status-disabled'
  const text = getCellStatusText(mediaId, acc, mediaIndex)
  if (text.includes(':')) return 'status-scheduled'
  return 'status-immediate'
}

// 流水线视图：切换单渠道开关
const toggleCellEnabled = (mediaId: string, acc: { platform: string; account: string }) => {
  const cell = getCell(mediaId, acc)
  cell.enabled = !cell.enabled
}

// 流水线视图：对某视频全部渠道启用
const enableAllChannelsForMedia = (mediaId: string) => {
  props.selectedAccounts.forEach(acc => {
    getCell(mediaId, acc).enabled = true
  })
}

// 流水线视图：对某视频全部渠道暂停
const disableAllChannelsForMedia = (mediaId: string) => {
  props.selectedAccounts.forEach(acc => {
    getCell(mediaId, acc).enabled = false
  })
}

// 打开微调抽屉
const handleOpenDrawer = (media: MediaItem, acc: { platform: string; account: string; nickname?: string }) => {
  const cell = getCell(media.id, acc)
  const mIdx = props.mediaList.findIndex(m => m.id === media.id)
  activeCellData.value = {
    mediaId: media.id,
    mediaName: media.fileName,
    platform: acc.platform,
    account: acc.account,
    nickname: acc.nickname,
    cell,
    inheritedTitle: resolveTitleTemplate(media, mIdx >= 0 ? mIdx : 0),
    inheritedDesc: props.masterForm.desc,
    inheritedTags: props.masterForm.tags,
    inheritedSchedule: getCellStatusText(media.id, acc, mIdx >= 0 ? mIdx : 0)
  }
  drawerVisible.value = true
}

// 平台图标辅助
const getPlatformName = (pid: string) => getPlatformConfig(pid)?.name || pid
const getPlatformShort = (pid: string) => getPlatformName(pid).substring(0, 2)
const getPlatformColor = (pid: string) => getPlatformConfig(pid)?.color || '#6366f1'
</script>

<style scoped>
.cross-publish-matrix {
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
}

.matrix-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.title-box {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-badge {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--primary-gradient);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.title-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.main-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.req-star {
  color: var(--status-danger);
}

.sub-title {
  font-size: 12px;
  color: var(--text-muted);
}

.header-right-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-radios :deep(.el-radio-button__inner) {
  font-weight: 600;
}

.perspective-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 14px;
}

.hint-icon {
  font-size: 14px;
  color: var(--primary-color);
  flex-shrink: 0;
}

.perspective-hint strong {
  color: var(--primary-color);
}

.page-tip {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

/* ======================================= */
/* 视图 A：【任务流水线清单 (Pipeline)】    */
/* ======================================= */
.pipeline-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipeline-card {
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.pipeline-card:hover {
  border-color: var(--border-highlight);
  background: var(--bg-detail);
}

.pipeline-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.media-title-group {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.media-num {
  font-size: 12px;
  font-weight: 800;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  padding: 2px 7px;
  border-radius: 6px;
  flex-shrink: 0;
}

.video-info-box {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.video-file-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ep-tag {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--primary-gradient);
  padding: 1px 6px;
  border-radius: 4px;
}

.computed-title {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.computed-title strong {
  color: var(--text-muted);
}

.media-batch-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* 渠道胶囊流排版 (流式卡片，无论多少账号都不会拉爆) */
.channels-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.channel-pill-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px 6px 6px;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  min-width: 170px;
  max-width: 230px;
  flex: 1;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.channel-pill-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-1px);
}

.channel-pill-card.disabled {
  opacity: 0.5;
  background: var(--bg-input);
}

.channel-pill-card.customized {
  border-color: rgba(168, 85, 247, 0.5);
  background: rgba(168, 85, 247, 0.05);
}

.pill-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.plat-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.pill-text-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pill-acc-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timing-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  white-space: nowrap;
}

/* 微调胶囊按钮 */
.pill-tune-btn {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px 6px;
  border-radius: 5px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.pill-tune-btn:hover {
  background: var(--primary-gradient);
  border-color: transparent;
  color: #fff;
}

.pill-tune-btn.active {
  background: rgba(168, 85, 247, 0.18);
  border-color: rgba(168, 85, 247, 0.45);
  color: #a855f7;
}

/* ======================================= */
/* 视图 B：【交叉透视大表 (Matrix Grid)】  */
/* ======================================= */
.matrix-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-input);
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;
}

.matrix-table th {
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-detail);
  border-bottom: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-subtle);
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}

.matrix-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-subtle);
  vertical-align: middle;
}

.matrix-table tr:last-child td {
  border-bottom: none;
}

.sticky-col {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--bg-card) !important;
  border-right: 2px solid var(--border-highlight) !important;
  min-width: 170px;
  max-width: 220px;
}

.header-corner {
  color: var(--text-main) !important;
  font-weight: 700 !important;
}

.th-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.plat-mini-tag {
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}

.acc-title {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-main);
}

.media-th-name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-main);
}

.media-cell-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.media-idx {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.media-text-wrap {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.media-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.acc-cell-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.acc-text-wrap {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.acc-name-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.acc-plat-sub {
  font-size: 11px;
  color: var(--text-muted);
}

/* 交叉表单元格 */
.matrix-cell {
  background: var(--bg-input);
  transition: all 0.2s ease;
  min-width: 170px;
}

.matrix-cell:hover {
  background: var(--bg-detail);
}

.matrix-cell.disabled {
  opacity: 0.55;
}

.cell-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
}

.cell-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.1);
}

.cell-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}

.status-immediate {
  background: rgba(16, 185, 129, 0.15);
  color: var(--status-success);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-scheduled {
  background: rgba(245, 158, 11, 0.15);
  color: var(--status-warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-disabled {
  background: rgba(100, 116, 139, 0.15);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

.edit-tune-capsule {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.28);
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.edit-tune-capsule:hover {
  background: var(--primary-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.edit-tune-capsule.customized {
  background: rgba(168, 85, 247, 0.16);
  border-color: rgba(168, 85, 247, 0.45);
  color: #a855f7;
}

.cell-title-preview {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

/* 分页控制条 */
.matrix-pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 14px;
  margin-top: 12px;
  border-top: 1px solid var(--border-subtle);
  flex-wrap: wrap;
  gap: 12px;
}

.pagination-info {
  font-size: 12px;
  color: var(--text-muted);
}

.pagination-info strong {
  color: var(--text-main);
}

/* 空状态 */
.matrix-empty {
  text-align: center;
  padding: 36px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.empty-msg {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
