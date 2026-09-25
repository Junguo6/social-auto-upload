<template>
  <div class="account-card-picker glass-card">
    <div class="card-header">
      <div class="card-title-box">
        <div class="title-text-group">
          <div class="main-title">
            <span>要发到哪些账号</span>
            <span class="req-star">*</span>
          </div>
        </div>
      </div>

      <div class="header-actions">
        <el-button size="small" link type="primary" @click="selectAllValid">
          <el-icon><Check /></el-icon> 全选有效账号
        </el-button>
        <!-- 仅在已选账号时显示：无选中时清空无意义，也避免误点 -->
        <el-button
          v-if="selectedKeys.length > 0"
          size="small"
          link
          type="danger"
          @click="clearSelection"
        >
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </div>

    <!-- 已选统计（单独一行，不再和分组混在一起） -->
    <div class="picker-status" v-if="selectedKeys.length > 0">
      <span class="badge-count" :class="{ 'badge-warn': authStore.isTrialAccountLimitExceeded(selectedKeys.length) }">
        已选 {{ selectedKeys.length }} 个账号 · 覆盖 {{ activePlatformCount }} 个平台
        <span v-if="authStore.isTrialAccountLimitExceeded(selectedKeys.length)" class="trial-limit-hint">
          （试用版上限 {{ authStore.TRIAL_ACCOUNT_LIMIT }} 个）
        </span>
        <span class="hint-clear">（点「清空」可重新选择，对应表会重新分配）</span>
        <span v-if="pickedGroups.length > 0" class="picked-group-hint">
          （已按 {{ pickedGroups.length }} 个分组批量选中）
        </span>
      </span>
    </div>

    <!-- 左右两栏 -->
    <div class="picker-body">
      <!-- 左：分组 -->
      <div class="picker-side">
        <div class="side-title">
          分组
          <span class="side-hint">点整行 = 选整组</span>
        </div>

        <div class="group-folder-list" v-if="accountStore.groups.length > 0">
          <div
            v-for="grp in accountStore.groups"
            :key="grp"
            class="pick-folder"
            :class="{ all: isGroupFullyPicked(grp) }"
          >
            <div class="pf-head" @click="toggleGroupPick(grp)">
              <span class="pf-check" :class="{ on: isGroupFullyPicked(grp), partial: isGroupPartiallyPicked(grp) }">
                <el-icon v-if="isGroupFullyPicked(grp)"><Check /></el-icon>
                <span v-else-if="isGroupPartiallyPicked(grp)" class="pf-dash">—</span>
              </span>

              <FolderIcon :size="16" />
              <span class="pf-name">{{ grp }}</span>
              <span class="pf-count">{{ pickedCountIn(grp) }}/{{ groupKeys(grp).length }}</span>

              <span class="pf-arrow" :class="{ open: expandedGroups.includes(grp) }" @click.stop="toggleGroupExpand(grp)">
                <el-icon><ArrowRight /></el-icon>
              </span>
            </div>

            <!-- 展开成员 -->
            <div class="pf-members" v-if="expandedGroups.includes(grp)">
              <div
                v-for="m in groupMembers(grp)"
                :key="`${m.platform}:${m.account}`"
                class="pf-member"
                :class="{ on: isSelected(m) }"
                @click="toggleAccount(m)"
              >
                <span class="pfm-plat">{{ getPlatformName(m.platform) }}</span>
                <span class="pfm-nick">{{ m.nickname || m.account }}</span>
                <span class="pfm-status" :class="m.isValid ? 'ok' : (m.checked ? 'bad' : '')">
                  {{ m.isValid ? '✅' : (m.checked ? '⚠️' : '') }}
                </span>
              </div>
              <div class="pfm-empty" v-if="groupMembers(grp).length === 0">该分组暂无账号</div>
            </div>
          </div>
        </div>

        <div class="side-empty" v-else>
          <FolderIcon :size="26" />
          <span>还没有分组</span>
          <span class="se-sub">可在「账号管理」里创建</span>
        </div>
      </div>

      <!-- 右：账号 -->
      <div class="picker-main">
        <el-input
          v-model="accountSearch"
          placeholder="搜索账号昵称/平台..."
          size="small"
          clearable
          prefix-icon="Search"
          class="search-box"
        />

        <div v-if="filteredAccounts.length > 0" class="account-grid">
          <div
            v-for="acc in filteredAccounts"
            :key="`${acc.platform}:${acc.account}`"
            class="account-item-card"
            :class="{
              selected: isSelected(acc),
              invalid: !acc.isValid
            }"
            @click="toggleAccount(acc)"
          >
            <!-- 平台色彩图标 -->
            <div class="platform-avatar" :style="{ background: getPlatformColor(acc.platform) }">
              <span>{{ getPlatformShort(acc.platform) }}</span>
            </div>

            <!-- 账号信息 -->
            <div class="account-info">
              <div class="account-name" :title="acc.nickname || acc.account">
                {{ acc.nickname || acc.account }}
              </div>
              <!-- 所属分组标签（点标签也能快速切分组） -->
              <div class="acc-tags" v-if="acc.groups && acc.groups.length">
                <span v-for="g in acc.groups" :key="g" class="acc-tag" @click.stop="toggleGroupPick(g)">
                  #{{ g }}
                </span>
              </div>
              <div class="account-meta">
                <span class="status-dot" :class="{ online: acc.isValid }"></span>
                <span class="status-text" v-if="!acc.isValid">已失效</span>
              </div>
            </div>

            <!-- 选中角标：显示分配顺序序号；点击可把该账号提到最前 -->
            <div
              class="select-indicator"
              :class="{
                active: isSelected(acc),
                adjustable: isSelected(acc) && accountOrder(acc) > 1
              }"
              :title="isSelected(acc) && accountOrder(acc) > 1 ? '点击提到最前（调整分配顺序）' : ''"
              @click.stop="promoteAccount(acc)"
            >
              <span v-if="isSelected(acc)" class="order-num">{{ accountOrder(acc) }}</span>
            </div>
          </div>
        </div>

        <!-- 无账号空状态 -->
        <div v-else-if="accountStore.accounts.length === 0" class="empty-account-box">
          <div class="empty-text">当前尚未接入任何发布账号</div>
          <router-link to="/accounts">
            <el-button type="primary" class="gradient-btn-sm" style="margin-top: 10px;">
              <el-icon><Plus /></el-icon> 前往账号管理添加
            </el-button>
          </router-link>
        </div>

        <!-- 搜索无结果 -->
        <div v-else class="search-empty">
          <span>当前分组或搜索条件下未找到匹配的账号</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAccountStore } from '../../stores/accountStore'
import { useAuthStore } from '../../stores/authStore'
import { PLATFORMS, getPlatformConfig } from '../../config/platforms'
import type { SelectedTargetAccount } from '../../types/matrix'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import FolderIcon from '../common/FolderIcon.vue'
import { Check, ArrowRight, Plus, Delete } from '@element-plus/icons-vue'

const props = defineProps<{
  selectedKeys: string[] // 格式: "platform:account"
}>()

const emit = defineEmits<{
  (e: 'update:selectedKeys', keys: string[]): void
}>()

const accountStore = useAccountStore()
const authStore = useAuthStore()
const accountSearch = ref('')

/* ───────── 分组一键选中 ───────── */
const pickedGroups = ref<string[]>([])
const expandedGroups = ref<string[]>([])

/** 某分组内全部账号的 key */
function groupKeys(grp: string): string[] {
  return accountStore.accounts
    .filter(a => a.groups?.includes(grp))
    .map(a => `${a.platform}:${a.account}`)
}

/** 某分组内的账号对象 */
function groupMembers(grp: string) {
  return accountStore.accounts.filter(a => a.groups?.includes(grp))
}

/** 该组已选中的数量 */
function pickedCountIn(grp: string): number {
  return groupKeys(grp).filter(k => props.selectedKeys.includes(k)).length
}

/** 该组是否全选 */
function isGroupFullyPicked(grp: string): boolean {
  const keys = groupKeys(grp)
  return keys.length > 0 && keys.every(k => props.selectedKeys.includes(k))
}

/** 该组是否部分选中 */
function isGroupPartiallyPicked(grp: string): boolean {
  const n = pickedCountIn(grp)
  return n > 0 && n < groupKeys(grp).length
}

/** 点分组整行 → 选中/取消整组（自动去重） */
function toggleGroupPick(grp: string) {
  const idx = pickedGroups.value.indexOf(grp)
  const keys = groupKeys(grp)

  if (idx >= 0) {
    // 取消该组：只移除"不再被任何已选分组覆盖"的账号
    pickedGroups.value.splice(idx, 1)
    const stillCovered = new Set<string>()
    pickedGroups.value.forEach(g => groupKeys(g).forEach(k => stillCovered.add(k)))

    const toRemove = keys.filter(k => !stillCovered.has(k))
    emit('update:selectedKeys', props.selectedKeys.filter(k => !toRemove.includes(k)))
  } else {
    // 选中该组：整组并入（Set 自动去重）
    pickedGroups.value.push(grp)
    emit('update:selectedKeys', Array.from(new Set([...props.selectedKeys, ...keys])))
  }
}

function toggleGroupExpand(grp: string) {
  const i = expandedGroups.value.indexOf(grp)
  if (i >= 0) expandedGroups.value.splice(i, 1)
  else expandedGroups.value.push(grp)
}

/** 父组件清空选择时，同步清掉分组勾选态 */
watch(() => props.selectedKeys.length, (n) => {
  if (n === 0) pickedGroups.value = []
})

// 过滤后的账号列表（只按搜索过滤，分组由文件夹负责）
const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(acc => {
    // 搜索过滤
    if (accountSearch.value.trim()) {
      const q = accountSearch.value.toLowerCase()
      const nick = (acc.nickname || acc.account).toLowerCase()
      const plat = getPlatformName(acc.platform).toLowerCase()
      if (!nick.includes(q) && !plat.includes(q)) return false
    }
    return true
  })
})

// 覆盖的平台数量
const activePlatformCount = computed(() => {
  const plats = new Set(props.selectedKeys.map(k => k.split(':')[0]))
  return plats.size
})

// 检查是否已选
const isSelected = (acc: any) => {
  return props.selectedKeys.includes(`${acc.platform}:${acc.account}`)
}

/**
 * 账号在已选列表中的序号（1 起）。
 * 这个顺序就是分配顺序 —— 第 1 个被选中的账号会拿到第 1 组内容，
 * 与「内容与账号对应表」里的账号序号必须一致。
 */
function accountOrder(acc: any): number {
  return props.selectedKeys.indexOf(`${acc.platform}:${acc.account}`) + 1
}

/**
 * 把某个已选账号提到最前（= 调整为第 1 个拿内容）。
 * 序号即分配顺序，想改顺序时不必全清重选，点它的序号角标即可。
 */
function promoteAccount(acc: any) {
  const key = `${acc.platform}:${acc.account}`
  const idx = props.selectedKeys.indexOf(key)
  if (idx <= 0) return // 未选中或已在最前，无操作

  const rest = props.selectedKeys.filter((k) => k !== key)
  emit('update:selectedKeys', [key, ...rest])
  ElMessage.info(`已将「${acc.nickname || acc.account}」调整为第 1 个`)
}

// 切换单账号
const toggleAccount = (acc: any) => {
  const key = `${acc.platform}:${acc.account}`
  const current = [...props.selectedKeys]
  const idx = current.indexOf(key)
  if (idx !== -1) {
    // 取消选中：直接移除，无限制
    current.splice(idx, 1)
  } else {
    // 尝试新增：先检查试用账号数上限
    if (authStore.isTrialUser && current.length >= authStore.TRIAL_ACCOUNT_LIMIT) {
      ElNotification.warning({
        message: `试用版最多绑定 ${authStore.TRIAL_ACCOUNT_LIMIT} 个账号，开通后可解除限制`,
        duration: 4000
      })
      return
    }
    current.push(key)
  }
  emit('update:selectedKeys', current)
}

// 全选当前有效账号
const selectAllValid = () => {
  const validKeys = filteredAccounts.value
    .filter(a => a.isValid)
    .map(a => `${a.platform}:${a.account}`)
  const merged = Array.from(new Set([...props.selectedKeys, ...validKeys]))

  // 试用用户：截断到上限
  if (authStore.isTrialUser && merged.length > authStore.TRIAL_ACCOUNT_LIMIT) {
    merged.length = authStore.TRIAL_ACCOUNT_LIMIT
    ElNotification.warning({
      message: `试用版最多绑定 ${authStore.TRIAL_ACCOUNT_LIMIT} 个账号，已自动截取前 ${authStore.TRIAL_ACCOUNT_LIMIT} 个`,
      duration: 4000
    })
  }

  emit('update:selectedKeys', merged)
}

// 清空所选（会一并清掉对应表里的分配，故加确认）
const clearSelection = async () => {
  if (props.selectedKeys.length === 0) return
  try {
    await ElMessageBox.confirm(
      `将取消已选的 ${props.selectedKeys.length} 个账号，对应表中的分配也会一并清空。`,
      '确认清空账号？',
      { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户取消
  }
  emit('update:selectedKeys', [])
  pickedGroups.value = []
}

// 平台辅助方法
const getPlatformName = (pid: string) => {
  return getPlatformConfig(pid)?.name || pid
}

const getPlatformShort = (pid: string) => {
  const name = getPlatformName(pid)
  return name.substring(0, 2)
}

const getPlatformColor = (pid: string) => {
  return getPlatformConfig(pid)?.brandColor || '#6366f1'
}
</script>

<style scoped>
.account-card-picker {
  padding: 20px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-title-box {
  display: flex;
  align-items: center;
  gap: 12px;
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

.badge-count {
  font-size: 12px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 20px;
  padding: 1px 9px;
  font-weight: 600;
  color: var(--primary-color);
}

/* 试用账号超限时徽标变红 */
.badge-count.badge-warn {
  background: rgba(245, 108, 108, 0.08);
  border-color: rgba(245, 108, 108, 0.3);
  color: var(--status-danger);
}

.trial-limit-hint {
  color: var(--status-danger);
  font-weight: 700;
}

.hint-clear {
  color: var(--text-muted);
  font-weight: 400;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── 已选统计行 ── */
.picker-status {
  margin-bottom: 12px;
  flex-shrink: 0;
}

/* ── 左右两栏容器 ── */
.picker-body {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

/* ── 左：分组栏 ── */
.picker-side {
  width: 240px;
  min-width: 240px;
  max-width: 240px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--border-subtle);
  padding-right: 16px;
}

.side-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.side-hint {
  font-size: 10.5px;
  font-weight: 400;
  color: var(--text-muted);
  opacity: .8;
}

.side-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 26px 8px;
  color: var(--text-muted);
  font-size: 11.5px;
  text-align: center;
}
.se-sub { font-size: 10.5px; opacity: .7; }

/* ── 右：账号栏 ── */
.picker-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.picker-main .search-box {
  margin-bottom: 10px;
  flex-shrink: 0;
}

/* ── 分组文件夹列表（撑满左栏） ── */
.group-folder-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 2px;
}

/* ── 账号网格（撑满右侧） ── */
.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  flex: 1;
  min-height: 0;
  align-content: start;
  overflow-y: auto;
  padding-right: 4px;
}

/* ── 滚动条统一样式 ── */
.group-folder-list::-webkit-scrollbar,
.account-grid::-webkit-scrollbar { width: 6px; }
.group-folder-list::-webkit-scrollbar-thumb,
.account-grid::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, .22);
  border-radius: 3px;
}
.group-folder-list::-webkit-scrollbar-thumb:hover,
.account-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 128, 128, .38);
}
.group-folder-list::-webkit-scrollbar-track,
.account-grid::-webkit-scrollbar-track { background: transparent; }

/* ── 响应式：窗口 < 900px 时上下堆叠 ── */
@media (max-width: 900px) {
  .picker-body { flex-direction: column; }
  .picker-side {
    width: auto;
    min-width: 0;
    max-width: none;
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
    padding-right: 0;
    padding-bottom: 12px;
  }
  .group-folder-list { max-height: 200px; }
}

.pick-folder {
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  overflow: hidden;
  transition: border-color .15s, background-color .15s;
}
.pick-folder.all {
  border-color: rgba(79, 70, 229, .38);
  background: rgba(79, 70, 229, .04);
}

.pf-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  cursor: pointer;
}
.pf-head:hover { background: rgba(79, 70, 229, .05); }

.pf-check {
  width: 15px;
  height: 15px;
  border-radius: 4px;
  border: 1.5px solid var(--border-strong, #9ca3af);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 10px;
  transition: all .15s;
}
.pf-check.on {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}
.pf-check.partial {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.pf-dash { font-weight: 700; line-height: 1; }

.pf-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-count {
  margin-left: auto;
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  background: rgba(79, 70, 229, .10);
  color: var(--primary-color);
  white-space: nowrap;
}
.pf-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  opacity: .55;
  transition: transform .18s;
  flex-shrink: 0;
}
.pf-arrow.open { transform: rotate(90deg); }

.pf-members { border-top: 1px solid var(--border-subtle); padding: 4px 6px; }
.pf-member {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 7px;
  border-radius: 6px;
  font-size: 11.5px;
  cursor: pointer;
}
.pf-member:hover { background: rgba(79, 70, 229, .06); }
.pf-member.on { background: rgba(79, 70, 229, .10); }
.pfm-plat { font-size: 10px; padding: 1px 5px; border-radius: 4px; background: rgba(0,0,0,.06); }
.pfm-nick { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pfm-status { margin-left: auto; font-size: 11px; }
.pfm-empty { padding: 9px; font-size: 11px; color: var(--text-muted); text-align: center; }

/* 账号卡片上的分组标签 */
.acc-tags { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 3px; }
.acc-tag {
  font-size: 9.5px;
  padding: 1px 6px;
  border-radius: 20px;
  background: rgba(79, 70, 229, .09);
  color: var(--primary-color);
  cursor: pointer;
}
.acc-tag:hover { background: rgba(79, 70, 229, .18); }

.picked-group-hint { font-size: 11px; color: var(--text-muted); opacity: .8; margin-left: 4px; }

.account-item-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.account-item-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-detail);
}

.account-item-card.selected {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.08);
}

.account-item-card.invalid {
  opacity: 0.7;
}

.platform-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.22); /* 深色主题：保证抖音黑色头像有可见轮廓 */
}

.account-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.account-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

/* account-meta is handled by parent */

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--status-danger);
}

.status-dot.online {
  background: var(--status-success);
}

.status-text {
  color: var(--text-muted);
}

.select-indicator {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--border-subtle);
  background: var(--bg-input);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.select-indicator.active {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.3);
  color: var(--primary-color);
}

.select-indicator.adjustable {
  cursor: pointer;
}

.select-indicator.adjustable:hover {
  transform: scale(1.15);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
}

.select-indicator.active:not(.adjustable) {
  cursor: default;
}

.order-num {
  line-height: 1;
  color: inherit;
}

.empty-account-box {
  text-align: center;
  padding: 28px;
  color: var(--text-muted);
  font-size: 13px;
}

.search-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
