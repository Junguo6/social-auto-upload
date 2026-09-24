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

    <!-- 分组过滤栏与搜索 -->
    <div class="filter-toolbar">
      <span class="badge-count" v-if="selectedKeys.length > 0">
        已选 {{ selectedKeys.length }} 个账号 · 覆盖 {{ activePlatformCount }} 个平台
        <span class="hint-clear">（点「清空」可重新选择，对应表会重新分配）</span>
      </span>
      <div class="group-tabs">
        <button
          v-for="grp in allGroups"
          :key="grp"
          class="group-tab-btn"
          :class="{ active: currentGroup === grp }"
          @click="currentGroup = grp"
        >
          <span>{{ grp }}</span>
          <span class="grp-count">{{ getGroupCount(grp) }}</span>
        </button>
      </div>

      <el-input
        v-model="accountSearch"
        placeholder="搜索账号昵称/平台..."
        size="small"
        clearable
        prefix-icon="Search"
        class="search-box"
      />
    </div>

    <!-- 账号网格流 -->
    <div v-if="filteredAccounts.length > 0" class="account-grid custom-scrollbar">
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
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAccountStore } from '../../stores/accountStore'
import { PLATFORMS, getPlatformConfig } from '../../config/platforms'
import type { SelectedTargetAccount } from '../../types/matrix'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps<{
  selectedKeys: string[] // 格式: "platform:account"
}>()

const emit = defineEmits<{
  (e: 'update:selectedKeys', keys: string[]): void
}>()

const accountStore = useAccountStore()
const currentGroup = ref('全部')
const accountSearch = ref('')

// 分组清单
const allGroups = computed(() => {
  return ['全部', ...accountStore.groups]
})

// 各分组数量统计
const getGroupCount = (grp: string) => {
  if (grp === '全部') return accountStore.accounts.length
  return accountStore.accounts.filter(a => a.group === grp).length
}

// 过滤后的账号列表
const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(acc => {
    // 分组过滤
    if (currentGroup.value !== '全部' && acc.group !== currentGroup.value) {
      return false
    }
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
    current.splice(idx, 1)
  } else {
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
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 20px;
  padding: 1px 9px;
  font-weight: 600;
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

/* 分组与搜索 */
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  row-gap: 8px;
}

.filter-toolbar .badge-count {
  white-space: nowrap;
  flex-shrink: 0;
}

.title-text-group {
  min-width: 0;
}

.main-title {
  white-space: nowrap;
}

.group-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.group-tab-btn {
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.group-tab-btn:hover {
  border-color: var(--primary-color);
  color: var(--text-main);
}

.group-tab-btn.active {
  background: var(--primary-gradient);
  border-color: transparent;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.grp-count {
  font-size: 11px;
  opacity: 0.8;
  background: rgba(0, 0, 0, 0.15);
  padding: 0 5px;
  border-radius: 10px;
}

.search-box {
  max-width: 220px;
}

/* 账号卡片网格 */
.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  flex: 1;                  /* 撑满卡片剩余高度 */
  min-height: 220px;        /* 兜底：窗口极矮时不被压扁 */
  align-content: start;     /* 卡片从顶部排列，不被行高拉伸 */
  overflow-y: auto;
  padding-right: 4px;
}

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
