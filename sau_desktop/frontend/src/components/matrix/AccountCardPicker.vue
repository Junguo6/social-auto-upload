<template>
  <div class="account-card-picker glass-card">
    <!-- 顶部标题与全局动作（集成已选统计与清单入口，消除下方布局挤压位移） -->
    <div class="card-header">
      <div class="card-title-box">
        <div class="main-title">
          <span>要发到哪些账号</span>
          <span class="req-star">*</span>
        </div>

        <!-- 已选统计轻量徽标（内联呈现，杜绝挤压下方内容） -->
        <transition name="fade">
          <div
            v-if="selectedKeys.length > 0"
            class="header-summary-badge"
            :class="{ 'badge-warn': authStore.isTrialAccountLimitExceeded(selectedKeys.length) }"
          >
            <span class="status-dot"></span>
            <span>已选 <strong>{{ selectedKeys.length }}</strong> 个 · 覆盖 <strong>{{ activePlatformCount }}</strong> 平台</span>
            <span v-if="authStore.isTrialAccountLimitExceeded(selectedKeys.length)" class="trial-limit-hint">
              （上限 {{ authStore.TRIAL_ACCOUNT_LIMIT }}）
            </span>
          </div>
        </transition>
      </div>

      <div class="header-actions">
        <!-- 查看已选清单按钮（内联于顶栏右侧） -->
        <transition name="fade">
          <el-button
            v-if="selectedKeys.length > 0"
            size="small"
            class="selected-view-btn"
            @click="showSelectedDrawer = true"
          >
            <el-icon><List /></el-icon>
            <span>已选清单 ({{ selectedKeys.length }})</span>
          </el-button>
        </transition>

        <el-button size="small" link type="primary" @click="selectAllValid">
          <el-icon><Check /></el-icon> 全选有效
        </el-button>
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

    <!-- 左右两栏布局 -->
    <div class="picker-body">
      <!-- 左：分组导航栏 (Group Navigator) -->
      <div class="picker-side">
        <div class="side-title">
          <span>账号分组</span>
          <span class="side-hint">点击行切换视图 · 勾选框批量选</span>
        </div>

        <div class="group-folder-list">
          <!-- 1. 全部账号 (默认顶层) -->
          <div
            class="pick-folder nav-item"
            :class="{
              active: activeGroupFilter === GROUP_ALL,
              all: isAllFullyPicked
            }"
            @click="activeGroupFilter = GROUP_ALL"
          >
            <div class="pf-head">
              <span
                class="pf-check"
                :class="{ on: isAllFullyPicked, partial: isAllPartiallyPicked }"
                :title="isAllFullyPicked ? '取消全选全部有效账号' : '一键全选全部有效账号'"
                @click.stop="toggleAllPick"
              >
                <el-icon v-if="isAllFullyPicked"><Check /></el-icon>
                <span v-else-if="isAllPartiallyPicked" class="pf-dash">—</span>
              </span>

              <el-icon class="folder-lead-icon" :size="16"><UserFilled /></el-icon>
              <span class="pf-name">全部账号</span>
              <span class="pf-count">{{ selectedKeys.length }}/{{ accountStore.accounts.length }}</span>
            </div>
          </div>

          <!-- 2. 用户自定义分组列表 -->
          <div
            v-for="grp in accountStore.groups"
            :key="grp"
            class="pick-folder nav-item"
            :class="{
              active: activeGroupFilter === grp,
              all: isGroupFullyPicked(grp)
            }"
            @click="activeGroupFilter = grp"
          >
            <div class="pf-head">
              <span
                class="pf-check"
                :class="{ on: isGroupFullyPicked(grp), partial: isGroupPartiallyPicked(grp) }"
                :title="isGroupFullyPicked(grp) ? '取消勾选本组' : '全选本组账号'"
                @click.stop="toggleGroupPick(grp)"
              >
                <el-icon v-if="isGroupFullyPicked(grp)"><Check /></el-icon>
                <span v-else-if="isGroupPartiallyPicked(grp)" class="pf-dash">—</span>
              </span>

              <FolderIcon :size="16" />
              <span class="pf-name" :title="grp">{{ grp }}</span>
              <span class="pf-count">{{ pickedCountIn(grp) }}/{{ groupKeys(grp).length }}</span>
            </div>
          </div>

          <!-- 3. 未分组账号（若存在则展示） -->
          <div
            v-if="ungroupedAccounts.length > 0"
            class="pick-folder nav-item ungrouped-item"
            :class="{
              active: activeGroupFilter === GROUP_UNGROUPED,
              all: isUngroupedFullyPicked
            }"
            @click="activeGroupFilter = GROUP_UNGROUPED"
          >
            <div class="pf-head">
              <span
                class="pf-check"
                :class="{ on: isUngroupedFullyPicked, partial: isUngroupedPartiallyPicked }"
                :title="isUngroupedFullyPicked ? '取消勾选未分组' : '全选未分组账号'"
                @click.stop="toggleUngroupedPick"
              >
                <el-icon v-if="isUngroupedFullyPicked"><Check /></el-icon>
                <span v-else-if="isUngroupedPartiallyPicked" class="pf-dash">—</span>
              </span>

              <el-icon class="folder-lead-icon" :size="16"><Folder /></el-icon>
              <span class="pf-name">未分组账号</span>
              <span class="pf-count">{{ pickedCountInUngrouped }}/{{ ungroupedAccounts.length }}</span>
            </div>
          </div>
        </div>

        <div class="side-footer-tip" v-if="accountStore.groups.length === 0">
          <span class="se-sub">可在「账号管理」中为账号创建专属分组</span>
        </div>
      </div>

      <!-- 右：账号工作区 (Main Workspace) -->
      <div class="picker-main">
        <!-- 分组上下文与搜索工具栏（简约单行、防挤压溢出） -->
        <div class="group-context-banner">
          <div class="context-left">
            <span class="context-icon">
              <FolderIcon v-if="activeGroupFilter !== GROUP_ALL && activeGroupFilter !== GROUP_UNGROUPED" :size="15" />
              <el-icon v-else-if="activeGroupFilter === GROUP_UNGROUPED" :size="15"><Folder /></el-icon>
              <el-icon v-else :size="15"><UserFilled /></el-icon>
            </span>
            <span class="context-group-name" :title="currentGroupTitle">{{ currentGroupTitle }}</span>
            <span class="context-counter">
              已选 <strong>{{ currentGroupPickedCount }}</strong>/{{ currentGroupAccounts.length }}
            </span>
          </div>

          <div class="context-right">
            <!-- 当前组快捷全选/反选 -->
            <el-button
              v-if="currentGroupAccounts.length > 0"
              size="small"
              :type="isCurrentGroupAllPicked ? 'default' : 'primary'"
              plain
              class="group-batch-btn"
              @click="toggleCurrentGroupPick"
            >
              {{ isCurrentGroupAllPicked ? '取消本组' : '全选本组' }}
            </el-button>

            <!-- 搜索框 -->
            <el-input
              v-model="accountSearch"
              placeholder="搜索账号..."
              size="small"
              clearable
              prefix-icon="Search"
              class="search-box"
            />
          </div>
        </div>

        <!-- 账号卡片列表 -->
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
            <!-- 复合头像：用户高清头像 + 右下角平台官方图标徽标 -->
            <div class="account-avatar-wrapper">
              <img
                v-if="acc.avatar && !acc.avatarLoadFailed"
                :src="acc.avatar"
                class="account-real-avatar"
                referrerpolicy="no-referrer"
                @error="acc.avatarLoadFailed = true"
                :alt="acc.nickname || acc.account"
              />
              <div
                v-else
                class="account-fallback-avatar"
                :style="{ background: getPlatformColor(acc.platform) }"
              >
                {{ getAccountAvatarText(acc) }}
              </div>

              <!-- 右下角平台微型徽标 -->
              <div class="platform-badge" :title="getPlatformName(acc.platform)">
                <PlatformIcon :platform="acc.platform" :size="11" />
              </div>
            </div>

            <!-- 账号信息 -->
            <div class="account-info">
              <div class="account-name-row">
                <span class="account-name" :title="acc.nickname || acc.account">
                  {{ acc.nickname || acc.account }}
                </span>
                <span v-if="!acc.isValid" class="invalid-badge">已失效</span>
              </div>

              <!-- 所属分组标签（单行+防挤压：展示主标签，多出的折叠为 +N，悬浮可看全部） -->
              <div
                class="acc-tags"
                v-if="acc.groups && acc.groups.length"
                :title="`所属分组：${acc.groups.join('、')}`"
              >
                <span
                  class="acc-tag"
                  :class="{ active: activeGroupFilter === getDisplayGroups(acc.groups)[0] }"
                  :title="`点击聚焦查看【${getDisplayGroups(acc.groups)[0]}】分组`"
                  @click.stop="activeGroupFilter = getDisplayGroups(acc.groups)[0]"
                >
                  #{{ getDisplayGroups(acc.groups)[0] }}
                </span>
                <span
                  v-if="acc.groups.length > 1"
                  class="acc-tag-more"
                  :title="`更多分组(${acc.groups.length})：\n${acc.groups.join('、')}`"
                >
                  +{{ acc.groups.length - 1 }}
                </span>
              </div>
              <div v-else class="acc-no-group">
                <span class="no-group-text">未分组</span>
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

        <!-- 当前分组无账号空状态 -->
        <div v-else-if="accountStore.accounts.length === 0" class="empty-account-box">
          <div class="empty-text">当前尚未接入任何发布账号</div>
          <router-link to="/accounts">
            <el-button type="primary" class="gradient-btn-sm" style="margin-top: 10px;">
              <el-icon><Plus /></el-icon> 前往账号管理添加
            </el-button>
          </router-link>
        </div>

        <!-- 搜索或分组下无匹配 -->
        <div v-else class="search-empty">
          <div class="empty-prompt">
            <span>当前分组「{{ currentGroupTitle }}」下未找到匹配的账号</span>
            <el-button v-if="activeGroupFilter !== GROUP_ALL" size="small" link type="primary" @click="activeGroupFilter = GROUP_ALL">
              查看全部账号
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 已选账号清单抽屉 / 弹层 -->
    <el-drawer
      v-model="showSelectedDrawer"
      title="已选账号清单与分配顺序"
      size="440px"
      append-to-body
    >
      <div class="selected-drawer-content">
        <div class="drawer-meta-bar">
          <span>共勾选 <strong>{{ selectedAccountObjects.length }}</strong> 个发布账号（按分配顺序排列）</span>
          <el-button size="small" type="danger" link @click="clearSelection">全部清空</el-button>
        </div>

        <div class="selected-list custom-scrollbar">
          <div
            v-for="(acc, index) in selectedAccountObjects"
            :key="`${acc.platform}:${acc.account}`"
            class="selected-row-item"
          >
            <div class="row-order-badge">{{ index + 1 }}</div>
            <div class="row-avatar-wrap">
              <img
                v-if="acc.avatar && !acc.avatarLoadFailed"
                :src="acc.avatar"
                class="row-real-avatar"
                referrerpolicy="no-referrer"
                @error="acc.avatarLoadFailed = true"
              />
              <div
                v-else
                class="row-fallback-avatar"
                :style="{ background: getPlatformColor(acc.platform) }"
              >
                {{ getAccountAvatarText(acc) }}
              </div>
              <div class="row-platform-badge" :title="getPlatformName(acc.platform)">
                <PlatformIcon :platform="acc.platform" :size="10" />
              </div>
            </div>
            <div class="row-detail">
              <div class="row-name" :title="acc.nickname || acc.account">{{ acc.nickname || acc.account }}</div>
              <div class="row-groups">
                <span class="plat-tag">{{ getPlatformName(acc.platform) }}</span>
                <span v-for="g in (acc.groups || [])" :key="g" class="group-pill">#{{ g }}</span>
              </div>
            </div>
            <div class="row-tools">
              <el-button
                v-if="index > 0"
                size="small"
                text
                type="primary"
                title="置顶为第 1 顺位"
                @click="promoteAccount(acc)"
              >
                置顶
              </el-button>
              <el-button
                size="small"
                text
                type="danger"
                title="移出选择"
                @click="toggleAccount(acc)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
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
import PlatformIcon from './PlatformIcon.vue'
import { Check, ArrowRight, Plus, Delete, Search, UserFilled, Folder, List } from '@element-plus/icons-vue'

const props = defineProps<{
  selectedKeys: string[] // 格式: "platform:account"
}>()

const emit = defineEmits<{
  (e: 'update:selectedKeys', keys: string[]): void
}>()

const accountStore = useAccountStore()
const authStore = useAuthStore()
const accountSearch = ref('')

// 分组导航常量与当前活跃分组过滤器
const GROUP_ALL = '__ALL__'
const GROUP_UNGROUPED = '__UNGROUPED__'
const activeGroupFilter = ref<string>(GROUP_ALL)
const showSelectedDrawer = ref(false)

/* ───────── 分组数据计算与一键勾选 ───────── */

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

/** 未分组账号 */
const ungroupedAccounts = computed(() => {
  return accountStore.accounts.filter(a => !a.groups || a.groups.length === 0)
})

const ungroupedKeys = computed(() => {
  return ungroupedAccounts.value.map(a => `${a.platform}:${a.account}`)
})

const pickedCountInUngrouped = computed(() => {
  return ungroupedKeys.value.filter(k => props.selectedKeys.includes(k)).length
})

const isUngroupedFullyPicked = computed(() => {
  const keys = ungroupedKeys.value
  return keys.length > 0 && keys.every(k => props.selectedKeys.includes(k))
})

const isUngroupedPartiallyPicked = computed(() => {
  const n = pickedCountInUngrouped.value
  return n > 0 && n < ungroupedKeys.value.length
})

/** 全部账号的全选/部分选状态 */
const isAllFullyPicked = computed(() => {
  const validKeys = accountStore.accounts.filter(a => a.isValid).map(a => `${a.platform}:${a.account}`)
  return validKeys.length > 0 && validKeys.every(k => props.selectedKeys.includes(k))
})

const isAllPartiallyPicked = computed(() => {
  return props.selectedKeys.length > 0 && !isAllFullyPicked.value
})

/** 切换全部账号的全选/取消 */
function toggleAllPick() {
  if (isAllFullyPicked.value) {
    emit('update:selectedKeys', [])
  } else {
    selectAllValid()
  }
}

/** 切换未分组账号的全选/取消 */
function toggleUngroupedPick() {
  const keys = ungroupedKeys.value
  if (isUngroupedFullyPicked.value) {
    emit('update:selectedKeys', props.selectedKeys.filter(k => !keys.includes(k)))
  } else {
    emit('update:selectedKeys', Array.from(new Set([...props.selectedKeys, ...keys])))
  }
}

/** 切换具体分组的全选/取消 */
function toggleGroupPick(grp: string) {
  const keys = groupKeys(grp)
  if (isGroupFullyPicked(grp)) {
    // 已全选本组 -> 取消勾选本组
    emit('update:selectedKeys', props.selectedKeys.filter(k => !keys.includes(k)))
  } else {
    // 未全选 -> 全选本组
    emit('update:selectedKeys', Array.from(new Set([...props.selectedKeys, ...keys])))
  }
}

/* ───────── 当前聚焦分组的上下文数据 ───────── */
const currentGroupTitle = computed(() => {
  if (activeGroupFilter.value === GROUP_ALL) return '全部账号'
  if (activeGroupFilter.value === GROUP_UNGROUPED) return '未分组账号'
  return activeGroupFilter.value
})

const currentGroupAccounts = computed(() => {
  if (activeGroupFilter.value === GROUP_UNGROUPED) {
    return ungroupedAccounts.value
  }
  if (activeGroupFilter.value !== GROUP_ALL) {
    return groupMembers(activeGroupFilter.value)
  }
  return accountStore.accounts
})

const currentGroupPickedCount = computed(() => {
  return currentGroupAccounts.value.filter(a => isSelected(a)).length
})

const isCurrentGroupAllPicked = computed(() => {
  const list = currentGroupAccounts.value.filter(a => a.isValid)
  return list.length > 0 && list.every(a => isSelected(a))
})

function toggleCurrentGroupPick() {
  if (activeGroupFilter.value === GROUP_ALL) {
    toggleAllPick()
  } else if (activeGroupFilter.value === GROUP_UNGROUPED) {
    toggleUngroupedPick()
  } else {
    toggleGroupPick(activeGroupFilter.value)
  }
}

// 过滤后的账号列表：先根据左侧当前分组筛选，再按搜索词筛选
const filteredAccounts = computed(() => {
  let list = currentGroupAccounts.value

  // 搜索过滤
  if (accountSearch.value.trim()) {
    const q = accountSearch.value.toLowerCase()
    list = list.filter(acc => {
      const nick = (acc.nickname || acc.account).toLowerCase()
      const plat = getPlatformName(acc.platform).toLowerCase()
      return nick.includes(q) || plat.includes(q)
    })
  }
  return list
})

// 覆盖的平台数量
const activePlatformCount = computed(() => {
  const plats = new Set(props.selectedKeys.map(k => k.split(':')[0]))
  return plats.size
})

// 已选账号详细对象列表（按选中先后分配顺序）
const selectedAccountObjects = computed(() => {
  return props.selectedKeys.map(k => {
    const [platform, account] = k.split(':')
    const found = accountStore.accounts.find(a => a.platform === platform && a.account === account)
    return found || {
      platform,
      account,
      nickname: account,
      isValid: true,
      groups: []
    }
  })
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
 */
function promoteAccount(acc: any) {
  const key = `${acc.platform}:${acc.account}`
  const idx = props.selectedKeys.indexOf(key)
  if (idx <= 0) return

  const rest = props.selectedKeys.filter((k) => k !== key)
  emit('update:selectedKeys', [key, ...rest])
  ElMessage.info(`已将「${acc.nickname || acc.account}」调整为第 1 顺位`)
}

// 切换单账号
const toggleAccount = (acc: any) => {
  const key = `${acc.platform}:${acc.account}`
  const current = [...props.selectedKeys]
  const idx = current.indexOf(key)
  if (idx !== -1) {
    current.splice(idx, 1)
  } else {
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

// 全选全部有效账号
const selectAllValid = () => {
  const validKeys = accountStore.accounts
    .filter(a => a.isValid)
    .map(a => `${a.platform}:${a.account}`)
  const merged = Array.from(new Set([...props.selectedKeys, ...validKeys]))

  if (authStore.isTrialUser && merged.length > authStore.TRIAL_ACCOUNT_LIMIT) {
    merged.length = authStore.TRIAL_ACCOUNT_LIMIT
    ElNotification.warning({
      message: `试用版最多绑定 ${authStore.TRIAL_ACCOUNT_LIMIT} 个账号，已自动截取前 ${authStore.TRIAL_ACCOUNT_LIMIT} 个`,
      duration: 4000
    })
  }

  emit('update:selectedKeys', merged)
}

// 清空所选
const clearSelection = async () => {
  if (props.selectedKeys.length === 0) return
  try {
    await ElMessageBox.confirm(
      `将取消已选的 ${props.selectedKeys.length} 个账号，对应表中的分配也会一并清空。`,
      '确认清空账号？',
      { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  emit('update:selectedKeys', [])
}

// 平台与头像辅助方法
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

const getAccountAvatarText = (acc?: any) => {
  if (!acc) return 'U'
  const name = acc.nickname || acc.account || 'U'
  return name.trim().slice(0, 1).toUpperCase()
}

/** 优先返回当前聚焦的分组 */
function getDisplayGroups(groups?: string[]): string[] {
  if (!groups || groups.length === 0) return []
  if (
    activeGroupFilter.value !== GROUP_ALL &&
    activeGroupFilter.value !== GROUP_UNGROUPED &&
    groups.includes(activeGroupFilter.value)
  ) {
    const rest = groups.filter(g => g !== activeGroupFilter.value)
    return [activeGroupFilter.value, ...rest]
  }
  return groups
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
  height: 36px;
  min-height: 36px;
  max-height: 36px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: nowrap !important;
  white-space: nowrap;
  box-sizing: border-box;
  overflow: hidden;
}

.card-title-box {
  height: 36px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  min-width: 0;
  flex-shrink: 1;
}

.main-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 36px;
}

.req-star {
  color: var(--status-danger);
}

/* 顶部内联轻量已选统计徽标（高度锁定 24px，在 36px Header 中严格居中） */
.header-summary-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  padding: 0 9px;
  height: 24px;
  line-height: 24px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  color: var(--text-main);
  white-space: nowrap;
  box-sizing: border-box;
  flex-shrink: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-summary-badge .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  flex-shrink: 0;
}

.header-summary-badge strong {
  color: var(--primary-color);
  font-weight: 700;
}

.header-summary-badge.badge-warn strong,
.header-summary-badge.badge-warn .status-dot {
  color: var(--status-danger);
  background: var(--status-danger);
}

.header-summary-badge.badge-warn {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}

.trial-limit-hint {
  color: var(--status-danger);
  font-weight: 600;
  font-size: 11px;
}

.header-actions {
  height: 36px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
  white-space: nowrap;
}

.selected-view-btn {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary-color);
  background: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.22);
  border-radius: 5px;
  padding: 0 9px;
  height: 26px;
  line-height: 24px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}

.selected-view-btn:hover {
  background: rgba(99, 102, 241, 0.08);
  border-color: var(--primary-color);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* ── 左右两栏容器 ── */
.picker-body {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

/* ── 左：分组导航栏 ── */
.picker-side {
  width: 250px;
  min-width: 250px;
  max-width: 250px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--border-subtle);
  padding-right: 14px;
}

.side-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.side-title span:first-child {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.side-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  opacity: .85;
}

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

.side-footer-tip {
  padding-top: 10px;
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

/* ── 分组项 Nav Item ── */
.pick-folder {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--bg-input);
  position: relative;
  cursor: pointer;
}

.pick-folder:hover {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(99, 102, 241, 0.03);
}

/* 当前激活查看的分组 */
.pick-folder.active {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.09);
  box-shadow: 0 1px 3px rgba(99, 102, 241, 0.12);
}

.pick-folder.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3.5px;
  background: var(--primary-color);
  border-radius: 0 2px 2px 0;
}

.pick-folder.all .pf-count {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.pf-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  user-select: none;
}

.pf-check {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--border-strong, #9ca3af);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 10px;
  transition: all .15s;
  background: #ffffff;
  cursor: pointer;
}

.pf-check:hover {
  border-color: var(--primary-color);
}

.pf-check.on {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}

.pf-check.partial {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
}

.pf-dash {
  font-weight: 700;
  line-height: 1;
}

.folder-lead-icon {
  color: var(--text-muted);
}

.pick-folder.active .folder-lead-icon {
  color: var(--primary-color);
}

.pf-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.pick-folder.active .pf-name {
  color: var(--primary-color);
  font-weight: 700;
}

.pf-count {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-muted);
  white-space: nowrap;
}

.pick-folder.active .pf-count {
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary-color);
}

/* ── 右：账号主工作区 ── */
.picker-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── 分组上下文与搜索工具栏 ── */
.group-context-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  gap: 10px;
  padding: 5px 10px;
  background: var(--bg-hover, #f8fafc);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  margin-bottom: 10px;
  box-sizing: border-box;
  width: 100%;
  min-height: 36px;
}

.context-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex-shrink: 1;
  overflow: hidden;
  white-space: nowrap;
}

.context-icon {
  display: inline-flex;
  align-items: center;
  color: var(--primary-color);
  flex-shrink: 0;
}

.context-group-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.context-counter {
  font-size: 11.5px;
  color: var(--text-muted);
  white-space: nowrap;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.04);
}

.context-counter strong {
  color: var(--primary-color);
  font-weight: 700;
}

.context-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
}

.group-batch-btn {
  font-size: 12px;
  height: 26px;
  padding: 0 9px;
  flex-shrink: 0;
}

.search-box {
  width: 135px;
  flex-shrink: 0;
}

.search-box :deep(.el-input__wrapper) {
  padding-left: 7px;
  padding-right: 7px;
  height: 26px;
  line-height: 26px;
  font-size: 12px;
}

/* ── 账号网格 ── */
.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(185px, 1fr));
  gap: 10px;
  flex: 1;
  min-height: 0;
  align-content: start;
  overflow-y: auto;
  padding-right: 4px;
}

/* ── 账号卡片 ── */
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

/* ── 头像与平台徽标复合组件 ── */
.account-avatar-wrapper {
  position: relative;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.account-real-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
  display: block;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  background: var(--bg-hover, #f1f5f9);
}

.account-fallback-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.platform-badge {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #ffffff;
  border: 1.5px solid var(--bg-card, #ffffff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.account-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  justify-content: center;
}

.account-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.account-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.invalid-badge {
  font-size: 10px;
  color: var(--status-danger, #ef4444);
  background: rgba(239, 68, 68, 0.1);
  padding: 0 4px;
  border-radius: 3px;
  flex-shrink: 0;
  line-height: 16px;
}

/* 分组标签容器（严格单行、不换行） */
.acc-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
}

.acc-tag {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
  cursor: pointer;
  max-width: 76px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: all 0.15s ease;
  line-height: 16px;
}

.acc-tag:hover {
  background: rgba(99, 102, 241, 0.18);
}

.acc-tag.active {
  background: var(--primary-color);
  color: #ffffff;
  font-weight: 600;
}

.acc-tag-more {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-muted);
  line-height: 16px;
  flex-shrink: 0;
  font-weight: 500;
}

.acc-no-group {
  line-height: 16px;
}

.no-group-text {
  font-size: 10.5px;
  color: var(--text-muted);
  opacity: 0.6;
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

.order-num {
  line-height: 1;
  color: inherit;
}

.empty-account-box,
.search-empty {
  text-align: center;
  padding: 36px 20px;
  color: var(--text-muted);
  font-size: 13px;
}

.empty-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* ── 抽屉清单 ── */
.selected-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12.5px;
  color: #475569;
}

.drawer-meta-bar strong {
  color: var(--primary-color);
}

.selected-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selected-row-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.15s ease;
}

.selected-row-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.row-order-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.12);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.row-avatar-wrap {
  position: relative;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.row-real-avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  object-fit: cover;
}

.row-fallback-avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.row-platform-badge {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
}

.row-detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.row-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-groups {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.plat-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
}

.group-pill {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary-color);
}

.row-tools {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 滚动条与响应式 */
.group-folder-list::-webkit-scrollbar,
.account-grid::-webkit-scrollbar,
.selected-list::-webkit-scrollbar { width: 6px; }
.group-folder-list::-webkit-scrollbar-thumb,
.account-grid::-webkit-scrollbar-thumb,
.selected-list::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, .22);
  border-radius: 3px;
}
.group-folder-list::-webkit-scrollbar-thumb:hover,
.account-grid::-webkit-scrollbar-thumb:hover,
.selected-list::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 128, 128, .38);
}
.group-folder-list::-webkit-scrollbar-track,
.account-grid::-webkit-scrollbar-track,
.selected-list::-webkit-scrollbar-track { background: transparent; }

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
</style>
