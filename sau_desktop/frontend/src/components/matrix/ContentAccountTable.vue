<template>
  <div class="content-account-table">
    <!-- 1. 分配设置（先配置，再查看） -->
    <!-- 分配单位由上传区的层级选择器控制（unitLevel），此处只显示说明 -->
    <div v-if="rows.length > 0" class="views-panel">

      <!-- 说明行：单位说明 + 异常提示 + 重置入口 -->
      <div class="unit-desc">
        <span class="unit-desc-text">
          <template v-if="isFolderMode">
            <span class="level-badge">第{{ unitLevel }}层目录</span>
            文件夹里的内容整体发给同一个账号
          </template>
          <template v-else>
            每条视频单独分配账号，按列表顺序轮流对应
          </template>
        </span>

        <span v-if="selectedAccounts.length === 0" class="assign-hint">
          尚未选择账号 —— 请在「② 选择账号」中勾选
        </span>
        <span v-else-if="assignHint" class="assign-hint">{{ assignHint }}</span>

        <button class="reset-btn" @click="applyLoopAssign">循环分配</button>
      </div>

      <!-- 内容表始终显示（无账号时账号列为空，便于先核对内容组与序号） -->
      <!-- 文件夹分组视图（unitLevel > 0 时显示） -->
      <div v-if="isFolderMode" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width: 44px">#</th>
              <th>内容</th>
              <th style="width: 300px">发布账号</th>
              <th style="width: 92px">状态</th>
            </tr>
          </thead>
        <tbody>
          <tr v-for="g in filteredGroups" :key="g.key" class="group-row" :class="{ 'no-assign': g.assigned === 0 }">
            <td class="col-order">
              <span class="order-badge">{{ groupOrder(g.key) }}</span>
            </td>
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
                    v-for="{ acc, order } in visibleAccountsOfWithIndex(g)"
                    :key="acc.key"
                    class="acct"
                    :class="{ auto: isAutoMatchedGroup(g, acc.key) }"
                    :title="`点击移除（该文件夹下全部视频）· 覆盖 ${acc.count} 个视频`"
                    @click="removeAssignFromGroup(g.key, acc.key)"
                  >
                    <span class="av" :style="{ background: platformMeta(acc.platform).color }">
                      {{ platformMeta(acc.platform).short }}
                    </span>
                    <span class="chip-order">{{ order }}</span>{{ acc.name }}
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
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 视频列表视图（unitLevel === 0 时显示） -->
    <div v-if="!isFolderMode">
      <!-- 视频为单位：跳转筛选条 -->
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
              <th style="width: 44px">#</th>
              <th>视频文件名</th>
              <th style="width: 220px">所属文件夹</th>
              <th style="width: 280px">发布账号</th>
              <th style="width: 110px">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredRowsForVideoView" :key="r.id" class="video-row">
              <td class="col-order">
                <span class="order-badge">{{ videoOrder(r.id) }}</span>
              </td>
              <td class="col-content">
                <div class="vid">
                  <span class="vname">{{ r.fileName }}</span>
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
              <td colspan="5" class="empty-row">没有匹配的视频</td>
            </tr>
          </tbody>
        </table>
      </div><!-- /.table-wrap -->
    </div><!-- /video section -->

    </div><!-- /views-panel -->

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
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
  bilibili: { short: 'B', color: '#FB7299' },     // B站：粉
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
  /** 分配/汇总的单位层级，由上传区设定 */
  unitLevel: number
}>()

const emit = defineEmits<{
  (e: 'update:matrixMap', map: Record<string, Record<string, MatrixCellConfig>>): void
}>()

// ============ 状态 ============

const autoMatchedIds = ref<string[]>([])

/** 是否按文件夹（组）展示：unitLevel > 0 时按组，= 0 时按视频 */
const isFolderMode = computed(() => props.unitLevel > 0)

// ============ 文件夹分组：层级控制 ============
/** 素材里实际存在的最深目录层级 */
const maxFolderDepth = computed(() =>
  props.mediaList.reduce((mx, m) => Math.max(mx, (m.folderCrumbs || []).length), 0)
)

// 切换层级时清掉跳转筛选，避免 group key 变了导致过滤失效
watch(() => props.unitLevel, () => {
  jumpFilter.value = null
})

/** 按当前层级取分组 key（unitLevel === 0 时不分组，全部归为一组） */
function groupKeyOf(crumbs: string[]): string {
  if (props.unitLevel === 0) return '__all__'
  if (!crumbs || crumbs.length === 0) return '__ungrouped__'
  return crumbs.slice(0, Math.min(props.unitLevel, crumbs.length)).join(' / ')
}

/**
 * 分组显示名 = 第 N 层那一段目录名（不拼接父层）。
 * 例：crumbs = ['短剧A','第1集']、unitLevel = 2 → 显示「第1集」
 */
function groupNameOf(crumbs: string[]): string {
  if (props.unitLevel === 0) return '全部视频'
  if (!crumbs || crumbs.length === 0) return ''
  const idx = Math.min(props.unitLevel, crumbs.length) - 1
  return crumbs[idx] || ''
}

// ============ 跳转联动 ============
/** 从文件夹为单位跳进视频为单位时的筛选条件 */
const jumpFilter = ref<{ type: 'folder'; value: string } | null>(null)

/** 从文件夹分组跳进视频列表（只看该组的视频）—— 仅用于筛选，不切视图 */
function jumpToVideosByFolder(folderKey: string) {
  jumpFilter.value = { type: 'folder', value: folderKey }
}

function clearJumpFilter() {
  jumpFilter.value = null
}

/** 跳转筛选条上显示的标签 */
const jumpLabel = computed(() => {
  const jf = jumpFilter.value
  if (!jf) return ''
  const g = groups.value.find((x) => x.key === jf.value)
  return g?.parentFolder || '未分组视频'
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

  // 与上传视频区的文件夹排序保持一致（数字感知的本地化排序），
  // 否则左侧预览的序号与这里的分组行序会对不上
  return Array.from(map.values()).sort((a, b) =>
    (a.fullPath || '').localeCompare(b.fullPath || '', 'zh', { numeric: true })
  )
})

/**
 * 分配单元跟随当前选择的分配单位：
 * · 文件夹为单位 → 以「当前汇总层级的文件夹」为一个单元（整组给同一个账号）
 * · 视频为单位   → 以「单个视频」为一个单元
 */
function nameOfUnit(unitKey: string): string {
  if (unitKey === '__all__' || unitKey === '__ungrouped__') return ''
  const parts = unitKey.split(' / ')
  return parts[parts.length - 1] || ''
}

function buildAssignUnits(): Array<{ key: string; mediaIds: string[] }> {
  if (!isFolderMode.value) {
    // 每条视频为单位：不分组
    return rows.value.map((r) => ({ key: r.id, mediaIds: [r.id] }))
  }
  // 按第 unitLevel 层的文件夹分组
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
 * 默认分配（一对一）：按当前分配单位的顺序，第 i 组配给第 i 个账号；
 * 内容组数多于账号数时，多出来的先留空，由用户点「循环分配」补全。
 * 只补齐「尚未分配」的视频，不覆盖用户的手动调整。
 */
function applySequentialAssign() {
  const accounts = props.selectedAccounts
  if (accounts.length === 0 || rows.value.length === 0) return

  const next = { ...props.matrixMap }
  let changed = 0

  buildAssignUnits().forEach((unit, i) => {
    // 优先按文件夹名精确匹配账号
    const unitName = nameOfUnit(unit.key)
    const byName = accounts.find((a) => {
      const n = String(a.nickname || a.account || '').trim().toLowerCase()
      return n !== '' && n === unitName.trim().toLowerCase()
    })

    // 默认「一对一」：名字匹配不上、且序号已超出账号数量的单元，先留空不分配。
    // 想补全剩余内容 → 用户点「循环分配」。
    if (!byName && i >= accounts.length) return

    const acc = byName || accounts[i]
    const accKey = `${acc.platform}:${acc.account}`
    unit.mediaIds.forEach((id) => {
      if (next[id] && Object.keys(next[id]).length > 0) return // 已有分配 → 跳过
      next[id] = { ...(next[id] || {}), [accKey]: defaultCell() }
      changed += 1
    })
  })

  if (changed > 0) emit('update:matrixMap', next)
}

/**
 * 循环分配：把尚未分配的内容，按账号顺序循环补上（不覆盖已有分配）。
 * 与「默认一对一」的区别是这里用 i % accounts.length，内容会重复落到账号上。
 */
function applyLoopAssign() {
  const accounts = props.selectedAccounts
  if (accounts.length === 0 || rows.value.length === 0) return

  const next = { ...props.matrixMap }
  let changed = 0

  buildAssignUnits().forEach((unit, i) => {
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

  if (changed > 0) {
    emit('update:matrixMap', next)
    ElMessage.success(`已循环补全 ${changed} 条内容的分配`)
  } else {
    ElMessage.info('所有内容都已分配，无需补全')
  }
}

// ---- 自动执行：出现「未分配的视频」时按默认模式补齐 ----
watch(
  [() => rows.value.length, () => props.selectedAccounts.length],
  () => {
    applySequentialAssign()
  },
  { immediate: true }
)

/**
 * 取分组的内容序号。
 * 必须基于 groups（全量）而非 filteredGroups —— 否则切换"只看未分配"等筛选后，
 * 序号会跟着变，与左侧预览的序号就对不上了。
 */
function groupOrder(key: string): number {
  return groups.value.findIndex((g) => g.key === key) + 1
}

/** 取视频的全局序号（视频视角用，与上传视频区的顺序一致） */
function videoOrder(id: string): number {
  return rows.value.findIndex((r) => r.id === id) + 1
}

/** 取账号序号（与"选择账号"里的选择顺序一致） */
function accountOrder(key: string): number {
  const idx = props.selectedAccounts.findIndex((a) => `${a.platform}:${a.account}` === key)
  return idx >= 0 ? idx + 1 : 0
}

// 搜索功能已下线；保留该 computed 以兼容模板引用
const filteredGroups = computed<GroupRow[]>(() => groups.value)

/** 视频为单位的行数据：先叠加跳转筛选（仅文件夹来源） */
const filteredRowsForVideoView = computed(() => {
  let list = rows.value

  // 跳转筛选（从文件夹为单位进来时）
  const jf = jumpFilter.value
  if (jf?.type === 'folder') {
    const g = groups.value.find((x) => x.key === jf.value)
    const ids = new Set(g ? g.videos.map((v) => v.id) : [])
    list = list.filter((r) => ids.has(r.id))
  }

  return list
})

const groupCount = computed(() => groups.value.length)

const coveredAccountCount = computed(() => {
  const set = new Set<string>()
  rows.value.forEach((r) => getAssigned(r.id).forEach((k) => set.add(k)))
  return set.size
})

/** 组行上平铺展示的账号（超出部分折叠）；顺序与 selectedAccounts 一致，序号才能对上） */
function visibleAccountsOf(g: GroupRow) {
  const groupKeys = new Set(g.accountKeys)
  return props.selectedAccounts
    .map((a) => `${a.platform}:${a.account}`)
    .filter((key) => groupKeys.has(key))
    .map((key) => g.accountList.find((a) => a.key === key)!)
    .filter(Boolean)
    .slice(0, MAX_VISIBLE_ACCTS)
}

/** 同上，返回原始 index（用于渲染账号序号） */
function visibleAccountsOfWithIndex(g: GroupRow): Array<{ acc: GroupAccount; order: number }> {
  const groupKeys = new Set(g.accountKeys)
  return props.selectedAccounts
    .map((a, i) => ({ key: `${a.platform}:${a.account}`, order: i + 1 }))
    .filter(({ key }) => groupKeys.has(key))
    .map(({ key, order }) => ({ acc: g.accountList.find((a) => a.key === key)!, order }))
    .filter(({ acc }) => acc != null)
    .slice(0, MAX_VISIBLE_ACCTS)
}

/** 组内某账号是否来自"自动匹配" */
function isAutoMatchedGroup(g: GroupRow, accKey: string) {
  return g.videos.every((v) => autoMatchedIds.value.includes(v.id + '|' + accKey))
}

// ============ 按账号视角 ============
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

/* 搜索框收窄，不再撑满 */


.is-active-mode { color: var(--primary-color); font-weight: 600; }

.tb-btn { font-size: 12px; padding: 5px 12px; border-radius: 7px; cursor: pointer; border: 1px solid var(--border-subtle); background: var(--bg-input); color: var(--text-main); }
.tb-btn:hover { border-color: var(--primary-color); }
.tb-btn.ghost { background: transparent; }
.tb-select { font-size: 12px; padding: 5px 10px; border-radius: 7px; border: 1px solid var(--border-subtle); background: var(--bg-input); color: var(--text-main); outline: none; }
.hint { font-size: 12px; color: var(--text-muted); }

.table-wrap {
  flex: 1;
  min-height: 240px;
  overflow: auto;
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

/* 视角面板：页签 + 内容（同一外框） */
.views-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  overflow: hidden;
}

.unit-desc {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-muted);
  background: var(--bg-input);
  border-bottom: 1px solid var(--border-subtle);
}

.unit-desc-text {
  flex: 1;
  min-width: 0;
}

.reset-btn {
  flex-shrink: 0;
  font-size: 11.5px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.reset-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.level-badge {
  display: inline-block;
  padding: 0 6px;
  margin-right: 4px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 17px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  vertical-align: 1px;
}

/* 视角 Tab（页签贴合容器底边，视觉与内容区为一体） */
.view-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 6px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-input);
  flex-shrink: 0;
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
  border-radius: 2px 2px 0 0;
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

/* 视频为单位：文件夹路径 */
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

/* ===== 序号列 ===== */
/* 内容组/视频序号：与上传视频区的 .order-badge 保持同一套视觉 */
.order-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
}

.col-order {
  text-align: center;
  vertical-align: middle;
}

  /* 迷你序号：配色与 .order-badge 完全一致，仅尺寸小一号（嵌在账号 chip 内） */
.chip-order {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  margin-right: 4px;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
}
</style>
