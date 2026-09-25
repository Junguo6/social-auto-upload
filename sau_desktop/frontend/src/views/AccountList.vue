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
            <el-icon><FolderOpened /></el-icon><span>移动到分组</span>
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
        <el-button type="primary" @click="openNewTab">
          <el-icon><Plus /></el-icon>
          <span>添加账号</span>
        </el-button>
        <el-button plain @click="showGroupDialog = true">
          <el-icon><FolderOpened /></el-icon>
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
            :class="{ 'is-active': activeTabId === `${acc.platform}:${acc.account}` }"
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
                      #{{ acc.group || DEFAULT_GROUP }}
                      <el-icon class="grp-caret"><ArrowDown /></el-icon>
                    </span>
                  </template>

                  <div class="group-picker">
                    <div class="gp-title">移动到分组</div>
                    <div
                      v-for="grp in accountStore.groups"
                      :key="grp"
                      class="gp-item"
                      :class="{ on: (acc.group || DEFAULT_GROUP) === grp }"
                      @click="assignGroup(acc, grp)"
                    >
                      <el-icon v-if="(acc.group || DEFAULT_GROUP) === grp" class="gp-check"><Check /></el-icon>
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
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 👉 右侧：单账号面板 -->
      <div class="browser-window-pane" v-show="!browserCollapsed">
        <!-- 面板标题行（替代原来的浏览器工具栏） -->
        <div class="panel-head">
          <div class="ph-left">
            <span class="ph-title">
              <template v-if="currentActiveTab?.type === 'new'">添加账号</template>
              <template v-else-if="currentActiveTab?.accountItem">
                {{ currentActiveTab.accountItem.nickname || currentActiveTab.accountItem.account }}
              </template>
              <template v-else>账号详情</template>
            </span>
            <span
              v-if="currentActiveTab?.type === 'account' && currentActiveTab.accountItem"
              class="ph-status"
              :class="currentActiveTab.accountItem.isValid ? 'ok' : 'bad'"
            >
              {{ currentActiveTab.accountItem.isValid ? '✅ 登录正常' : '⚠️ 登录已失效' }}
            </span>
          </div>

          <div class="ph-right">
            <!-- 账号操作按钮 -->
            <template v-if="currentActiveTab?.type === 'account' && currentActiveTab.accountItem">
              <el-button size="small" plain :loading="currentActiveTab.accountItem.loading" @click="checkStatus(currentActiveTab.accountItem)">
                <el-icon><Search /></el-icon><span>检测登录状态</span>
              </el-button>
              <el-button size="small" type="primary" plain :loading="currentActiveTab.isStartingSession" @click="startAppWindowForTab(currentActiveTab)">
                <el-icon><Monitor /></el-icon>
                <span>{{ currentActiveTab.isSessionActive ? '重新打开浏览器' : '打开浏览器登录' }}</span>
              </el-button>
              <el-button v-if="currentActiveTab.isSessionActive" size="small" type="danger" plain @click="stopSessionForTab(currentActiveTab)">
                <el-icon><CircleClose /></el-icon><span>关闭浏览器</span>
              </el-button>
            </template>

            <!-- 收起 / 展开 -->
            <el-tooltip :content="browserCollapsed ? '展开' : '收起'" placement="bottom">
              <el-button size="small" text @click="browserCollapsed = !browserCollapsed">
                <el-icon><ArrowRight v-if="browserCollapsed" /><ArrowLeft v-else /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <!-- 面板内容区 -->
        <div class="browser-viewport-stage">
          <div
            v-for="tab in openTabs"
            :key="tab.id"
            v-show="activeTabId === tab.id"
            class="tab-viewport-container"
          >
            <!-- A. 处于会话中 -->
            <template v-if="tab.isSessionActive">
              <div class="browser-appmode-hub">
                <div class="appmode-card">
                  <div class="appmode-header">
                    <div class="appmode-badge-live">
                      <span class="live-pulse-dot"></span>
                      <span>浏览器已打开</span>
                    </div>
                  </div>

                  <div class="appmode-avatar-box" :style="{ background: getPlatformStyle(tab.platform).gradient }">
                    <img
                      v-if="tab.accountItem?.avatar && !tab.accountItem?.avatarLoadFailed"
                      :src="tab.accountItem.avatar"
                      class="appmode-real-avatar"
                      referrerpolicy="no-referrer"
                      @error="tab.accountItem ? tab.accountItem.avatarLoadFailed = true : null"
                      :alt="tab.accountItem?.nickname || tab.accountItem?.account || tab.title"
                    />
                    <span v-else class="avatar-char">{{ getAccountAvatarText(tab.accountItem, tab.account || getPlatformConfig(tab.platform).name) }}</span>
                    <span class="avatar-badge">
                      <el-icon><component :is="getPlatformStyle(tab.platform).icon" /></el-icon>
                    </span>
                  </div>

                  <h3 class="appmode-title">{{ tab.accountItem?.nickname || tab.accountItem?.account || tab.title }}</h3>
                  <p class="appmode-url">{{ tab.url }}</p>

                  <div class="appmode-guide-tip">
                    <el-icon><CircleCheck /></el-icon>
                    <span>浏览器窗口已为您展开在桌面上，您可以在里面扫码登录、使用键盘打字、拖拽上传文件。登录状态每 30 秒自动保存一次。</span>
                  </div>

                  <div class="appmode-actions">
                    <el-button
                      type="primary"
                      size="large"
                      class="focus-window-btn"
                      @click="startAppWindowForTab(tab)"
                    >
                      <el-icon><RefreshRight /></el-icon>
                      <span>重新打开窗口</span>
                    </el-button>

                    <el-button
                      type="danger"
                      size="large"
                      plain
                      class="stop-session-btn"
                      @click="stopSessionForTab(tab)"
                    >
                      <el-icon><CircleClose /></el-icon>
                      <span>关闭并保存登录状态</span>
                    </el-button>
                  </div>
                </div>
              </div>
            </template>

            <!-- B. 待机状态：账号就绪面板 -->
            <div v-else-if="tab.type === 'account' && tab.accountItem" class="browser-standby-hub">
              <div class="standby-card-content">
                <div class="standby-brand-avatar" :style="{ background: getPlatformStyle(tab.platform).gradient }">
                  <img
                    v-if="tab.accountItem.avatar && !tab.accountItem.avatarLoadFailed"
                    :src="tab.accountItem.avatar"
                    class="standby-real-avatar"
                    referrerpolicy="no-referrer"
                    @error="tab.accountItem.avatarLoadFailed = true"
                    :alt="tab.accountItem.nickname || tab.accountItem.account"
                  />
                  <span v-else class="avatar-huge-char">{{ getAccountAvatarText(tab.accountItem) }}</span>
                  <span class="brand-sub-badge">
                    <el-icon><component :is="getPlatformStyle(tab.platform).icon" /></el-icon>
                  </span>
                </div>

                <h2 class="standby-account-title">{{ tab.accountItem.nickname || tab.accountItem.account }}</h2>
                <div class="standby-meta-pills">
                  <el-tag size="default" :type="isTabSyncing(tab) ? 'warning' : (tab.accountItem.isValid ? 'success' : 'danger')" effect="dark" round>
                    <el-icon v-if="isTabSyncing(tab)" class="is-loading" style="margin-right: 4px;"><Loading /></el-icon>
                    <span>{{ isTabSyncing(tab) ? '正在检查登录状态…' : (tab.accountItem.isValid ? '✅ 登录状态正常' : '⚠️ 登录已失效，请重新扫码') }}</span>
                  </el-tag>
                  <el-tag size="default" type="info" round v-if="tab.accountItem.finderUid">
                    UID: {{ tab.accountItem.finderUid }}
                  </el-tag>
                  <el-tag size="default" type="warning" round>
                    分组：{{ tab.accountItem.group || DEFAULT_GROUP }}
                  </el-tag>
                </div>

                <p class="standby-intro-desc" v-if="tab.accountItem.isValid">
                  本账号登录状态健康，点击下方按钮即可直接在浏览器窗口打开创作者服务平台，享受清晰的画面与顺畅的交互。
                </p>
                <p class="standby-intro-desc warning-text" v-else>
                  当前账号登录已失效，点击下方按钮将打开浏览器窗口并呈现扫码页面，手机微信/抖音扫码即可无缝完成绑定更新。
                </p>

                <div class="standby-action-launch">
                  <el-button
                    type="primary"
                    class="launch-stream-large-btn"
                    size="large"
                    :loading="tab.isStartingSession"
                    @click="startAppWindowForTab(tab)"
                  >
                    <el-icon><Monitor /></el-icon>
                    <span>{{ tab.accountItem.isValid ? '🚀 打开浏览器窗口' : '🚀 打开浏览器扫码登录' }}</span>
                  </el-button>
                </div>
              </div>
            </div>

            <!-- C. 新标签页 / 快速接入向导 -->
            <div v-else class="browser-newtab-hub">
              <div class="newtab-content-box">
                <div class="newtab-logo-box">
                  <el-icon class="newtab-logo"><Compass /></el-icon>
                </div>
                <h2 class="newtab-heading">添加账号</h2>
                <p class="newtab-sub">选择要添加的平台，点下方按钮后会打开浏览器，用手机扫码登录即可</p>

                <!-- 平台选择卡片网格 -->
                <div class="newtab-platforms-grid">
                  <div
                    v-for="plat in platformList"
                    :key="plat.id"
                    class="newtab-platform-card"
                    :class="{ 'selected': newTabSelectedPlatform === plat.id }"
                    @click="newTabSelectedPlatform = plat.id"
                  >
                    <div class="card-plat-icon" :style="{ background: plat.gradient }">
                      <el-icon><component :is="plat.icon" /></el-icon>
                    </div>
                    <span class="card-plat-name">{{ plat.name }}</span>
                  </div>
                </div>

                <!-- 备注名 + 分组 + 启动按钮 -->
                <div class="newtab-launch-form">
                  <div class="form-row">
                    <span class="row-label">账号备注名</span>
                    <el-input
                      v-model="newTabAccountAlias"
                      placeholder="选填：留空则自动读取平台昵称"
                      size="default"
                      style="flex: 1;"
                      clearable
                    />
                  </div>

                  <div class="form-row">
                    <span class="row-label">分组</span>
                    <el-select
                      v-model="newTabGroup"
                      placeholder="选填：默认归入「默认分组」"
                      size="default"
                      style="flex: 1;"
                      filterable
                      allow-create
                      clearable
                      default-first-option
                    >
                      <el-option
                        v-for="g in accountStore.groups"
                        :key="g"
                        :label="g"
                        :value="g"
                      />
                    </el-select>
                  </div>

                  <div class="newtab-form-hint">
                    💡 分组用于在「发布工作台」里批量勾选账号；也可直接输入新名称创建分组
                  </div>

                  <div class="form-action-row">
                    <el-button
                      type="primary"
                      class="launch-stream-large-btn"
                      size="default"
                      :loading="tab.isStartingSession"
                      @click="startNewTabLoginForTab(tab)"
                    >
                      <el-icon><Monitor /></el-icon>
                      <span>🚀 打开浏览器扫码登录</span>
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 业务分组管理弹窗 -->
    <el-dialog
      v-model="showGroupDialog"
      title="分组管理"
      width="520px"
      append-to-body
      destroy-on-close
    >
      <div class="group-dialog-body">
        <div class="new-group-input">
          <el-input
            v-model="newGroupName"
            placeholder="输入新分组名称 (如: 探店组、科技出海组)"
            @keyup.enter="handleCreateGroup"
          >
            <template #append>
              <el-button @click="handleCreateGroup">创建</el-button>
            </template>
          </el-input>
        </div>

        <div class="group-list-box">
          <div class="group-list-title">现有分组：</div>
          <div class="group-rows">
            <div v-for="grp in accountStore.groups" :key="grp" class="group-row">
              <el-icon class="gr-ic"><FolderOpened /></el-icon>
              <span class="gr-name" :title="grp">{{ grp }}</span>
              <span class="gr-count">{{ accountStore.groupCounts[grp] || 0 }} 个账号</span>

              <template v-if="grp !== DEFAULT_GROUP">
                <el-button size="small" text @click="handleRenameGroup(grp)">改名</el-button>
                <el-button size="small" text type="danger" @click="handleDeleteGroup(grp)">删除</el-button>
              </template>
              <span v-else class="gr-lock" title="默认分组不可改名或删除">默认</span>
            </div>
          </div>

          <div class="group-dialog-tip">
            💡 分组用于「发布工作台」里快速筛选账号，例如只勾选「出海三人组」下的全部账号
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PLATFORMS, getPlatformConfig } from '../config/platforms'
import { useAccountStore, AccountItem, DEFAULT_GROUP } from '../stores/accountStore'
import { LoginAccountWithAppWindow, StopTaskById } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'

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
  /** 接入向导里选的分组，登录成功后用于给新账号归组 */
  pendingGroup?: string
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
/** 接入向导里选择的分组（选填） */
const newTabGroup = ref('')

const showGroupDialog = ref(false)
const newGroupName = ref('')

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
    if (currentGroupFilter.value !== 'all' && acc.group !== currentGroupFilter.value) {
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

// 激活某个标签页
const activateTab = (tabId: string) => {
  activeTabId.value = tabId
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
        const wantGroup = (tab.pendingGroup || '').trim()
        if (wantGroup) {
          if (!accountStore.groups.includes(wantGroup)) accountStore.addGroup(wantGroup)
          accountStore.updateAccountGroup(platform, savedAcc.account, wantGroup)
        }
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
  tab.pendingGroup = newTabGroup.value.trim()
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

/** 批量移动到分组 */
function handleBatchMove(groupName: string) {
  const list = checkedAccountItems.value
  list.forEach(acc => accountStore.updateAccountGroup(acc.platform, acc.account, groupName))
  ElMessage.success(`已将 ${list.length} 个账号移动到「${groupName}」`)
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

/** 把账号移到指定分组 */
function assignGroup(acc: AccountItem, groupName: string) {
  accountStore.updateAccountGroup(acc.platform, acc.account, groupName)
  ElMessage.success(`已移动到「${groupName}」`)
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
        ? `删除分组「${name}」后，组内 ${count} 个账号会移到「${DEFAULT_GROUP}」（账号不会被删除）。`
        : `确认删除空分组「${name}」？`,
      '确认删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch { return }

  const moved = accountStore.removeGroup(name)
  if (moved < 0) ElMessage.warning('默认分组不可删除')
  else ElMessage.success(moved > 0 ? `已删除分组，${moved} 个账号已移到默认分组` : '已删除分组')
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

/* 面板标题行（替代原来的浏览器工具栏） */
.panel-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.ph-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
.ph-title { font-size: 14px; font-weight: 700; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ph-status { font-size: 12px; font-weight: 600; white-space: nowrap; }
.ph-status.ok { color: var(--status-success); }
.ph-status.bad { color: var(--status-danger); }
.ph-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

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

/* 👉 右侧：单账号面板 */
.browser-window-pane {
  flex: 1;
  min-width: 0;
  height: auto;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* 收起浏览器时隐藏右侧面板 */
.accounts-body.collapsed .browser-window-pane {
  display: none;
}

/* 浏览器主内容区 */
.browser-viewport-stage {
  flex: 1;
  position: relative;
  background: var(--bg-app);
  overflow: hidden;
  display: flex;
}

.tab-viewport-container {
  width: 100%;
  height: 100%;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.live-canvas-fill {
  width: 100%;
  height: 100%;
}

/* 浏览器伴侣控制台样式 */
.browser-appmode-hub {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: radial-gradient(circle at 50% 30%, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
}

.appmode-card {
  max-width: 540px;
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.15);
  animation: fadeIn 0.3s ease;
}

.appmode-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.appmode-badge-live {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #10b981;
}

.live-pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 10px #10b981;
  animation: pulse 1.6s infinite;
}

.appmode-avatar-box {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 13px;
}

.appmode-title {
  margin: 0 0 6px 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--text-main);
}

.appmode-url {
  margin: 0 0 16px 0;
  font-size: 12px;
  color: var(--text-secondary);
  font-family: monospace;
  background: var(--bg-detail);
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.appmode-guide-tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  text-align: left;
  margin-bottom: 20px;
}

.appmode-guide-tip .el-icon {
  font-size: 16px;
  color: #10b981;
  margin-top: 2px;
  flex-shrink: 0;
}

.appmode-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  margin-bottom: 14px;
}

.focus-window-btn {
  flex: 1;
  background: var(--primary-color) !important;
  border: none !important;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.stop-session-btn {
  font-weight: 700;
}

/* 创作者中心就绪待机面板 */
.browser-standby-hub {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.standby-card-content {
  max-width: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.standby-brand-avatar {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25);
  border: 3px solid var(--bg-card);
}

.avatar-huge-char {
  font-size: 36px;
  font-weight: 800;
  color: #ffffff;
}

.brand-sub-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 13px;
}

.standby-account-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
}

.standby-meta-pills {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.standby-intro-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

.standby-intro-desc.warning-text {
  color: #ef4444;
  font-weight: 600;
}

.standby-action-launch {
  width: 100%;
  margin: 8px 0;
}

.launch-stream-large-btn {
  width: 100%;
  background: var(--primary-color) !important;
  border: none !important;
  font-weight: 800;
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.35);
}

.standby-feature-tags {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

/* 新标签页接入向导面板 */
.browser-newtab-hub {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.newtab-content-box {
  max-width: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.newtab-logo-box {
  width: 68px;
  height: 68px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.newtab-logo {
  font-size: 36px;
  color: var(--primary-color);
}

.newtab-heading {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
}

.newtab-sub {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

.newtab-platforms-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  width: 100%;
  margin: 6px 0;
}

.newtab-platform-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 8px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.newtab-platform-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.newtab-platform-card.selected {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.card-plat-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
}

.card-plat-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
}

.newtab-launch-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.row-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  min-width: 70px;
}

.newtab-form-hint {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.6;
  margin: 2px 0 4px;
  padding-left: 2px;
}
</style>
