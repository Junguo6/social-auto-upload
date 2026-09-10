<template>
  <div class="account-card-picker glass-card">
    <div class="card-header">
      <div class="card-title-box">
        <span class="step-badge">2</span>
        <div class="title-text-group">
          <div class="main-title">
            <span>要发到哪些账号</span>
            <span class="req-star">*</span>
            <span class="badge-count" v-if="selectedKeys.length > 0">
              已选 {{ selectedKeys.length }} 个账号 (覆盖 {{ activePlatformCount }} 个平台)
            </span>
          </div>
          <div class="sub-title">勾选目标矩阵账号，系统会自动校验凭证有效性，可按业务分组快捷一键选择</div>
        </div>
      </div>

      <div class="header-actions">
        <el-button size="small" link type="primary" @click="selectAllValid">
          <el-icon><Check /></el-icon> 全选有效账号
        </el-button>
        <el-button size="small" link @click="clearSelection">
          <el-icon><Close /></el-icon> 取消全选
        </el-button>
      </div>
    </div>

    <!-- 分组过滤栏与搜索 -->
    <div class="filter-toolbar">
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
            <span class="plat-name">{{ getPlatformName(acc.platform) }}</span>
            <span class="status-dot" :class="{ online: acc.isValid }"></span>
            <span class="status-text">{{ acc.isValid ? '凭证正常' : '已失效' }}</span>
          </div>
        </div>

        <!-- 选中角标 -->
        <div class="select-indicator" :class="{ active: isSelected(acc) }">
          <el-icon v-if="isSelected(acc)"><Check /></el-icon>
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

// 清空所选
const clearSelection = () => {
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
  return getPlatformConfig(pid)?.color || '#6366f1'
}
</script>

<style scoped>
.account-card-picker {
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
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

.badge-count {
  font-size: 12px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 20px;
  padding: 1px 9px;
  font-weight: 600;
}

.sub-title {
  font-size: 12px;
  color: var(--text-muted);
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
  max-height: 240px;
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
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
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

.plat-name {
  color: var(--text-secondary);
}

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
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid var(--border-highlight);
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.select-indicator.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
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
