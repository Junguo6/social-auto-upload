<template>
  <div class="account-browser-workspace">
    <!-- 顶部汇总条：一眼看清整体状况 + 两个主入口 -->
    <div class="account-summary-bar">
      <div class="sum-left">
        <span class="sum-total">共 {{ accountStore.accounts.length }} 个账号</span>
        <span class="sum-sep">·</span>
        <button
          class="sum-invalid"
          :class="{ zero: invalidCount === 0 }"
          :disabled="invalidCount === 0"
          @click="filterOnlyInvalid"
        >
          {{ invalidCount > 0 ? `${invalidCount} 个需重新登录` : '全部登录正常' }}
        </button>
      </div>

      <!-- 有勾选 → 显示批量操作栏（无勾选时完全隐藏） -->
      <div class="sum-batch" v-if="checkedAccounts.length > 0">
        <span class="batch-count">已选 {{ checkedAccounts.length }} 个</span>

        <el-button size="small" plain :loading="batchChecking" @click="handleBatchCheck">
          <el-icon><Search /></el-icon><span>检测登录状态</span>
        </el-button>

        <el-dropdown trigger="click" @command="handleBatchMove">
          <el-button size="small" plain>
            <FolderIcon :size="13" /><span>移动到分组</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="g in accountStore.groups"
                :key="g"
                :command="g"
              >{{ g }}（{{ accountStore.groupCounts[g] || 0 }}）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button size="small" plain type="danger" @click="handleBatchDelete">
          <el-icon><Delete /></el-icon><span>删除</span>
        </el-button>

        <el-button size="small" text @click="checkedAccounts = []">取消</el-button>
      </div>

      <div class="sum-right">
        <el-button type="primary" @click="openAddAccountDialog">
          <el-icon><Plus /></el-icon>
          <span>添加账号</span>
        </el-button>
        <el-button plain @click="showGroupDialog = true">
          <FolderIcon :size="13" />
          <span>分组管理</span>
        </el-button>
      </div>
    </div>

    <!-- 左右两栏 -->
    <div class="accounts-body" :class="{ 'collapsed': browserCollapsed }">
      <!-- 👈 左侧：账号列表侧边栏 -->
      <div class="account-sidebar-pane">
        <!-- 1. 顶部操作与搜索中枢 -->
        <div class="sidebar-header-section">
          <!-- 浏览器收起时的恢复入口 -->
          <el-button
            v-if="browserCollapsed"
            size="small"
            plain
            class="expand-browser-btn"
            @click="browserCollapsed = false"
          >
            <el-icon><ArrowLeft /></el-icon>
            <span>展开浏览器</span>
          </el-button>

          <!-- 搜索框 -->
          <div class="sidebar-search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索昵称 / 账号 / UID..."
              prefix-icon="Search"
              clearable
              size="default"
            />
          </div>

          <!-- 平台与业务双维度快速筛选 -->
          <div class="sidebar-filter-bar">
            <el-select v-model="currentPlatformFilter" size="small" style="width: 110px;">
              <el-option label="全部平台" value="all" />
              <el-option
                v-for="plat in availablePlatforms"
                :key="plat.id"
                :label="plat.name"
                :value="plat.id"
              />
            </el-select>

            <el-select v-model="currentGroupFilter" size="small" style="flex: 1;">
              <el-option label="全部分组" value="all" />
              <el-option
                v-for="grp in accountStore.groups"
                :key="grp"
                :label="grp"
                :value="grp"
              />
            </el-select>

            <el-tooltip content="管理/新建分组" placement="top">
              <el-button size="small" type="info" plain circle @click="showGroupDialog = true">
                <el-icon><FolderAdd /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <!-- 2. 账号联系人滚动列表 -->
        <div class="sidebar-contact-list custom-scrollbar">
          <!-- 空状态：仅在没有任何账号且无正在接入任务时显示 -->
          <div v-if="filteredAccounts.length === 0 && pendingAccountLogins.length === 0" class="contact-empty-state">
            <el-icon class="empty-icon"><UserFilled /></el-icon>
            <p class="empty-title">未找到匹配的账号</p>
            <el-button size="small" type="primary" link @click="openNewTab">
              接入新账号
            </el-button>
          </div>

          <!-- 正在接入中的新账号临时卡片 -->
          <div
            v-for="pending in pendingAccountLogins"
            :key="pending.id"
            class="contact-card-item is-pending-login"
          >
            <div class="contact-avatar-wrapper" :style="{ background: getPlatformStyle(pending.platform).gradient }">
              <el-icon class="avatar-pending-spinner is-loading"><Loading /></el-icon>
            </div>

            <div class="contact-meta-content">
              <div class="contact-first-row">
                <span class="contact-name-text pending-title">
                  <span class="plat-chip" :title="getPlatformStyle(pending.platform).name">
                    {{ platShort(pending.platform) }}
                  </span>
                  {{ pending.alias ? `正在接入 [${pending.alias}]...` : '正在接入新账号...' }}
                </span>
              </div>

              <div class="contact-second-row">
                <span class="contact-group-name">#{{ pending.alias ? pending.alias : '接入中' }}</span>
                <span class="contact-status-label status-syncing">
                  <el-icon class="is-loading" style="margin-right: 2px;"><Loading /></el-icon>
                  <span>{{ pending.statusText }}</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 账号联系人单元 -->
          <div
            v-for="acc in filteredAccounts"
            :key="acc.platform + ':' + acc.account"
            class="contact-card-item"
            :class="{ 'is-active': activeTabId === `${acc.platform}:${acc.account}`, dragging: isDragging(acc) }"
            draggable="true"
            @dragstart="onDragStart(acc, $event)"
            @dragend="onDragEnd"
            @click="openAccountTab(acc)"
          >
            <!-- 左侧勾选框 (批量操作) -->
            <el-checkbox
              class="acc-check"
              :model-value="checkedAccounts.includes(accKey(acc))"
              @click.stop
              @change="(v: any) => toggleAccountCheck(acc, !!v)"
            />

            <!-- 头像模块 -->
            <div class="contact-avatar-wrapper" :style="{ background: getPlatformStyle(acc.platform).gradient }">
              <img
                v-if="acc.avatar && !acc.avatarLoadFailed"
                :src="acc.avatar"
                class="contact-real-avatar"
                referrerpolicy="no-referrer"
                @error="acc.avatarLoadFailed = true"
                :alt="acc.nickname || acc.account"
              />
              <span v-else class="avatar-char">{{ getAccountAvatarText(acc) }}</span>
            </div>

            <!-- 文本与状态信息 -->
            <div class="contact-meta-content">
              <div class="contact-first-row">
                <span class="contact-name-text">
                  <span class="plat-chip" :title="getPlatformStyle(acc.platform).name">
                    {{ platShort(acc.platform) }}
                  </span>
                  {{ acc.nickname || acc.account }}
                </span>
              </div>

              <div class="contact-second-row">
                <!-- 点这里直接改分组 -->
                <el-popover
                  :width="200"
                  trigger="click"
                  placement="right-start"
                  popper-class="group-picker-popover"
                  @show="newGroupNameForAccount = ''"
                >
                  <template #reference>
                    <span class="contact-group-name clickable">
                      {{ (acc.groups && acc.groups.length) ? '#' + acc.groups.join(' #') : '未分组' }}
                      <el-icon class="grp-caret"><ArrowDown /></el-icon>
                    </span>
                  </template>

                  <div class="group-picker">
                    <div class="gp-title">移动到分组</div>
                    <div
                      v-for="grp in accountStore.groups"
                      :key="grp"
                      class="gp-item"
                      :class="{ on: (acc.groups || []).includes(grp) }"
                      @click="assignGroup(acc, grp)"
                    >
                      <el-icon v-if="(acc.groups || []).includes(grp)" class="gp-check"><Check /></el-icon>
                      <span v-else class="gp-check placeholder" />
                      <span class="gp-name">{{ grp }}</span>
                      <span class="gp-count">{{ accountStore.groupCounts[grp] || 0 }}</span>
                    </div>

                    <div class="gp-divider" />

                    <div class="gp-new">
                      <el-input
                        v-model="newGroupNameForAccount"
                        size="small"
                        placeholder="新建分组…"
                        @keyup.enter="createGroupAndAssign(acc)"
                      />
                      <el-button
                        size="small"
                        type="primary"
                        :disabled="!newGroupNameForAccount.trim()"
                        @click="createGroupAndAssign(acc)"
                      >新建</el-button>
                    </div>
                  </div>
                </el-popover>

                <span
                  class="contact-status-label"
                  :class="{ 'status-err': acc.checked && !acc.isValid, 'status-ok': acc.checked && acc.isValid, 'status-syncing': acc.isSyncing || acc.loading }"
                >
                  <el-icon v-if="acc.isSyncing || acc.loading" class="is-loading" style="margin-right: 2px;"><Loading /></el-icon>
                  <span>{{ (acc.isSyncing || acc.loading) ? '同步中...' : (acc.checked ? (acc.isValid ? '登录正常' : '需重新扫码') : '待检测') }}</span>
                </span>

                <!-- 上次检测时间 -->
                <span
                  v-if="acc.checkedAt"
                  class="contact-checked-at"
                  :class="{ stale: isStaleCheck(acc.checkedAt) }"
                  :title="new Date(acc.checkedAt).toLocaleString('zh-CN')"
                >
                  {{ fmtCheckedAt(acc.checkedAt) }}
                </span>

                <!-- 操作按钮 -->
                <span class="acc-acts" @click.stop>
                  <el-tooltip content="检测登录状态" placement="top">
                    <el-icon class="acc-act" :class="{ spinning: acc.isSyncing }" @click="checkStatus(acc)"><Refresh /></el-icon>
                  </el-tooltip>
                  <el-tooltip content="打开浏览器登录" placement="top">
                    <el-icon class="acc-act" @click="openBrowserForAccount(acc)"><Monitor /></el-icon>
                  </el-tooltip>
                </span>
              </div>

              <!-- 分组标签 -->
              <div class="acc-group-tags" v-if="acc.groups && acc.groups.length">
                <span v-for="g in acc.groups" :key="g" class="acc-gtag">#{{ g }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 👉 右侧：分组（文件夹形式） -->
      <div class="groups-pane" v-show="!browserCollapsed">
        <div class="gsp-head">
          <span class="gsp-title">分组</span>
          <span class="gsp-count">{{ accountStore.groups.length }} 个</span>
          <span class="gsp-spacer"></span>
          <el-button size="small" text @click="showGroupDialog = true">
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>

        <!-- 新建分组 -->
        <div class="gsp-create">
          <el-input
            v-model="newGroupName"
            size="small"
            placeholder="新分组名称"
            clearable
            @keyup.enter="handleCreateGroupInline"
          />
          <el-button size="small" type="primary" plain @click="handleCreateGroupInline">新建</el-button>
        </div>

        <!-- 文件夹列表 -->
        <div class="gsp-list" v-if="accountStore.groups.length > 0">
          <div
            v-for="grp in accountStore.groups"
            :key="grp"
            class="folder"
            :class="{ drop: dropTargetGroup === grp }"
            @dragover.prevent="onDragOverGroup(grp)"
            @dragleave="onDragLeaveGroup(grp)"
            @drop.prevent="onDropToGroup(grp)"
          >
            <div class="folder-head" @click="toggleGroupExpand(grp)">
              <el-icon class="f-arrow" :class="{ open: expandedGroups.includes(grp) }">
                <ArrowRight />
              </el-icon>
              <FolderIcon :size="17" />
              <span class="f-name">{{ grp }}</span>
              <span class="f-count">{{ accountStore.groupCounts[grp] || 0 }}</span>

              <el-dropdown
                trigger="click"
                placement="bottom-end"
                @command="(cmd: string) => handleGroupCommand(cmd, grp)"
                @click.stop
              >
                <span class="f-more" @click.stop><el-icon><MoreFilled /></el-icon></span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename"><el-icon><EditPen /></el-icon>重命名</el-dropdown-item>
                    <el-dropdown-item command="selectAll"><el-icon><Select /></el-icon>选中该组账号</el-dropdown-item>
                    <el-dropdown-item command="delete" divided><el-icon><Delete /></el-icon>删除分组</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- 拖拽提示 -->
            <div class="f-drop-hint" v-if="dropTargetGroup === grp">
              ⬇ 松开即可加入 {{ draggingAccounts.length }} 个账号
            </div>

            <!-- 展开的成员 -->
            <div class="f-members" v-if="expandedGroups.includes(grp)">
              <div
                v-for="m in groupMembers(grp)"
                :key="`${m.platform}:${m.account}`"
                class="f-member"
                @click="openAccountTab(m)"
              >
                <span class="fm-plat">{{ platShort(m.platform) }}</span>
                <span class="fm-nick">{{ m.nickname || m.account }}</span>
                <span class="fm-status" :class="m.isValid ? 'ok' : 'bad'">
                  {{ m.isValid ? '✅' : (m.checked ? '⚠️' : '—') }}
                </span>
                <span
                  class="fm-x"
                  title="从该分组移除（不删除账号）"
                  @click.stop="handleRemoveFromGroup(m, grp)"
                >✕</span>
              </div>
              <div class="f-empty" v-if="groupMembers(grp).length === 0">
                这个分组还没有账号，从左侧拖进来
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="gsp-empty" v-else>
          <FolderIcon :size="30" />
          <span>还没有分组</span>
          <span class="gsp-empty-sub">在上面输入名称，点「新建」开始</span>
        </div>

        <div class="gsp-tip">
          💡 把左侧账号拖到文件夹即可归类；一个账号可以属于多个分组
        </div>
      </div>
    </div>

    <!-- 业务分组管理弹窗 -->
    <el-dialog
      v-model="showGroupDialog"
      title="分组管理"
      width="540px"
      append-to-body
      destroy-on-close
    >
      <div class="group-dialog-body">
        <!-- 新建分组 -->
        <div class="gd-create-row">
          <el-input
            v-model="newGroupName"
            placeholder="新分组名称，如「出海三人组」"
            size="default"
            clearable
            @keyup.enter="handleCreateGroup"
          />
          <el-button type="primary" @click="handleCreateGroup">+ 新建</el-button>
        </div>

        <!-- 汇总 -->
        <div class="gd-summary">
          共 <b>{{ accountStore.groups.length }}</b> 个分组
          <span class="gd-dot">·</span>
          <b>{{ accountStore.accounts.length }}</b> 个账号
        </div>

        <!-- 分组列表 -->
        <div class="gd-list" v-if="accountStore.groups.length > 0">
          <div v-for="grp in accountStore.groups" :key="grp" class="gd-row">
            <FolderIcon :size="18" />

            <div class="gd-meta">
              <div class="gd-name">{{ grp }}</div>
              <div class="gd-sub">{{ groupPlatforms(grp) }}</div>
            </div>

            <span class="gd-count">{{ accountStore.groupCounts[grp] || 0 }} 个账号</span>

            <!-- 所有分组均可改名或删除 -->
            <el-dropdown
              trigger="click"
              placement="bottom-end"
              @command="(cmd: string) => handleGroupCommand(cmd, grp)"
            >
              <span class="gd-more" title="更多操作">
                <el-icon><MoreFilled /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">
                    <el-icon><EditPen /></el-icon>重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>删除分组
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="gd-empty" v-else>
          <FolderIcon :size="26" />
          <span>还没有自定义分组</span>
        </div>

        <div class="gd-tip">
          💡 分组用于「发布工作台」里批量勾选账号 —— 例如只发「出海三人组」的号
        </div>
      </div>

      <template #footer>
        <el-button @click="showGroupDialog = false">完成</el-button>
      </template>
    </el-dialog>

    <!-- 添加账号弹框 -->
    <el-dialog v-model="showAddAccountDialog" title="添加账号" width="560px" destroy-on-close>
      <div class="add-dlg-body">
        <div class="add-step-label">1. 选择平台</div>
        <div class="add-platform-grid">
          <div
            v-for="plat in platformList"
            :key="plat.id"
            class="add-plat-card"
            :class="{ on: addForm.platform === plat.id }"
            @click="addForm.platform = plat.id"
          >
            <span class="ap-name">{{ plat.name }}</span>
          </div>
        </div>

        <div class="add-step-label">2. 填写信息（可选）</div>
        <div class="add-form-row">
          <span class="af-label">账号备注名</span>
          <el-input v-model="addForm.alias" size="default" placeholder="留空则自动读取平台昵称" clearable />
        </div>
        <div class="add-form-row">
          <span class="af-label">分组</span>
          <el-select
            v-model="addForm.groups"
            multiple
            collapse-tags
            filterable
            allow-create
            clearable
            placeholder="可多选，留空则不分组"
            style="flex:1"
          >
            <el-option v-for="g in accountStore.groups" :key="g" :label="g" :value="g" />
          </el-select>
        </div>

        <div class="add-hint">💡 点下方按钮会打开浏览器，用手机扫码登录</div>
      </div>

      <template #footer>
        <el-button @click="showAddAccountDialog = false">取消</el-button>
        <el-button type="primary" :loading="addForm.loading" @click="handleAddAccountConfirm">
          🚀 打开浏览器扫码登录
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FolderIcon from '../components/common/FolderIcon.vue'
import { PLATFORMS, getPlatformConfig } from '../config/platforms'
import { useAccountStore, AccountItem } from '../stores/accountStore'
import { LoginAccountWithAppWindow, StopTaskById } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'
import {
  Plus, Search, Delete, Monitor, ArrowDown, ArrowLeft,
  ArrowRight, FolderAdd, UserFilled, Loading, Check,
  CircleClose, Refresh, RefreshRight, CircleCheck, Compass,
  MoreFilled, EditPen, Setting, Select
} from '@element-plus/icons-vue'

const accountStore = useAccountStore()

// 浏览器标签页结构定义 (单面板模式：只保留一个标签页)
interface BrowserTab {
  id: string
  type: 'account' | 'new'
  title: string
  platform: string
  account: string
  url: string
  accountItem?: AccountItem
  isSessionActive: boolean
  isStartingSession: boolean
  taskId: string
  sessionStatusText: string
  /** 接入向导里选的分组（选填，可多选） */
  pendingGroups?: string[]
}

const openTabs = ref<BrowserTab[]>([])
const activeTabId = ref<string>('')

const currentPlatformFilter = ref('all')
const currentGroupFilter = ref('all')
const searchKeyword = ref('')

/** 只看"需重新登录"的账号 */
const filterOnlyInvalidFlag = ref(false)

const newTabSelectedPlatform = ref('douyin')
const newTabAccountAlias = ref('')
/** 接入向导里选择的分组（选填，可多选） */
const newTabGroups = ref<string[]>([])

const showGroupDialog = ref(false)
const newGroupName = ref('')

/** 添加账号弹框 */
const showAddAccountDialog = ref(false)
const addForm = reactive({
  platform: 'douyin',
  alias: '',
  groups: [] as string[],
  loading: false
})

/** 是否收起右侧浏览器 */
const browserCollapsed = ref(false)

// 正在接入中的新账号临时状态
interface PendingAccountLogin {
  id: string
  platform: string
  alias?: string
  statusText: string
  startTime: number
}
const pendingAccountLogins = ref<PendingAccountLogin[]>([])

const platformList = computed(() => PLATFORMS)
const availablePlatforms = computed(() => {
  const ids = new Set<string>([...PLATFORMS.map(p => p.id), ...accountStore.accounts.map(a => a.platform)])
  return [...ids].map(id => getPlatformConfig(id))
})

// 当前激活的标签页
const currentActiveTab = computed<BrowserTab | null>(() => {
  return openTabs.value.find(t => t.id === activeTabId.value) || openTabs.value[0] || null
})

// 筛选后的左侧账号列表
const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(acc => {
    if (filterOnlyInvalidFlag.value) {
      if (!acc.checked || acc.isValid) return false
    }
    if (currentPlatformFilter.value !== 'all' && acc.platform !== currentPlatformFilter.value) {
      return false
    }
    if (currentGroupFilter.value !== 'all' && !acc.groups?.includes(currentGroupFilter.value)) {
      return false
    }
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      const accMatch = acc.account.toLowerCase().includes(kw)
      const nickMatch = acc.nickname ? acc.nickname.toLowerCase().includes(kw) : false
      const uidMatch = acc.finderUid ? acc.finderUid.toLowerCase().includes(kw) : false
      const platMatch = acc.platform.toLowerCase().includes(kw)
      return accMatch || nickMatch || uidMatch || platMatch
    }
    return true
  })
})

/** 需重新登录的账号数（已检测且失效） */
const invalidCount = computed(() =>
  accountStore.accounts.filter(a => a.checked && !a.isValid).length
)

/** 点汇总条上的"N 个需重新登录" → 只筛失效账号 */
function filterOnlyInvalid() {
  currentPlatformFilter.value = 'all'
  currentGroupFilter.value = 'all'
  filterOnlyInvalidFlag.value = true
}

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

/** 平台简称 */
function platShort(pid: string): string {
  const map: Record<string, string> = {
    douyin: '抖音',
    xiaohongshu: '小红书',
    kuaishou: '快手',
    shipinhao: '视频号',
    bilibili: 'B站',
    youtube: 'YouTube',
    baijiahao: '百家号',
    weibo: '微博',
    alipay: '生活号'
  }
  return map[pid] || getPlatformStyle(pid)?.name?.slice(0, 3) || pid
}

const getPlatformCreatorUrl = (platform: string) => {
  switch (platform) {
    case 'douyin': return 'https://creator.douyin.com/'
    case 'xiaohongshu': return 'https://creator.xiaohongshu.com/'
    case 'kuaishou': return 'https://cp.kuaishou.com/'
    case 'tencent': return 'https://channels.weixin.qq.com/'
    case 'bilibili': return 'https://member.bilibili.com/'
    case 'weibo': return 'https://weibo.com/'
    case 'baijiahao': return 'https://baijiahao.baidu.com/'
    default: return 'https://creator.platform.com/'
  }
}

const getAccountAvatarText = (acc?: AccountItem | null, fallbackName: string = '新') => {
  if (!acc) {
    if (fallbackName && fallbackName.trim()) {
      return fallbackName.trim().slice(0, 1).toUpperCase()
    }
    return '新'
  }
  const name = acc.nickname || acc.account || fallbackName || 'U'
  return name.trim().slice(0, 1).toUpperCase()
}

/** 上次检测时间的友好显示 */
function fmtCheckedAt(ts?: number): string {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()

  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')

  if (sameDay) return `今天 ${hh}:${mm} 检测`

  const days = Math.floor((now.getTime() - ts) / 86400000)
  if (days === 1) return `昨天 ${hh}:${mm} 检测`
  if (days < 7) return `${days} 天前检测`

  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mo}-${dd} 检测`
}

/** 检测时间是否已陈旧（超过 7 天）—— 用于变橙色提醒 */
function isStaleCheck(ts?: number): boolean {
  if (!ts) return false
  return Date.now() - ts > 7 * 86400000
}

/** 分组 → 该组包含的平台名（最多 3 个） */
function groupPlatforms(grp: string): string {
  const names = accountStore.accounts
    .filter(a => a.groups?.includes(grp))
    .map(a => getPlatformConfig(a.platform).name)
  const uniq = Array.from(new Set(names))
  if (uniq.length === 0) return '暂无账号'
  return uniq.slice(0, 3).join(' · ') + (uniq.length > 3 ? ` 等 ${uniq.length} 个平台` : '')
}

// 激活某个标签页
const activateTab = (tabId: string) => {
  activeTabId.value = tabId
}

/* ───────── 拖拽归类 ───────── */
const draggingAccounts = ref<AccountItem[]>([])
const dropTargetGroup = ref('')

function isDragging(acc: AccountItem) {
  return draggingAccounts.value.some(a => a.platform === acc.platform && a.account === acc.account)
}

function onDragStart(acc: AccountItem, e: DragEvent) {
  const useChecked = checkedAccounts.value.length > 0 && checkedAccounts.value.includes(accKey(acc))
  draggingAccounts.value = useChecked ? checkedAccountItems.value.slice() : [acc]
  e.dataTransfer?.setData('text/plain', String(draggingAccounts.value.length))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy'
}

function onDragEnd() {
  draggingAccounts.value = []
  dropTargetGroup.value = ''
}

function onDragOverGroup(grp: string) {
  if (dropTargetGroup.value !== grp) dropTargetGroup.value = grp
}

function onDragLeaveGroup(grp: string) {
  if (dropTargetGroup.value === grp) dropTargetGroup.value = ''
}

function onDropToGroup(grp: string) {
  const list = draggingAccounts.value
  if (list.length > 0) {
    accountStore.addAccountsToGroup(
      list.map(a => ({ platform: a.platform, account: a.account })),
      grp
    )
    ElMessage.success(`已将 ${list.length} 个账号加入「${grp}」`)
  }
  onDragEnd()
}

/* ───────── 文件夹展开 ───────── */
const expandedGroups = ref<string[]>([])

function toggleGroupExpand(grp: string) {
  const i = expandedGroups.value.indexOf(grp)
  if (i >= 0) expandedGroups.value.splice(i, 1)
  else expandedGroups.value.push(grp)
}

function groupMembers(grp: string): AccountItem[] {
  return accountStore.accounts.filter(a => a.groups?.includes(grp))
}

/** 从分组移除单个账号 */
function handleRemoveFromGroup(acc: AccountItem, grp: string) {
  accountStore.removeFromGroup(acc.platform, acc.account, grp)
  ElMessage.success(`已从「${grp}」移除`)
}

/** ⋯ 菜单 */
function handleGroupCommand(cmd: string, grp: string) {
  if (cmd === 'rename') handleRenameGroup(grp)
  else if (cmd === 'delete') handleDeleteGroup(grp)
  else if (cmd === 'selectAll') {
    groupMembers(grp).forEach(a => {
      const k = accKey(a)
      if (!checkedAccounts.value.includes(k)) checkedAccounts.value.push(k)
    })
    ElMessage.success(`已选中「${grp}」的 ${accountStore.groupCounts[grp] || 0} 个账号`)
  }
}

/** 右侧面板内联新建分组 */
function handleCreateGroupInline() {
  const name = newGroupName.value.trim()
  if (!name) { ElMessage.warning('请输入分组名称'); return }
  if (accountStore.groups.includes(name)) { ElMessage.warning('已存在同名分组'); return }
  accountStore.addGroup(name)
  newGroupName.value = ''
  ElMessage.success(`已创建分组「${name}」`)
}

/** 为指定账号打开浏览器登录 */
async function openBrowserForAccount(acc: AccountItem) {
  openAccountTab(acc)
  const tab = currentActiveTab.value
  if (tab) await startAppWindowForTab(tab)
}

// 左侧点击用户卡片：在右侧单账号面板中显示该账号（单面板模式：切换账号即替换）
const openAccountTab = (acc: AccountItem) => {
  const tabId = `${acc.platform}:${acc.account}`

  // 单面板模式：始终只保留一个账号标签，切换账号即替换
  const existing = openTabs.value.find(t => t.id === tabId)
  if (existing) {
    existing.accountItem = acc
    existing.title = `${getPlatformConfig(acc.platform).name} - ${acc.nickname || acc.account}`
    openTabs.value = [existing]
    activeTabId.value = tabId
    return
  }

  openTabs.value = [{
    id: tabId,
    type: 'account',
    title: `${getPlatformConfig(acc.platform).name} - ${acc.nickname || acc.account}`,
    platform: acc.platform,
    account: acc.account,
    url: getPlatformCreatorUrl(acc.platform),
    accountItem: acc,
    isSessionActive: false,
    isStartingSession: false,
    taskId: `login_${acc.platform}_${acc.account}`,
    sessionStatusText: '等待打开浏览器...'
  }]
  activeTabId.value = tabId
}

// 打开"新建标签页 / 接入新账号"（单面板模式）
const openNewTab = () => {
  const newTabId = `new_tab_${Date.now()}`
  openTabs.value = [{
    id: newTabId,
    type: 'new',
    title: '添加账号',
    platform: newTabSelectedPlatform.value,
    account: '',
    url: 'sau://new-tab',
    isSessionActive: false,
    isStartingSession: false,
    taskId: `login_new_${Date.now()}`,
    sessionStatusText: '就绪'
  }]
  activeTabId.value = newTabId
}

/** 打开添加账号弹框 */
function openAddAccountDialog() {
  addForm.platform = 'douyin'
  addForm.alias = ''
  addForm.groups = []
  addForm.loading = false
  showAddAccountDialog.value = true
}

/** 弹框确认 → 走原有登录链路 */
async function handleAddAccountConfirm() {
  addForm.loading = true
  try {
    openNewTab()
    const tab = currentActiveTab.value
    if (!tab) return
    tab.platform = addForm.platform
    tab.account = addForm.alias.trim() || 'auto'
    tab.pendingGroups = addForm.groups.slice()
    showAddAccountDialog.value = false
    await startAppWindowForTab(tab)
  } finally {
    addForm.loading = false
  }
}

// 关闭标签页
const closeTab = async (tabId: string) => {
  const idx = openTabs.value.findIndex(t => t.id === tabId)
  if (idx !== -1) {
    const tabToClose = openTabs.value[idx]
    if (tabToClose.isSessionActive && tabToClose.taskId) {
      await StopTaskById(tabToClose.taskId)
    }
    openTabs.value.splice(idx, 1)
    if (activeTabId.value === tabId) {
      if (openTabs.value.length > 0) {
        const nextTab = openTabs.value[Math.max(0, idx - 1)]
        activeTabId.value = nextTab.id
      } else {
        openNewTab()
      }
    }
  }
}

// 为指定标签页拉起原生 Chrome App 沉浸式真机视窗
const startAppWindowForTab = async (tab: BrowserTab) => {
  const platform = tab.platform
  const account = tab.account || 'auto'
  tab.taskId = `login_${platform}_${account}`
  tab.isSessionActive = true
  tab.isStartingSession = true
  if (tab.accountItem) {
    tab.accountItem.isSyncing = true
  } else {
    // 初次新增账号：立即在左侧联系人列表展示接入中状态卡片
    pendingAccountLogins.value = pendingAccountLogins.value.filter(p => p.platform !== platform)
    pendingAccountLogins.value.push({
      id: `pending_${platform}_${Date.now()}`,
      platform,
      alias: account === 'auto' ? '' : account,
      statusText: '浏览器已打开，等待扫码授权...',
      startTime: Date.now()
    })
  }
  tab.sessionStatusText = '正在打开浏览器...'

  try {
    const res = await LoginAccountWithAppWindow(platform, account)
    if (res && res.success && res.account && res.account !== 'auto') {
      tab.sessionStatusText = `🎉 账号 [${res.nickname || res.account}] 登录状态已保存`
      ElMessage.success(`账号 [${res.nickname || res.account}] 登录状态已保存`)
      const savedAcc = accountStore.saveLoggedInAccount(platform, res.account, res.nickname, res.finderUid, true, res.avatar)
      pendingAccountLogins.value = pendingAccountLogins.value.filter(p => p.platform !== platform)
      if (savedAcc) {
        const wantGroups = (tab.pendingGroups || []).filter((g: string) => !!g.trim())
        wantGroups.forEach((g: string) => {
          if (!accountStore.groups.includes(g)) accountStore.addGroup(g)
          accountStore.addToGroup(platform, savedAcc.account, g)
        })
        tab.accountItem = savedAcc
        tab.account = savedAcc.account
        tab.type = 'account'
        tab.id = `${savedAcc.platform}:${savedAcc.account}`
        tab.title = `${getPlatformConfig(savedAcc.platform).name} - ${savedAcc.nickname || savedAcc.account}`
      }
    } else {
      const finishMsg = res?.msg || '操作完成'
      tab.sessionStatusText = `操作已完成: ${finishMsg}`
      if (account === 'auto') {
        ElMessage.info('未完成扫码登录，您可以随时点击重新打开浏览器')
      } else {
        if (tab.accountItem) {
          tab.accountItem.checked = true
        }
        ElMessage.info(`操作已完成: ${finishMsg}`)
      }
    }
  } catch (err: any) {
    const errStr = err?.message || String(err)
    if (!errStr.includes('手动中止') && !errStr.includes('signal') && !errStr.includes('killed')) {
      tab.sessionStatusText = `操作异常: ${errStr}`
      const cleanMsg = errStr.startsWith('打开浏览器失败') ? errStr : `打开浏览器失败：${errStr}`
      ElMessage.error({ message: cleanMsg, duration: 6000 })
    }
  } finally {
    pendingAccountLogins.value = pendingAccountLogins.value.filter(p => p.platform !== platform)
    tab.isStartingSession = false
    tab.isSessionActive = false
    if (tab.accountItem) {
      tab.accountItem.isSyncing = false
      tab.accountItem.loading = false
    }
    await accountStore.fetchAccounts()
    if (tab.account && tab.account !== 'auto') {
      const targetAcc = accountStore.accounts.find(a => a.platform === platform && a.account === tab.account)
      if (targetAcc) {
        tab.accountItem = targetAcc
        tab.type = 'account'
        tab.id = `${targetAcc.platform}:${targetAcc.account}`
        tab.title = `${getPlatformConfig(targetAcc.platform).name} - ${targetAcc.nickname || targetAcc.account}`
      }
    }
  }
}

// 新标签页中发起接入
const startNewTabLoginForTab = (tab: BrowserTab) => {
  tab.platform = newTabSelectedPlatform.value
  tab.account = newTabAccountAlias.value.trim() || 'auto'
  tab.pendingGroups = newTabGroups.value
  tab.url = getPlatformCreatorUrl(tab.platform)
  tab.title = `${getPlatformConfig(tab.platform).name} - ${tab.account === 'auto' ? '扫码接入' : tab.account}`
  startAppWindowForTab(tab)
}

// 停止指定标签页的会话
const stopSessionForTab = async (tab: BrowserTab) => {
  if (tab.taskId) {
    await StopTaskById(tab.taskId)
  }
  tab.isSessionActive = false
  tab.isStartingSession = false
  tab.sessionStatusText = '浏览器已手动关闭'
  ElMessage.info(`已关闭「${tab.title}」的浏览器`)
}

// 严格判断标签页是否真正处于同步或加载中
const isTabSyncing = (tab?: BrowserTab | null) => {
  if (!tab) return false
  if (tab.accountItem?.loading || tab.accountItem?.isSyncing) return true
  if (tab.isSessionActive && tab.isStartingSession) return true
  return false
}

/** 批量操作：账号唯一键 */
const accKey = (a: AccountItem) => `${a.platform}:${a.account}`

/** 批量勾选列表 */
const checkedAccounts = ref<string[]>([])

function toggleAccountCheck(acc: AccountItem, on: boolean) {
  const k = accKey(acc)
  if (on) {
    if (!checkedAccounts.value.includes(k)) checkedAccounts.value.push(k)
  } else {
    checkedAccounts.value = checkedAccounts.value.filter(x => x !== k)
  }
}

/** 勾选对应的账号对象 */
const checkedAccountItems = computed(() =>
  accountStore.accounts.filter(a => checkedAccounts.value.includes(accKey(a)))
)

/** 批量检测登录状态 */
const batchChecking = ref(false)
async function handleBatchCheck() {
  if (batchChecking.value) return
  batchChecking.value = true
  const list = checkedAccountItems.value
  let ok = 0, bad = 0
  try {
    for (const acc of list) {
      try {
        await checkStatus(acc)
        if (acc.isValid) ok++; else bad++
      } catch { bad++ }
    }
    ElMessage.success(`检测完成：${ok} 个正常${bad ? `，${bad} 个需重新登录` : ''}`)
  } finally {
    batchChecking.value = false
  }
}

/** 批量加入分组 */
function handleBatchMove(groupName: string) {
  const list = checkedAccountItems.value
  accountStore.addAccountsToGroup(list.map(acc => ({ platform: acc.platform, account: acc.account })), groupName)
  ElMessage.success(`已将 ${list.length} 个账号加入「${groupName}」`)
  checkedAccounts.value = []
}

/** 批量删除账号 */
async function handleBatchDelete() {
  const list = checkedAccountItems.value
  if (list.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${list.length} 个账号？删除后需要重新扫码登录。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch { return }
  list.forEach(acc => accountStore.removeAccount(acc.platform, acc.account))
  ElMessage.success(`已删除 ${list.length} 个账号`)
  checkedAccounts.value = []
}

// 账号凭证检测
const checkStatus = async (acc: AccountItem) => {
  if (currentActiveTab.value) {
    currentActiveTab.value.isStartingSession = false
  }
  try {
    await accountStore.checkAccount(acc)
    if (currentActiveTab.value && currentActiveTab.value.type === 'account') {
      const latest = accountStore.accounts.find(a => a.platform === acc.platform && a.account === acc.account)
      if (latest) {
        currentActiveTab.value.accountItem = latest
      }
      currentActiveTab.value.isStartingSession = false
    }
    const displayName = acc.nickname || acc.account || '当前账号'
    if (acc.isValid) {
      ElMessage.success(`[${displayName}] 登录状态正常`)
    } else {
      ElMessage.warning(`[${displayName}] 登录已失效：${acc.msg || '请重新扫码登录'}`)
    }
  } catch (err: any) {
    ElMessage.error(`检测失败: ${err.message || err}`)
  } finally {
    acc.loading = false
    acc.isSyncing = false
    if (currentActiveTab.value) {
      currentActiveTab.value.isStartingSession = false
      if (currentActiveTab.value.accountItem) {
        currentActiveTab.value.accountItem.loading = false
        currentActiveTab.value.accountItem.isSyncing = false
      }
    }
  }
}

// 删除账号
const confirmDelete = (platform: string, account: string) => {
  const accItem = accountStore.accounts.find(a => a.platform === platform && a.account === account)
  const displayName = accItem?.nickname || account
  ElMessageBox.confirm(
    `确定要删除账号「${displayName}」吗？删除后需要重新扫码登录。`,
    '确认删除账号',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    const ok = await accountStore.removeAccount(platform, account)
    if (ok) {
      ElMessage.success('账号已删除，本机登录信息已清理')
      closeTab(`${platform}:${account}`)
    } else {
      ElMessage.error('本地登录文件删除失败，账号未移除，请检查文件权限后重试')
    }
  }).catch(() => {})
}

// 创建新业务分组
const handleCreateGroup = () => {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  accountStore.addGroup(newGroupName.value.trim())
  ElMessage.success(`已创建分组「${newGroupName.value.trim()}」`)
  newGroupName.value = ''
}

/** 卡片上"改分组"弹层里新建分组的输入 */
const newGroupNameForAccount = ref('')

/** 把账号加入分组（已在组内则移除） */
function assignGroup(acc: AccountItem, groupName: string) {
  accountStore.toggleAccountGroup(acc.platform, acc.account, groupName)
}

/** 新建分组并把当前账号放进去 */
function createGroupAndAssign(acc: AccountItem) {
  const name = newGroupNameForAccount.value.trim()
  if (!name) return
  accountStore.addGroup(name)
  assignGroup(acc, name)
  newGroupNameForAccount.value = ''
}

/** 重命名分组 */
async function handleRenameGroup(oldName: string) {
  try {
    const { value } = await ElMessageBox.prompt('输入新的分组名称', '重命名分组', {
      inputValue: oldName,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (v: string) => (!!v && v.trim().length > 0) || '名称不能为空'
    })
    const err = accountStore.renameGroup(oldName, value)
    if (err) ElMessage.warning(err)
    else ElMessage.success('已重命名')
  } catch { /* 取消 */ }
}

/** 删除分组（账号回落到默认分组） */
async function handleDeleteGroup(name: string) {
  const count = accountStore.groupCounts[name] || 0
  try {
    await ElMessageBox.confirm(
      count > 0
        ? `删除分组「${name}」后，组内 ${count} 个账号会从这个分组移除（账号不会被删除）。`
        : `确认删除空分组「${name}」？`,
      '确认删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch { return }

  accountStore.removeGroup(name)
  ElMessage.success(count > 0 ? `已删除分组，${count} 个账号已从该分组移除` : '已删除分组')
}

let unlistenLoginSuccess: (() => void) | null = null

// 初始化时：打开第一个账号标签页，若无账号则打开新标签页向导
onMounted(() => {
  if (accountStore.accounts.length > 0) {
    openAccountTab(accountStore.accounts[0])
  } else {
    openNewTab()
  }

  // 监听后端即时上报的登录成功事件
  try {
    unlistenLoginSuccess = EventsOn('sau-login-success', (evt: any) => {
      const platform = evt?.platform
      const realAccount = (evt?.account && evt.account !== 'auto') ? evt.account : (evt?.finderUid || '')
      if (!platform || !realAccount) return

      const updated = accountStore.saveLoggedInAccount(
        platform,
        realAccount,
        evt?.nickname,
        evt?.finderUid,
        true,
        evt?.avatar
      )

      pendingAccountLogins.value = pendingAccountLogins.value.filter(p => p.platform !== platform)

      const taskId = evt?.taskId
      const targetTab = openTabs.value.find(t =>
        (taskId && t.taskId === taskId) ||
        (t.platform === platform && (t.account === realAccount || t.account === 'auto'))
      )
      if (targetTab) {
        targetTab.sessionStatusText = `🟢 扫码成功 · 账号 [${evt?.nickname || realAccount}] 登录已就绪`
        targetTab.isStartingSession = false
        targetTab.isSessionActive = true
        targetTab.account = realAccount
        targetTab.type = 'account'
        targetTab.id = `${platform}:${realAccount}`
        if (updated) {
          targetTab.accountItem = updated
        }
        targetTab.title = `${getPlatformConfig(platform).name} - ${evt?.nickname || realAccount}`
      }

      ElMessage.success({
        message: `🎉 账号 [${evt?.nickname || realAccount}] 扫码成功，已实时同步至账号列表！`,
        duration: 4000
      })
    })
  } catch (err) {
    console.error('EventsOn sau-login-success failed:', err)
  }
})

onUnmounted(() => {
  if (typeof unlistenLoginSuccess === 'function') {
    unlistenLoginSuccess()
  }
})

// 监听账号列表更新，同步更新标签页中 accountItem 的引用
watch(() => accountStore.accounts, (newAccounts) => {
  for (const tab of openTabs.value) {
    if (tab.type === 'account') {
      const found = newAccounts.find(a => `${a.platform}:${a.account}` === tab.id)
      if (found) {
        tab.accountItem = found
        tab.title = `${getPlatformConfig(found.platform).name} - ${found.nickname || found.account}`
      }
    }
  }
  if (openTabs.value.length === 0) {
    if (newAccounts.length > 0) {
      openAccountTab(newAccounts[0])
    } else {
      openNewTab()
    }
  }
})
</script>

<style scoped>
/* 一体化浏览器工作空间布局：顶部汇总条 + 下方左右两栏 */
.account-browser-workspace {
  display: flex;
  flex-direction: column;
  gap: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* 左右两栏容器（横向排列） */
.accounts-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 14px;
  overflow: hidden;
  padding: 14px 14px 14px 14px;
  box-sizing: border-box;
}

/* 顶部汇总条 */
.account-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.sum-left { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
.sum-total { color: var(--text-main); font-weight: 600; }
.sum-sep { opacity: .4; }
.sum-invalid {
  /* 完全重置原生 button 外观，呈文字链接样式 */
  all: unset;
  display: inline;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--status-danger);
}
.sum-invalid:hover { text-decoration: underline; }
.sum-invalid.zero { color: var(--status-success); cursor: default; }
.sum-invalid:disabled { cursor: default; }
.sum-right { display: flex; align-items: center; gap: 8px; }

.acc-check {
  margin-right: 6px;
  flex-shrink: 0;
}

.sum-batch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
  margin-left: 4px;
  border-left: 1px solid var(--border-subtle);
}

.batch-count {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--primary-color);
  white-space: nowrap;
}

/* 👈 左侧：账号列表侧边栏 */
.account-sidebar-pane {
  width: 420px;
  min-width: 420px;
  max-width: 420px;
  height: auto;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* 收起浏览器时左侧撑满全宽，右边留空白 */
.accounts-body.collapsed .account-sidebar-pane {
  flex: 1;
  max-width: none;
}

.sidebar-header-section {
  padding: 12px 14px 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-detail);
}

.sidebar-title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-with-pill {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text-main);
}

.account-count-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary-color);
}

.add-account-gradient-btn {
  background: var(--primary-color) !important;
  border: none !important;
  font-weight: 700;
}

.sidebar-search-box {
  width: 100%;
}

.sidebar-filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 联系人滚动列表 */
.sidebar-contact-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.contact-empty-state {
  padding: 40px 14px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}

.contact-empty-state .empty-icon {
  font-size: 36px;
  color: var(--text-disabled);
}

.contact-empty-state .empty-title {
  font-size: 13px;
  margin: 0;
  color: var(--text-secondary);
}

/* 单个账号联系人项 */
.contact-card-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  position: relative;
}

.contact-card-item:hover {
  background: var(--bg-detail);
}

.contact-card-item.is-active {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.35);
}

.contact-card-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 4px 4px 0;
  background: var(--primary-color);
  box-shadow: 0 0 8px var(--primary-color);
}

.contact-card-item.is-pending-login {
  background: rgba(99, 102, 241, 0.08);
  border: 1px dashed rgba(99, 102, 241, 0.4);
  animation: pendingPulse 2s ease-in-out infinite;
}

@keyframes pendingPulse {
  0%, 100% { opacity: 0.92; }
  50% { opacity: 1; border-color: rgba(99, 102, 241, 0.8); }
}

.avatar-pending-spinner {
  font-size: 20px;
  color: #ffffff;
}

.pending-title {
  color: var(--primary-color, #6366f1) !important;
  font-weight: 600;
}

/* 头像微模块 */
.contact-avatar-wrapper {
  position: relative;
  width: 44px;
  height: 44px;
  min-width: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
}

.contact-real-avatar,
.appmode-real-avatar,
.standby-real-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.avatar-char {
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1;
}

/* 文本信息 */
.contact-meta-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.contact-first-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.contact-name-text {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plat-chip {
  display: inline-block;
  padding: 0 5px;
  margin-right: 5px;
  border-radius: 4px;
  font-size: 10px;
  line-height: 15px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  vertical-align: 1px;
  white-space: nowrap;
}
.contact-card-item.is-active .plat-chip {
  color: var(--primary-color);
  border-color: rgba(79, 70, 229, 0.32);
}

.contact-second-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.contact-group-name {
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.contact-status-label {
  font-size: 11px;
  color: var(--text-muted);
}

.contact-status-label.status-ok {
  color: #10b981;
  font-weight: 600;
}

.contact-status-label.status-err {
  color: #ef4444;
  font-weight: 600;
}

.contact-status-label.status-syncing {
  color: #f59e0b;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

/* 上次检测时间（卡片第二行） */
.contact-checked-at {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--text-muted);
  opacity: .72;
  white-space: nowrap;
  flex-shrink: 0;
}
/* 超过 7 天未检测 → 橙色提醒 */
.contact-checked-at.stale {
  color: var(--status-warning, #d97706);
  opacity: .95;
  font-weight: 600;
}

/* 👉 右侧：分组面板 */
.groups-pane {
  width: 340px; min-width: 340px; max-width: 340px;
  display: flex; flex-direction: column;
  min-height: 0;
  border-left: 1px solid var(--border-subtle);
  padding-left: 14px;
}
.gsp-head { display: flex; align-items: center; gap: 7px; padding: 2px 0 10px; flex-shrink: 0; }
.gsp-title { font-size: 13px; font-weight: 700; color: var(--text-main); }
.gsp-count { font-size: 11px; color: var(--text-muted); }
.gsp-spacer { flex: 1; }

.gsp-create { display: flex; gap: 7px; margin-bottom: 11px; flex-shrink: 0; }

.gsp-list { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }

.folder {
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  margin-bottom: 7px;
  overflow: hidden;
  transition: border-color .15s, background-color .15s;
}
.folder.drop {
  border: 2px dashed var(--primary-color);
  background: rgba(79, 70, 229, .07);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, .10);
}
.folder-head {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 11px; cursor: pointer;
}
.folder-head:hover { background: rgba(79,70,229,.04); }
.f-arrow { font-size: 11px; color: var(--text-muted); transition: transform .18s; }
.f-arrow.open { transform: rotate(90deg); }
.f-name { font-size: 12.5px; font-weight: 600; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.f-count {
  margin-left: auto; font-size: 10.5px; font-weight: 700;
  padding: 2px 8px; border-radius: 20px;
  background: rgba(79,70,229,.10); color: var(--primary-color);
}
.f-more {
  width: 22px; height: 22px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); opacity: .5; flex-shrink: 0;
}
.f-more:hover { background: rgba(0,0,0,.06); opacity: 1; }

.f-drop-hint {
  font-size: 11.5px; font-weight: 700; color: var(--primary-color);
  padding: 0 11px 9px;
}
.f-members { border-top: 1px solid var(--border-subtle); padding: 4px 6px; }
.f-member {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 7px; border-radius: 6px;
  font-size: 11.5px; cursor: pointer;
}
.f-member:hover { background: rgba(79,70,229,.06); }
.fm-plat { font-size: 10px; padding: 1px 5px; border-radius: 4px; background: rgba(0,0,0,.06); }
.fm-nick { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fm-status { margin-left: auto; font-size: 11px; }
.fm-x { opacity: .35; font-size: 11px; padding: 0 3px; }
.fm-x:hover { opacity: 1; color: var(--status-danger); }
.f-empty { padding: 10px; font-size: 11px; color: var(--text-muted); text-align: center; }

.gsp-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 34px 0; color: var(--text-muted); font-size: 12px;
}
.gsp-empty-sub { font-size: 11px; opacity: .7; }

.gsp-tip { font-size: 11px; color: var(--text-muted); line-height: 1.6; padding: 10px 0 2px; flex-shrink: 0; }

/* ── 账号卡片 ── */
.acc-group-tags { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 2px; }
.acc-gtag {
  font-size: 9.5px; padding: 1px 6px; border-radius: 20px;
  background: rgba(79,70,229,.09); color: var(--primary-color);
}
.acc-acts { margin-left: auto; display: flex; gap: 6px; flex-shrink: 0; }
.acc-act { font-size: 13px; color: var(--text-muted); cursor: pointer; opacity: .55; }
.acc-act:hover { opacity: 1; color: var(--primary-color); }
.acc-act.spinning { animation: spin 1s linear infinite; opacity: 1; }
@keyframes spin { to { transform: rotate(360deg); } }
.contact-item.dragging { opacity: .4; }

/* ── 添加账号弹框 ── */
.add-dlg-body { display: flex; flex-direction: column; gap: 12px; }
.add-step-label { font-size: 12px; font-weight: 700; color: var(--text-main); }
.add-platform-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.add-plat-card {
  border: 1px solid var(--border-subtle); border-radius: 8px;
  padding: 10px; text-align: center; font-size: 12px; cursor: pointer;
  transition: all .15s;
}
.add-plat-card:hover { border-color: var(--primary-color); }
.add-plat-card.on {
  border-color: var(--primary-color);
  background: rgba(79,70,229,.08);
  color: var(--primary-color); font-weight: 700;
}
.add-form-row { display: flex; align-items: center; gap: 9px; }
.af-label { font-size: 12px; color: var(--text-muted); min-width: 70px; }
.add-hint { font-size: 11.5px; color: var(--text-muted); }

/* ── 分组管理弹窗 ── */
.group-dialog-body { display: flex; flex-direction: column; }

/* 新建行 */
.gd-create-row {
  display: flex; gap: 9px; align-items: center;
  margin-bottom: 14px;
}

/* 汇总行 */
.gd-summary {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-bottom: 9px;
  padding-left: 2px;
}
.gd-summary b { color: var(--text-main); font-weight: 700; }
.gd-dot { opacity: .4; margin: 0 3px; }

/* 分组列表 */
.gd-list {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
}
.gd-row {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 13px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background-color .15s;
}
.gd-row:last-child { border-bottom: none; }
.gd-row:hover { background: rgba(79, 70, 229, .05); }

.gd-meta { min-width: 0; flex: 1; }
.gd-name {
  font-size: 12.5px; font-weight: 600; color: var(--text-main);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.gd-sub {
  font-size: 10.5px; color: var(--text-muted);
  margin-top: 1px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.gd-count {
  font-size: 11px; font-weight: 700;
  padding: 2px 9px; border-radius: 20px;
  background: rgba(79, 70, 229, .10);
  color: var(--primary-color);
  white-space: nowrap; flex-shrink: 0;
}

.gd-more {
  width: 24px; height: 24px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted);
  cursor: pointer;
  opacity: .55;
  flex-shrink: 0;
  transition: all .15s;
}
.gd-more:hover {
  background: rgba(128, 128, 128, .12);
  opacity: 1;
  color: var(--text-main);
}

/* 空状态 */
.gd-empty {
  display: flex; flex-direction: column; align-items: center; gap: 9px;
  padding: 30px 0;
  color: var(--text-muted); font-size: 12px;
}

/* 底部提示 */
.gd-tip {
  margin-top: 13px;
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.65;
}
</style>
