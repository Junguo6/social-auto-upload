<template>
  <div class="content-account-table">
    <!-- 视角 Tab（同一份对应关系的三种读法） -->
    <div v-if="rows.length > 0" class="view-tabs">
      <button
        class="view-tab"
        :class="{ on: viewMode === 'folder' }"
        @click="switchView('folder')"
      >文件夹视角</button>
      <button
        class="view-tab"
        :class="{ on: viewMode === 'video' }"
        @click="switchView('video')"
      >视频视角</button>
      <button
        class="view-tab"
        :class="{ on: viewMode === 'account' }"
        @click="switchView('account')"
      >账号视角</button>
    </div>

    <!-- 统计行（紧跟 Tab，右侧显示） -->
    <div v-if="rows.length > 0" class="summary-row">
      <span class="summary">
        <b>{{ rows.length }}</b> 个视频 ·
        <b>{{ coveredAccountCount }}</b> 个账号 ·
        <span :class="{ 'is-warn': pendingCount > 0 }">待分配 {{ pendingCount }}</span>
      </span>
    </div>

    <!-- 分配设置卡片 -->
    <div v-if="rows.length > 0" class="assign-card">
      <!-- 汇总层级（仅文件夹视角且素材有层级时） -->
      <div v-if="viewMode === 'folder' && maxFolderDepth >= 1" class="assign-item">
        <span class="assign-label">汇总层级</span>
        <select v-model.number="folderLevel" class="tb-select">
          <option :value="0">全部视频（不分组）</option>
          <option v-for="n in maxFolderDepth" :key="n" :value="n">按第 {{ n }} 层汇总</option>
        </select>
        <span class="assign-sub">分配也按此层级</span>
      </div>

      <!-- 分配方式 -->
      <div class="assign-item">
        <span class="assign-label">分配方式</span>
        <select v-model="assignMode" class="tb-select">
          <option value="sequential">按顺序均分</option>
          <option value="manual">手动指定</option>
        </select>
      </div>

      <div class="assign-actions">
        <button class="tb-btn" @click="reapplyAssign">重新应用分配</button>
        <button class="tb-btn ghost" @click="clearAssign">清空账号分配</button>
        <span v-if="assignHint" class="assign-hint">{{ assignHint }}</span>
      </div>
    </div>

    <!-- ============ 视角 1：文件夹视角 ============ -->
    <div v-if="rows.length > 0 && viewMode === 'folder'" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>内容</th>
            <th style="width: 300px">发布账号</th>
            <th style="width: 92px">状态</th>
            <th style="width: 78px"></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="g in filteredGroups" :key="g.key">
            <!-- 文件夹分区标题行（不可点击，仅作分组识别） -->
            <tr class="group-row" :class="{ 'no-assign': g.assigned === 0 }">
              <td class="col-content">
                <div class="folder" :title="g.fullPath || g.parentFolder">
                  <FolderIcon v-if="g.parentFolder" :size="15" />
                  <span v-else class="ic">🎬</span>
                  <span class="gname">{{ g.parentFolder || '未分组视频' }}</span>
                  <span class="cnt">{{ g.videos.length }} 个视频</span>
                </div>
              </td>
              <td class="col-accts" @click.stop>
                <div class="chips">
                  <span
                    v-for="acc in visibleAccountsOf(g)"
                    :key="acc.key"
                    class="acct"
                    :class="{ auto: isAutoMatchedGroup(g, acc.key) }"
                    :title="`点击移除（该文件夹下全部视频）· 覆盖 ${acc.count} 个视频`"
                    @click="removeAssignFromGroup(g.key, acc.key)"
                  >
                    <span class="av" :style="{ background: platformMeta(acc.platform).color }">
                      {{ platformMeta(acc.platform).short }}
                    </span>{{ acc.name }}
                  </span>
                  <span v-if="g.accountList.length > MAX_VISIBLE_ACCTS" class="acct more">
                    +{{ g.accountList.length - MAX_VISIBLE_ACCTS }}
                  </span>
                  <span v-if="g.accountList.length === 0" class="acct empty" @click="openGroupPicker(g.key)">
                    + 点击指定账号
                  </span>
                </div>
              </td>
              <td>
                <span v-if="g.assigned === 0" class="badge warn">待分配</span>
                <span v-else-if="g.assigned < g.videos.length" class="badge part">部分分配</span>
                <span v-else class="badge ok">已分配</span>
              </td>
              <td>
                <button class="jump-btn" @click.stop="jumpToVideosByFolder(g.key)">明细 ›</button>
              </td>
            </tr>

            <!-- 视频明细：仅当汇总层级已到「最后一层」时才列出 -->
            <tr v-for="v in (isLeafLevel ? g.videos : [])" :key="v.id" class="video-row">
              <td class="col-content">
                <div class="vid">
                  <span class="vname">{{ v.fileName }}</span>
                  <span v-if="v.childFolder" class="sub-path">{{ v.childFolder }}</span>
                  <span v-if="v.parsedEpisode" class="cp">第{{ v.parsedEpisode }}集</span>
                </div>
              </td>
              <td class="col-accts">
                <div class="chips">
                  <span
                    v-for="key in getAssigned(v.id)"
                    :key="key"
                    class="acct"
                    :class="{ auto: autoMatchedIds.includes(v.id + '|' + key) }"
                    title="点击移除"
                    @click.stop="removeAssign(v.id, key)"
                  >
                    <span class="av" :style="{ background: platformMeta(key.split(':')[0]).color }">
                      {{ platformMeta(key.split(':')[0]).short }}
                    </span>{{ getAccountName(key) }}
                  </span>
                  <span v-if="getAssigned(v.id).length === 0" class="acct empty" @click.stop="openPicker(v.id)">
                    + 指定账号
                  </span>
                </div>
              </td>
              <td>
                <span v-if="getAssigned(v.id).length === 0" class="badge warn">待分配</span>
                <span v-else class="badge ok">已分配 {{ getAssigned(v.id).length }}</span>
              </td>
              <td></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ============ 视角 2：按账号看 ============ -->
    <div v-if="rows.length > 0 && viewMode === 'account'" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width: 260px">账号</th>
            <th>负责的内容</th>
            <th style="width: 110px">合计</th>
            <th style="width: 78px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in accountRows" :key="a.key" class="acct-row">
            <td>
              <div class="acct-cell">
                <span class="av big" :style="{ background: platformMeta(a.platform).color }">
                  {{ platformMeta(a.platform).short }}
                </span>
                <div>
                  <div class="aname">{{ a.name }}</div>
                  <div class="aplat">{{ a.platform }}</div>
                </div>
              </div>
            </td>
            <td>
              <div class="src-chips">
                <span v-for="s in a.sources" :key="s.folder" class="src">{{ s.folder }} <b>{{ s.count }}</b></span>
                <span v-if="a.total === 0" class="none">未分发任何内容</span>
              </div>
            </td>
            <td><span class="total" :class="{ zero: a.total === 0 }">{{ a.total }} 个视频</span></td>
            <td>
              <button v-if="a.total > 0" class="jump-btn" @click.stop="jumpToVideosByAccount(a.key)">明细 ›</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ============ 视角 3：视频视角 ============ -->
    <div v-if="rows.length > 0 && viewMode === 'video'">
      <!-- 视频视角：跳转筛选条 -->
      <div v-if="jumpFilter" class="jump-bar">
        <span class="jump-label">仅显示：</span>
        <span class="jump-chip">
          <FolderIcon v-if="jumpFilter?.type === 'folder'" :size="12" />
          {{ jumpLabel }}
          <el-icon class="jump-close" @click="clearJumpFilter"><Close /></el-icon>
        </span>
        <span class="jump-count">共 {{ filteredRowsForVideoView.length }} 个视频</span>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>视频文件名</th>
              <th style="width: 220px">所属文件夹</th>
              <th style="width: 280px">发布账号</th>
              <th style="width: 110px">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredRowsForVideoView" :key="r.id" class="video-row">
              <td class="col-content">
                <div class="vid">
                  <span class="vname">{{ r.fileName }}</span>
                  <span v-if="r.parsedEpisode" class="cp">第{{ r.parsedEpisode }}集</span>
                </div>
              </td>
              <td>
                <div class="folder-path">
                  <span v-if="r.parentFolder" class="pf"><FolderIcon :size="12" /> {{ r.parentFolder }}</span>
                  <span v-if="r.childFolder" class="cf">/ {{ r.childFolder }}</span>
                </div>
              </td>
              <td class="col-accts">
                <div class="chips">
                  <span
                    v-for="key in getAssigned(r.id)"
                    :key="key"
                    class="acct"
                    :class="{ auto: autoMatchedIds.includes(r.id + '|' + key) }"
                    title="点击移除"
                    @click.stop="removeAssign(r.id, key)"
                  >
                    <span class="av" :style="{ background: platformMeta(key.split(':')[0]).color }">
                      {{ platformMeta(key.split(':')[0]).short }}
                    </span>{{ getAccountName(key) }}
                  </span>
                  <span v-if="getAssigned(r.id).length === 0" class="acct empty" @click.stop="openPicker(r.id)">
                    + 指定账号
                  </span>
                </div>
              </td>
              <td>
                <span v-if="getAssigned(r.id).length === 0" class="badge warn">待分配</span>
                <span v-else class="badge ok">已分配 {{ getAssigned(r.id).length }}</span>
              </td>
            </tr>
            <tr v-if="filteredRowsForVideoView.length === 0">
              <td colspan="4" class="empty-row">没有匹配的视频</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 指定账号弹窗 -->
    <el-dialog v-model="pickerVisible" title="指定发布账号" width="420px">
      <div class="picker-list">
        <div
          v-for="acc in selectedAccounts"
          :key="acc.platform + ':' + acc.account"
          class="picker-item"
          :class="{ on: pickerChecked.includes(acc.platform + ':' + acc.account) }"
          @click="togglePicker(acc.platform + ':' + acc.account)"
        >
          <span class="nm">@{{ acc.nickname || acc.account }}</span>
          <span class="plat">{{ acc.platform }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="pickerVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmPicker">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import FolderIcon from '../common/FolderIcon.vue'
import type { MediaItem, MatrixCellConfig } from '../../types/matrix'

// ============ 类型与常量 ============
/** 平台简称 + 配色（未命中时按名称哈希取色，避免硬编码中文枚举） */
const PLATFORM_META: Record<string, { short: string; color: string }> = {
  douyin: { short: '抖', color: '#000000' },      // 抖音：黑（官方 logo 主色）
  tencent: { short: '视', color: '#FA9D3B' },     // 视频号：橙
  wechat: { short: '视', color: '#FA9D3B' },
  kuaishou: { short: '快', color: '#FF4906' },    // 快手：橙红
  xiaohongshu: { short: '红', color: '#FF2442' }, // 小红书：正红
  redbook: { short: '红', color: '#FF2442' },
  bilibili: { short: 'B', color: '#FB7299' },     // 哔哩哔哩：粉
  'b站': { short: 'B', color: '#FB7299' }
}

/** 组行上最多平铺几个账号，超出折叠成 +N */
const MAX_VISIBLE_ACCTS = 3

interface GroupAccount {
  key: string
  platform: string
  name: string
  count: number
}

interface GroupRow {
  key: string
  parentFolder: string   // 当前层的分组显示名（如「第1集」）
  fullPath: string        // 完整层级路径（如「短剧A / 第1集」），用于 hover 提示
  videos: RowItem[]
  assigned: number
  accountKeys: string[]
  accountList: GroupAccount[]
  /** 由搜索过滤产生，表示组内视频被筛掉了一部分 */
  filtered?: boolean
}

interface AccountRow {
  key: string
  platform: string
  name: string
  sources: Array<{ folder: string; count: number }>
  total: number
}

interface RowItem {
  id: string
  fileName: string
  filePath: string
  parentFolder: string
  childFolder: string
  folderCrumbs: string[]
  parsedEpisode?: number
}

// ============ Props / Emit ============
const props = defineProps<{
  mediaList: MediaItem[]
  selectedAccounts: Array<{ platform: string; account: string; nickname?: string }>
  matrixMap: Record<string, Record<string, MatrixCellConfig>>
}>()

const emit = defineEmits<{
  (e: 'update:matrixMap', map: Record<string, Record<string, MatrixCellConfig>>): void
}>()

// ============ 状态 ============


const autoMatchedIds = ref<string[]>([])

type ViewMode = 'folder' | 'video' | 'account'
const viewMode = ref<ViewMode>('folder')

/**
 * 默认视角：
 * · 素材里存在子文件夹（有分组结构）→ 文件夹视角
 * · 素材全是平铺视频（无子文件夹）  → 视频视角
 */
const defaultViewMode = computed<ViewMode>(() =>
  props.mediaList.some((m) => (m.folderCrumbs || []).length > 0) ? 'folder' : 'video'
)

// 仅在「素材结构」变化时重置视角；用户手动切换视角后，只要媒体结构没变，watch 不会再触发
watch(defaultViewMode, (v) => { viewMode.value = v }, { immediate: true })

// ============ 文件夹视角：汇总层级 ============
/** 文件夹视角按第几层汇总（1 = 最外层，默认） */
const folderLevel = ref(1)

/** 素材里实际存在的最深目录层级 */
const maxFolderDepth = computed(() =>
  props.mediaList.reduce((mx, m) => Math.max(mx, (m.folderCrumbs || []).length), 0)
)

// 素材结构变化时，默认汇总到「第 2 层」：
// 层级约定为「第 1 层 = 父文件夹（拖入的根）、第 2 层 = 账号目录、第 3 层 = 内容目录」，
// 第 2 层才是常用的分组粒度（按账号把内容分下去）。
// 素材不足两层时（一层文件夹或纯平铺视频）回退到实际深度。
watch(
  maxFolderDepth,
  (depth) => {
    folderLevel.value = Math.min(2, depth)
  },
  { immediate: true }
)

/** 当前汇总层级是否已到素材的最深层（最后一层） */
const isLeafLevel = computed(
  () => maxFolderDepth.value > 0 && folderLevel.value >= maxFolderDepth.value
)

/** 按当前层级取分组 key（folderLevel === 0 时不分组，全部归为一组） */
function groupKeyOf(crumbs: string[]): string {
  if (folderLevel.value === 0) return '__all__'
  if (!crumbs || crumbs.length === 0) return '__ungrouped__'
  return crumbs.slice(0, Math.min(folderLevel.value, crumbs.length)).join(' / ')
}

/**
 * 分组显示名 = 第 N 层那一段目录名（不拼接父层）。
 * 例：crumbs = ['短剧A','第1集']、folderLevel = 2 → 显示「第1集」
 */
function groupNameOf(crumbs: string[]): string {
  if (folderLevel.value === 0) return '全部视频'
  if (!crumbs || crumbs.length === 0) return ''
  const idx = Math.min(folderLevel.value, crumbs.length) - 1
  return crumbs[idx] || ''
}

// 切换层级时清掉跳转筛选，避免 group key 变了导致过滤失效
watch(folderLevel, () => {
  jumpFilter.value = null
})

// ============ 跳转联动 ============
/** 从其他视角跳进视频视角时的筛选条件 */
const jumpFilter = ref<{ type: 'folder' | 'account'; value: string } | null>(null)

/** 视角切换（离开视频视角时清掉跳转筛选，避免下次进入被莫名过滤） */
function switchView(v: ViewMode) {
  viewMode.value = v
  if (v !== 'video') jumpFilter.value = null
}

/** 文件夹视角 → 视频视角（只看该文件夹的视频） */
function jumpToVideosByFolder(folderKey: string) {
  jumpFilter.value = { type: 'folder', value: folderKey }
  viewMode.value = 'video'
}

/** 账号视角 → 视频视角（只看该账号负责的视频） */
function jumpToVideosByAccount(accKey: string) {
  jumpFilter.value = { type: 'account', value: accKey }
  viewMode.value = 'video'
}

function clearJumpFilter() {
  jumpFilter.value = null
}

/** 跳转筛选条上显示的标签 */
const jumpLabel = computed(() => {
  const jf = jumpFilter.value
  if (!jf) return ''
  if (jf.type === 'folder') {
    const g = groups.value.find((x) => x.key === jf.value)
    return g?.parentFolder || '未分组视频'
  }
  return `@${getAccountName(jf.value)}`
})

// ============ 路径解析 ============
function parsePath(filePath: string) {
  const normalized = (filePath || '').replace(/\\/g, '/')
  const parts = normalized.split('/').filter(Boolean)
  const fileName = parts.pop() || ''
  const childFolder = parts.length >= 1 ? parts[parts.length - 1] : ''
  const parentFolder = parts.length >= 2 ? parts[parts.length - 2] : ''
  return { fileName, childFolder, parentFolder }
}

// ============ 行数据 ============
const rows = computed<RowItem[]>(() =>
  props.mediaList.map((m) => {
    const parsed = parsePath(m.filePath)
    const crumbs = m.folderCrumbs || []
    const parentFolder = crumbs.length >= 2 ? crumbs[crumbs.length - 2] : parsed.parentFolder
    const childFolder = crumbs.length >= 1 ? crumbs[crumbs.length - 1] : parsed.childFolder
    return {
      id: m.id,
      fileName: m.fileName || parsed.fileName,
      filePath: m.filePath,
      parentFolder,
      childFolder,
      folderCrumbs: crumbs.length > 0 ? crumbs : [],
      parsedEpisode: m.parsedEpisode
    }
  })
)



// ============ matrixMap 读写 ============
function getAssigned(mediaId: string): string[] {
  const cells = props.matrixMap[mediaId] || {}
  return Object.keys(cells).filter((k) => cells[k]?.enabled)
}

const assignedCount = computed(() => rows.value.filter((r) => getAssigned(r.id).length > 0).length)

function getAccountName(key: string) {
  const [plat, acc] = key.split(':')
  const found = props.selectedAccounts.find((a) => a.platform === plat && a.account === acc)
  return found?.nickname || acc
}

function defaultCell(): MatrixCellConfig {
  return {
    enabled: true,
    scheduleMode: 'inherit',
    isCustomized: false,
    override: {
      isCustomized: false,
      title: '', desc: '', tags: '', thumbnail: '', thumbnailLandscape: '', thumbnailPortrait: '',
      tid: 0, shortTitle: '', category: '', draft: false, schedule: '', declaration: '',
      collection: '', productLink: '', productTitle: '', visibility: 'public',
      playlist: '', bgm: '', note: '', notef: ''
    }
  }
}

function setAssign(mediaId: string, keys: string[]) {
  const next = { ...props.matrixMap }
  const cells: Record<string, MatrixCellConfig> = {}
  keys.forEach((k) => { cells[k] = defaultCell() })
  next[mediaId] = cells
  emit('update:matrixMap', next)
}

function removeAssign(mediaId: string, key: string) {
  const next = { ...props.matrixMap }
  const cells = { ...(next[mediaId] || {}) }
  delete cells[key]
  next[mediaId] = cells
  emit('update:matrixMap', next)
}

function clearAssign() {
  emit('update:matrixMap', {})
  autoMatchedIds.value = []
}

// 注意：已从工具栏移除入口 —— 按文件夹名匹配已并入「按顺序均分」的默认逻辑
//（精确匹配账号名，匹配不到再按顺序轮转）。保留实现以便日后需要单独入口时复用。
function autoMatchByFolder() {
  const next = { ...props.matrixMap }
  const matched: string[] = []
  rows.value.forEach((r) => {
    const folderKey = `${r.parentFolder}${r.childFolder}`.toLowerCase()
    if (!folderKey) return
    const hit = props.selectedAccounts.filter((a) => {
      const name = (a.nickname || a.account).toLowerCase()
      if (!name) return false
      return folderKey.includes(name) || name.includes(r.childFolder.toLowerCase())
    })
    if (hit.length > 0) {
      const cells = { ...(next[r.id] || {}) }
      hit.forEach((a) => {
        const key = `${a.platform}:${a.account}`
        if (!cells[key]) { cells[key] = defaultCell(); matched.push(`${r.id}|${key}`) }
      })
      next[r.id] = cells
    }
  })
  emit('update:matrixMap', next)
  autoMatchedIds.value = matched
}

// ============ 平台元信息 ============
function platformMeta(p: string) {
  const hit = PLATFORM_META[(p || '').toLowerCase()]
  if (hit) return hit
  let h = 0
  const s = p || '?'
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return { short: s.slice(0, 1), color: `hsl(${h}, 55%, 45%)` }
}

// ============ 按父文件夹聚合（行粒度 = 文件夹） ============
const groups = computed<GroupRow[]>(() => {
  const map = new Map<string, GroupRow>()

  rows.value.forEach((r) => {
    const crumbs = r.folderCrumbs || []
    const key = groupKeyOf(crumbs)
    let g = map.get(key)
    if (!g) {
      g = {
        key,
        parentFolder: groupNameOf(crumbs), // 按当前层级显示的汇总名（仅该层目录名）
        fullPath: crumbs.join(' / '),       // 完整路径，供 hover 提示
        videos: [],
        assigned: 0,
        accountKeys: [],
        accountList: []
      }
      map.set(key, g)
    }
    g.videos.push(r)
  })

  map.forEach((g) => {
    const counter = new Map<string, number>()
    g.videos.forEach((v) => {
      getAssigned(v.id).forEach((k) => counter.set(k, (counter.get(k) || 0) + 1))
    })
    g.assigned = g.videos.filter((v) => getAssigned(v.id).length > 0).length
    g.accountList = Array.from(counter.entries())
      .map(([key, count]) => {
        const [platform, account] = key.split(':')
        const found = props.selectedAccounts.find((a) => a.platform === platform && a.account === account)
        return { key, platform, name: found?.nickname || account, count }
      })
      .sort((a, b) => b.count - a.count) // 发得最多的账号排前面
    g.accountKeys = g.accountList.map((a) => a.key)
  })

  return Array.from(map.values())
})

// ============ 对应模式（默认：按顺序均分） ============
type AssignMode = 'sequential' | 'manual'
const assignMode = ref<AssignMode>('sequential')

/**
 * 构建「分配单元」：
 * · 有子文件夹 → 以父文件夹为一个单元（同系列不拆散，整组给同一个账号）
 * · 无子文件夹 → 以单个视频为一个单元
 */
function nameOfUnit(unitKey: string): string {
  if (unitKey === '__all__' || unitKey === '__ungrouped__') return ''
  const parts = unitKey.split(' / ')
  return parts[parts.length - 1] || ''
}

function buildAssignUnits(): Array<{ key: string; mediaIds: string[] }> {
  const hasFolders = groups.value.some((g) => !!g.parentFolder)
  if (!hasFolders) {
    return rows.value.map((r) => ({ key: r.id, mediaIds: [r.id] }))
  }
  return groups.value.map((g) => ({ key: g.key, mediaIds: g.videos.map((v) => v.id) }))
}

/** 分配单元数 < 账号数 时的提示（避免静默丢内容） */
/** 仅在异常（内容不足以覆盖全部账号）时给提示，正常时不占用界面空间 */
const assignHint = computed(() => {
  const unitCount = buildAssignUnits().length
  const acctCount = props.selectedAccounts.length
  if (unitCount === 0 || acctCount === 0) return ''
  if (unitCount < acctCount) {
    return `⚠ ${acctCount - unitCount} 个账号分不到内容`
  }
  return ''
})

const pendingCount = computed(() => rows.value.length - assignedCount.value)

/**
 * 按顺序均分：单元 i → 账号 (i % 账号数)
 * 只补齐「尚未分配」的视频，不覆盖用户的手动调整
 */
function applySequentialAssign() {
  const accounts = props.selectedAccounts
  if (accounts.length === 0 || rows.value.length === 0) return

  const next = { ...props.matrixMap }
  let changed = 0

  buildAssignUnits().forEach((unit, i) => {
    // 优先按文件夹名精确匹配账号；匹配不到再回退到按顺序轮转
    const unitName = nameOfUnit(unit.key)
    const byName = accounts.find((a) => {
      const n = String(a.nickname || a.account || '').trim().toLowerCase()
      return n !== '' && n === unitName.trim().toLowerCase()
    })
    const acc = byName || accounts[i % accounts.length]
    const accKey = `${acc.platform}:${acc.account}`
    unit.mediaIds.forEach((id) => {
      if (next[id] && Object.keys(next[id]).length > 0) return // 已有分配 → 跳过
      next[id] = { ...(next[id] || {}), [accKey]: defaultCell() }
      changed += 1
    })
  })

  if (changed > 0) emit('update:matrixMap', next)
}

// ---- 撤销快照 ----
const assignSnapshot = ref<Record<string, Record<string, MatrixCellConfig>> | null>(null)

/** 覆盖式重新应用（用户主动点击时使用，会重算全部） */
async function reapplyAssign() {
  const accounts = props.selectedAccounts
  if (accounts.length === 0) return

  // 重新应用会按「当前汇总层级」重算分配，层级切错会导致分配全变，先确认
  const unitCount = buildAssignUnits().length
  try {
    await ElMessageBox.confirm(
      `将按当前层级（${folderLevel.value === 0 ? '不分组' : `第 ${folderLevel.value} 层`} · ${unitCount} 个分组）重新分配，覆盖现有对应关系。`,
      '确认重新应用均分？',
      { type: 'warning', confirmButtonText: '重新分配', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户取消
  }

  assignSnapshot.value = JSON.parse(JSON.stringify(props.matrixMap))

  const next: Record<string, Record<string, MatrixCellConfig>> = {}
  buildAssignUnits().forEach((unit, i) => {
    // 优先按文件夹名精确匹配账号；匹配不到再回退到按顺序轮转
    const unitName = nameOfUnit(unit.key)
    const byName = accounts.find((a) => {
      const n = String(a.nickname || a.account || '').trim().toLowerCase()
      return n !== '' && n === unitName.trim().toLowerCase()
    })
    const acc = byName || accounts[i % accounts.length]
    const accKey = `${acc.platform}:${acc.account}`
    unit.mediaIds.forEach((id) => {
      next[id] = { [accKey]: defaultCell() }
    })
  })

  emit('update:matrixMap', next)

  const count = Object.keys(next).length
  ElMessage({
    type: 'success',
    duration: 5000,
    message: h('span', { style: 'display:inline-flex;align-items:center;gap:8px' }, [
      h('span', null, `已按顺序均分生成 ${count} 条对应关系`),
      h(
        'a',
        {
          style: 'color: var(--primary-color); cursor: pointer; font-weight: 600',
          onClick: () => undoAssign()
        },
        '撤销'
      )
    ])
  })

  // 5 秒后快照失效（撤销入口随之消失）
  window.setTimeout(() => { assignSnapshot.value = null }, 5000)
}

function undoAssign() {
  if (!assignSnapshot.value) return
  emit('update:matrixMap', assignSnapshot.value)
  assignSnapshot.value = null
  ElMessage.success('已撤销上一次分配')
}

// ---- 自动执行：出现「未分配的视频」时按默认模式补齐 ----
watch(
  [() => rows.value.length, () => props.selectedAccounts.length, assignMode],
  () => {
    if (assignMode.value !== 'sequential') return
    applySequentialAssign()
  },
  { immediate: true }
)

// 搜索功能已下线；保留该 computed 以兼容模板引用
const filteredGroups = computed<GroupRow[]>(() => groups.value)

/** 视频视角的行数据：先叠加跳转筛选（文件夹 / 账号） */
const filteredRowsForVideoView = computed(() => {
  let list = rows.value

  // 跳转筛选（从文件夹/账号视角进来时）
  const jf = jumpFilter.value
  if (jf?.type === 'folder') {
    const g = groups.value.find((x) => x.key === jf.value)
    const ids = new Set(g ? g.videos.map((v) => v.id) : [])
    list = list.filter((r) => ids.has(r.id))
  } else if (jf?.type === 'account') {
    list = list.filter((r) => getAssigned(r.id).includes(jf.value))
  }

  return list
})

const groupCount = computed(() => groups.value.length)

const coveredAccountCount = computed(() => {
  const set = new Set<string>()
  rows.value.forEach((r) => getAssigned(r.id).forEach((k) => set.add(k)))
  return set.size
})

/** 组行上平铺展示的账号（超出部分折叠） */
function visibleAccountsOf(g: GroupRow) {
  return g.accountList.slice(0, MAX_VISIBLE_ACCTS)
}

/** 组内某账号是否来自"自动匹配" */
function isAutoMatchedGroup(g: GroupRow, accKey: string) {
  return g.videos.every((v) => autoMatchedIds.value.includes(v.id + '|' + accKey))
}

// ============ 按账号视角 ============
const accountRows = computed<AccountRow[]>(() => {
  return props.selectedAccounts
    .map((a) => {
      const key = `${a.platform}:${a.account}`
      const hit = rows.value.filter((r) => getAssigned(r.id).includes(key))
      const m = new Map<string, number>()
      hit.forEach((r) => {
        const f = r.parentFolder || '未分组'
        m.set(f, (m.get(f) || 0) + 1)
      })
      return {
        key,
        platform: a.platform,
        name: a.nickname || a.account,
        sources: Array.from(m.entries()).map(([folder, count]) => ({ folder, count })),
        total: hit.length
      }
    })
    .sort((a, b) => b.total - a.total)
})

// ============ 组级批量操作 ============
/** 批量写入分配（组级操作：一次 emit，避免逐条触发） */
function setAssignBatch(mediaIds: string[], keys: string[]) {
  const next = { ...props.matrixMap }
  mediaIds.forEach((id) => {
    const cells: Record<string, MatrixCellConfig> = {}
    keys.forEach((k) => { cells[k] = defaultCell() })
    next[id] = cells
  })
  emit('update:matrixMap', next)
}

/** 从整组移除某账号 */
function removeAssignFromGroup(groupKey: string, accKey: string) {
  const g = groups.value.find((x) => x.key === groupKey)
  if (!g) return
  const next = { ...props.matrixMap }
  g.videos.forEach((v) => {
    const cells = { ...(next[v.id] || {}) }
    delete cells[accKey]
    next[v.id] = cells
  })
  emit('update:matrixMap', next)
  autoMatchedIds.value = autoMatchedIds.value.filter((k) => !k.endsWith('|' + accKey))
}

// ============ 账号选择器 ============
const pickerVisible = ref(false)
const pickerTargetIds = ref<string[]>([])
const pickerChecked = ref<string[]>([])

function openPicker(mediaId: string) {
  pickerTargetIds.value = [mediaId]
  pickerChecked.value = getAssigned(mediaId)
  pickerVisible.value = true
}

/** 整组指定：初始勾选 = 组内视频都拥有的账号（交集） */
function openGroupPicker(groupKey: string) {
  const g = groups.value.find((x) => x.key === groupKey)
  if (!g) return
  pickerTargetIds.value = g.videos.map((v) => v.id)
  const lists = g.videos.map((v) => getAssigned(v.id))
  pickerChecked.value = lists.length === 0
    ? []
    : lists[0].filter((k) => lists.every((l) => l.includes(k)))
  pickerVisible.value = true
}

function togglePicker(key: string) {
  const i = pickerChecked.value.indexOf(key)
  if (i >= 0) pickerChecked.value.splice(i, 1)
  else pickerChecked.value.push(key)
}

function confirmPicker() {
  setAssignBatch(pickerTargetIds.value, [...pickerChecked.value])
  pickerVisible.value = false
}
</script>

<style scoped>
.content-account-table {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

/* 统计行 */
.summary-row {
  display: flex;
  align-items: center;
  padding: 4px 2px 0;
  margin-bottom: 6px;
}
.summary {
  font-size: 12px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.summary b { color: var(--text-main); font-weight: 600; }
.summary .is-warn { color: var(--status-warning, #f5a623); font-weight: 600; }
.summary-note { margin-left: 6px; font-size: 11.5px; color: var(--status-warning, #f5a623); }

/* 分配设置卡片 */
.assign-card {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 10px 14px;
  margin-bottom: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
}
.assign-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.assign-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}
.assign-sub {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.assign-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}
.assign-hint {
  font-size: 11.5px;
  color: var(--status-warning, #f5a623);
  white-space: nowrap;
}

/* 搜索框收窄，不再撑满 */


.is-active-mode { color: var(--primary-color); font-weight: 600; }

.tb-btn { font-size: 12px; padding: 5px 12px; border-radius: 7px; cursor: pointer; border: 1px solid var(--border-subtle); background: var(--bg-input); color: var(--text-main); }
.tb-btn:hover { border-color: var(--primary-color); }
.tb-btn.ghost { background: transparent; }
.tb-select { font-size: 12px; padding: 5px 10px; border-radius: 7px; border: 1px solid var(--border-subtle); background: var(--bg-input); color: var(--text-main); outline: none; }
.hint { font-size: 12px; color: var(--text-muted); }

.table-wrap {
  margin-top: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  overflow: auto;
  flex: 1;
  min-height: 240px;
}
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { position: sticky; top: 0; background: var(--bg-detail); padding: 9px 12px; text-align: left; font-weight: 600; border-bottom: 1px solid var(--border-subtle); white-space: nowrap; z-index: 2; color: var(--text-main); }
td { padding: 9px 12px; border-bottom: 1px solid var(--border-subtle); vertical-align: middle; }
tbody tr:hover td { background: rgba(99, 102, 241, 0.06); }
/* 分区标题行不参与 hover 高亮，保持稳定的浅色背景 */
tbody tr.group-row:hover td { background: rgba(99, 102, 241, 0.07); }

.folder { font-weight: 600; display: flex; align-items: center; gap: 7px; color: var(--text-main); }
.folder.child { font-weight: 500; }
.ic { font-size: 13px; }
.merged { color: transparent; }
.vid { display: flex; align-items: center; gap: 7px; color: var(--text-secondary); }
.cp { font-size: 10px; color: var(--text-muted); background: var(--bg-input); padding: 1px 6px; border-radius: 8px; }
.sub-path { font-size: 10px; color: var(--text-muted); background: var(--bg-input); padding: 1px 6px; border-radius: 8px; }

.acct { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; padding: 3px 9px; border-radius: 12px; border: 1px solid var(--border-subtle); background: var(--bg-input); margin-right: 5px; cursor: pointer; color: var(--text-main); }
.acct .d { width: 5px; height: 5px; border-radius: 50%; background: var(--status-success); }
.acct.auto { border-color: rgba(99, 102, 241, 0.5); color: var(--primary-color); background: rgba(99, 102, 241, 0.1); }
.acct.empty { border-style: dashed; color: var(--text-muted); }
.acct.empty:hover { border-color: var(--primary-color); color: var(--primary-color); }

.picker-list { display: flex; flex-direction: column; gap: 7px; }
.picker-item { display: flex; justify-content: space-between; padding: 9px 12px; border: 1px solid var(--border-subtle); border-radius: 8px; cursor: pointer; font-size: 13px; }
.picker-item.on { border-color: var(--primary-color); background: rgba(99, 102, 241, 0.1); }
.picker-item .plat { font-size: 11px; color: var(--text-muted); }

/* 视角 Tab（表格上方，与左侧步骤 Tab 区分：下划线样式） */
.view-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 10px;
}
.view-tab {
  position: relative;
  padding: 9px 16px;
  font-size: 13px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color .15s;
}
.view-tab:hover { color: var(--text-main); }
.view-tab.on { color: var(--primary-color); font-weight: 600; }
.view-tab.on::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -1px;
  height: 2px;
  background: var(--primary-color);
  border-radius: 2px;
}

/* 跳转筛选条 */
.jump-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 8px;
  font-size: 12px;
}

/* 跳转筛选条 */
.jump-label { color: var(--text-muted); }
.jump-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  font-weight: 500;
}
.jump-close { cursor: pointer; font-size: 12px; color: var(--text-muted); }
.jump-close:hover { color: var(--status-danger, #ef4444); }
.jump-count { margin-left: auto; color: var(--text-muted); }

/* 明细跳转按钮 */
.jump-btn {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  transition: all .15s;
}
.jump-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* 视频视角：文件夹路径 */
.folder-path { font-size: 12px; color: var(--text-muted); }
.folder-path .pf { color: var(--text-main); font-weight: 500; }
.folder-path .cf { color: var(--text-muted); }

.empty-row {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

/* ===== 文件夹分区标题行 ===== */
/* 标题行不再可点击（点击会触发表内 hover 高亮导致整片变蓝） */
.group-row { cursor: default; }
.group-row td {
  background: rgba(99, 102, 241, 0.07);
  border-top: 1px solid var(--border-subtle);
}
.group-row .folder { font-weight: 600; }
.group-row .gname { color: var(--text-main); }
.group-row .cnt { font-size: 11px; color: var(--text-muted); font-weight: 400; }
.group-row.no-assign { background: rgba(245, 166, 35, 0.06); }

/* ===== 视频明细行 ===== */
.video-row .col-content { padding-left: 34px; }
.video-row .vname { color: var(--text-secondary); }
.video-row td { background: rgba(0, 0, 0, 0.12); }

/* ===== 账号 chip ===== */
.chips { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.acct .av { width: 15px; height: 15px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  font-size: 9px; color: #fff; font-weight: 600; margin-right: 4px; flex: 0 0 auto;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22); /* 深色主题：保证抖音黑色头像有可见轮廓 */
}
.acct.more { border-style: dashed; color: var(--text-muted); background: transparent; cursor: default; }
.acct.more:hover { border-color: var(--border-subtle); }
.acct .d { display: none; }

/* ===== 状态徽标 ===== */
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.badge.ok { color: var(--status-success); background: rgba(52, 211, 153, 0.12); }
.badge.warn { color: var(--status-warning, #f5a623); background: rgba(245, 166, 35, 0.14); }
.badge.part { color: var(--primary-color); background: rgba(99, 102, 241, 0.12); }

/* ===== 按账号看 ===== */
.acct-cell { display: flex; align-items: center; gap: 9px; }
.av.big { width: 24px; height: 24px; font-size: 11px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-weight: 600;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22); /* 深色主题：保证抖音黑色头像有可见轮廓 */
}
.acct-cell .aname { font-weight: 500; color: var(--text-main); }
.acct-cell .aplat { font-size: 11px; color: var(--text-muted); }
.src-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.src { font-size: 11px; padding: 2px 9px; border-radius: 10px; background: var(--bg-input); border: 1px solid var(--border-subtle); color: var(--text-secondary); }
.src b { color: var(--text-main); font-weight: 600; margin-left: 3px; }
.total { font-size: 12px; color: var(--text-main); font-weight: 600; }
.total.zero { color: var(--text-muted); font-weight: 400; }
.none { font-size: 11px; color: var(--status-warning, #f5a623); }
</style>
