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
    </div>

    <!-- 左右两栏 -->
    <div class="accounts-body" :class="{ 'collapsed': browserCollapsed }">
      <!-- 👈 左侧：账号列表侧边栏 -->
      <div class="account-sidebar-pane">
        <!-- 卡片标题行 -->
        <div class="pane-card-head">
          <span class="pch-title">账号列表</span>
          <span class="pch-badge">{{ accountStore.accounts.length }}</span>
          <span class="pch-spacer"></span>
          <el-button type="primary" size="small" @click="openAddAccountDialog">
            <el-icon><Plus /></el-icon><span>添加账号</span>
          </el-button>
        </div>

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

        <!-- 筛选 chips -->
        <div class="acc-chips">
          <span
            class="acc-chip"
            :class="{ on: !filterOnlyInvalidFlag && !filterUngrouped }"
            @click="filterOnlyInvalidFlag = false; filterUngrouped = false"
          >
            全部 <span class="chip-n">{{ accountStore.accounts.length }}</span>
          </span>

          <span
            class="acc-chip danger"
            :class="{ on: filterOnlyInvalidFlag, disabled: invalidCount === 0 }"
            @click="invalidCount > 0 && (filterOnlyInvalidFlag = true, filterUngrouped = false)"
          >
            需重新登录 <span class="chip-n">{{ invalidCount }}</span>
          </span>

          <span
            class="acc-chip warn"
            :class="{ on: filterUngrouped, disabled: ungroupedCount === 0 }"
            @click="ungroupedCount > 0 && (filterUngrouped = true, filterOnlyInvalidFlag = false)"
          >
            未分组 <span class="chip-n">{{ ungroupedCount }}</span>
          </span>
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
            :title="(acc.groups && acc.groups.length) ? '所属分组：' + acc.groups.join('、') : '未分组'"
            @mousedown="onCardMouseDown(acc, $event)"
            @click="onCardClick(acc)"
          >
            <!-- 左侧勾选热区：点这一整条都能切换勾选 -->
            <div
              class="acc-check-zone"
              :class="{ on: checkedAccounts.includes(accKey(acc)) }"
              @click.stop="toggleAccountCheck(acc, !checkedAccounts.includes(accKey(acc)))"
            >
              <el-checkbox
                class="acc-check"
                :model-value="checkedAccounts.includes(accKey(acc))"
                @click.stop
                @change="(v: any) => toggleAccountCheck(acc, !!v)"
              />
            </div>

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

            </div>
          </div>

          <!-- 底部操作提示（固定在卡片底部，不随列表滚动） -->
          <div class="pane-tip" v-if="accountStore.groups.length > 0">
            💡 拖拽账号到右侧分组即可归类（一个账号可属于多个分组）
          </div>
          <div class="pane-tip" v-else>
            💡 先在右侧新建一个分组，再把账号拖进去归类
          </div>
        </div>
      </div>

      <!-- 👉 右侧：分组（文件夹形式） -->
      <div class="groups-pane" v-show="!browserCollapsed">
        <!-- 卡片标题行 -->
        <div class="pane-card-head">
          <span class="pch-title">分组列表</span>
          <span class="pch-badge">{{ accountStore.groups.length }}</span>
          <span class="pch-spacer"></span>
          <el-button type="primary" size="small" @click="showGroupDialog = true">
            <el-icon><Plus /></el-icon>
            <span>新建分组</span>
          </el-button>
        </div>

        <!-- ═══ 视图 A：分组平铺网格 ═══ -->
        <div class="folder-grid" :class="{ dragging: dragState.active }" v-if="!openedGroup && accountStore.groups.length > 0">
          <div
            v-for="grp in accountStore.groups"
            :key="grp"
            class="fcell"
            :class="{
              hot: dragState.targetGroup === grp,
              pop: justDroppedGroup === grp,
              empty: (accountStore.groupCounts[grp] || 0) === 0
            }"
            :data-group="grp"
            @dblclick="openGroupDetail(grp)"
          >
            <!-- hover 显示：重命名 / 删除 -->
            <div class="fcell-actions" @click.stop @dblclick.stop @mousedown.stop>
              <span
                class="fcell-act"
                title="重命名"
                @click.stop="startRename(grp)"
              >
                <el-icon><EditPen /></el-icon>
              </span>
              <span
                class="fcell-act danger"
                :title="`删除分组「${grp}」`"
                @click.stop="handleDeleteGroup(grp)"
              >
                <el-icon><Delete /></el-icon>
              </span>
            </div>

            <FolderIcon :size="56" />

            <!-- 双击名字 → 就地重命名；双击其他地方 → 进入文件夹 -->
            <el-input
              v-if="renamingGroup === grp"
              ref="renameInputRef"
              v-model="renameDraft"
              size="small"
              class="fcell-rename"
              maxlength="20"
              @click.stop
              @dblclick.stop
              @mousedown.stop
              @keyup.enter="commitRename"
              @keyup.esc="cancelRename"
              @blur="commitRename"
            />
            <span
              v-else
              class="fcell-name"
              :title="grp"
              @dblclick.stop="startRename(grp)"
            >{{ grp }}</span>
            <span v-if="dragState.targetGroup === grp" class="drop-hint">
              松开加入 {{ dragState.accounts.length }} 个
            </span>
            <span v-else class="fcell-count">
              {{ accountStore.groupCounts[grp] || 0 }} 个账号
            </span>
          </div>
        </div>

        <div class="pane-tip" v-if="!openedGroup && accountStore.groups.length > 0">
          💡 双击图标进入查看 · 双击名称可重命名 · 也可把左侧账号拖到格子上归类
        </div>

        <!-- ═══ 视图 B：进入某个分组 ═══ -->
        <div
          class="group-detail"
          v-else-if="openedGroup"
          :class="{ droppable: dragState.active, hot: dragState.active && dragState.targetGroup === openedGroup, pop: justDroppedGroup === openedGroup }"
          :data-group="openedGroup"
        >
          <div class="back-bar">
            <el-button size="small" text @click="backToGroupList">
              <el-icon><ArrowLeft /></el-icon>
              <span>返回</span>
            </el-button>
            <span class="crumb-sep">/</span>
            <FolderIcon :size="15" />
            <span class="crumb-cur">{{ openedGroup }}</span>
            <span class="pch-badge">{{ groupMembers(openedGroup).length }}</span>
          </div>

          <!-- 拖拽时提示：整片区域都可以放 -->
          <div class="gd-drop-banner" v-if="dragState.active">
            <template v-if="dragState.targetGroup === openedGroup">
              <span class="gdb-dot"></span>
              ⬇ 松开即可把 {{ dragState.accounts.length }} 个账号加入「{{ openedGroup }}」
            </template>
            <template v-else>
              拖到这里松开，即可加入「{{ openedGroup }}」
            </template>
          </div>

          <div class="gd-members">
            <div
              v-for="m in groupMembers(openedGroup)"
              :key="`${m.platform}:${m.account}`"
              class="gd-member"
              :class="{ dragging: isDragging(m) }"
              :title="(m.groups && m.groups.length) ? '所属分组：' + m.groups.join('、') : '未分组'"
              @mousedown="onCardMouseDown(m, $event)"
              @click="onCardClick(m)"
            >
              <!-- 勾选框（与左侧全局选择联动） -->
              <div
                class="acc-check-zone"
                :class="{ on: checkedAccounts.includes(accKey(m)) }"
                @click.stop="toggleAccountCheck(m, !checkedAccounts.includes(accKey(m)))"
              >
                <el-checkbox
                  class="acc-check"
                  :model-value="checkedAccounts.includes(accKey(m))"
                  @click.stop
                  @change="(v: any) => toggleAccountCheck(m, !!v)"
                />
              </div>

              <!-- 头像 -->
              <div class="contact-avatar-wrapper" :style="{ background: getPlatformStyle(m.platform).gradient }">
                <img
                  v-if="m.avatar && !m.avatarLoadFailed"
                  :src="m.avatar"
                  class="contact-real-avatar"
                  referrerpolicy="no-referrer"
                  @error="m.avatarLoadFailed = true"
                  :alt="m.nickname || m.account"
                />
                <span v-else class="avatar-char">{{ getAccountAvatarText(m) }}</span>
              </div>

              <!-- 文本与状态 -->
              <div class="contact-meta-content">
                <div class="contact-first-row">
                  <span class="contact-name-text">
                    <span class="plat-chip" :title="getPlatformStyle(m.platform).name">
                      {{ platShort(m.platform) }}
                    </span>
                    {{ m.nickname || m.account }}
                  </span>
                </div>

                <div class="contact-second-row">
                  <span class="acc-status" :class="m.isValid ? 'ok' : (m.checked ? 'bad' : '')">
                    {{ m.checked ? (m.isValid ? '登录正常' : '登录已失效') : '未检测' }}
                  </span>

                  <span
                    v-if="m.checkedAt"
                    class="contact-checked-at"
                    :class="{ stale: isStaleCheck(m.checkedAt) }"
                    :title="new Date(m.checkedAt).toLocaleString('zh-CN')"
                  >
                    {{ fmtCheckedAt(m.checkedAt) }}
                  </span>

                  <span class="acc-acts" @click.stop>
                    <el-tooltip content="检测登录状态" placement="top">
                      <el-icon class="acc-act" :class="{ spinning: m.isSyncing }" @click="checkStatus(m)">
                        <Refresh />
                      </el-icon>
                    </el-tooltip>
                    <el-tooltip content="打开浏览器登录" placement="top">
                      <el-icon class="acc-act" @click="openBrowserForAccount(m)">
                        <Monitor />
                      </el-icon>
                    </el-tooltip>
                    <el-tooltip content="从该分组移出（不影响其他分组）" placement="top">
                      <el-icon class="gdm-x" @click.stop="handleRemoveFromGroup(m, openedGroup)">
                        <CircleClose />
                      </el-icon>
                    </el-tooltip>
                  </span>
                </div>
              </div>
            </div>

            <div class="gd-empty" v-if="groupMembers(openedGroup).length === 0">
              这个分组还没有账号<br>把左侧的账号拖进来，或拖到其他分组格子上
            </div>
          </div>

          <div class="pane-tip">
            💡 ✕ 只是从本分组移出，账号本身和其他分组都不受影响
          </div>
        </div>

        <!-- ═══ 视图 C：一个分组都没有 ═══ -->
        <div class="gsp-empty" v-else>
          <FolderIcon :size="34" />
          <span>还没有分组</span>
          <span class="gsp-empty-sub">点右上角「+ 新建分组」创建一个，再把左侧账号拖进来</span>
        </div>
      </div>
    </div>

    <!-- 手动拖拽时跟随鼠标的幽灵标签 -->
    <div
      v-if="dragState.active"
      class="drag-ghost"
      :style="{ left: dragState.x + 14 + 'px', top: dragState.y + 14 + 'px' }"
    >
      <FolderIcon :size="13" />
      <span>{{ dragState.accounts.length }} 个账号</span>
      <span v-if="dragState.targetGroup" class="dg-target">→ {{ dragState.targetGroup }}</span>
      <span v-else class="dg-hint">拖到分组文件夹</span>
    </div>

    <!-- 业务分组管理弹窗 -->
    <el-dialog
      v-model="showGroupDialog"
      title="新建分组"
      width="420px"
      append-to-body
      destroy-on-close
    >
      <div class="group-dialog-body">
        <div class="gd-create-row">
          <el-input
            v-model="newGroupName"
            placeholder="分组名称，如「出海三人组」"
            size="default"
            clearable
            @keyup.enter="handleCreateGroup"
          />
          <el-button type="primary" @click="handleCreateGroup">+ 新建</el-button>
        </div>

        <!-- 已有的分组：只读提示，不再提供操作 -->
        <div class="gd-existing" v-if="accountStore.groups.length > 0">
          <span class="gd-existing-label">已有分组：</span>
          <span v-for="g in accountStore.groups" :key="g" class="gd-existing-tag">
            {{ g }}
          </span>
        </div>

        <div class="gd-tip">
          💡 重命名或删除分组，请在分组格子上点 ⋯<br>
          分组用于「发布工作台」里批量勾选账号
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
import { ref, computed, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
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

/** 只看未归类的账号 */
const filterUngrouped = ref(false)

/** 未归入任何分组的账号数 */
const ungroupedCount = computed(() =>
  accountStore.accounts.filter(a => !a.groups || a.groups.length === 0).length
)

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
    } else if (filterUngrouped.value) {
      if (acc.groups && acc.groups.length > 0) return false
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

/* ───────── 手动拖拽（Wails 禁用了 WebView 原生拖放，只能用鼠标事件自己实现） ───────── */
const dragState = reactive({
  active: false,                                  // 是否已进入拖拽态
  accounts: [] as AccountItem[],                 // 正在拖的账号（可能多个）
  x: 0,
  y: 0,
  targetGroup: '',                               // 鼠标当前悬停的文件夹
})

/** 刚放下账号的分组（用于播放弹跳动画） */
const justDroppedGroup = ref('')
const justDroppedTimer = ref<number | null>(null)

function playDropPop(grp: string) {
  if (justDroppedTimer.value) window.clearTimeout(justDroppedTimer.value)
  justDroppedGroup.value = ''
  nextTick(() => {
    justDroppedGroup.value = grp
    justDroppedTimer.value = window.setTimeout(() => {
      justDroppedGroup.value = ''
    }, 520)
  })
}

/** 是否已经提示过"可以拖多个"（仅弹一次） */
const DRAG_TIP_KEY = 'sau_drag_tip_shown'
function maybeShowDragTip() {
  if (localStorage.getItem(DRAG_TIP_KEY)) return
  localStorage.setItem(DRAG_TIP_KEY, '1')
  ElNotification({
    title: '小提示',
    message: '一个账号可以同时拖到多个分组里；勾选多个账号再拖，可以一次归类一批',
    type: 'info',
    duration: 6000
  })
}

onUnmounted(() => {
  if (justDroppedTimer.value) window.clearTimeout(justDroppedTimer.value)
})

/** 待定拖拽（还没超过阈值，避免误触） */
let pendingDrag: { acc: AccountItem; startX: number; startY: number } | null = null

/** 拖拽后要吞掉一次 click，避免在卡片上拖完又触发"打开账号" */
let swallowNextClick = false

const DRAG_THRESHOLD = 5    // 移动超过 5px 才算拖拽

function onCardMouseDown(acc: AccountItem, e: MouseEvent) {
  if (e.button !== 0) return                    // 只响应左键
  const el = e.target as HTMLElement
  // 点在勾选框 / 操作图标 / 分组标签上时不启动拖拽
  if (el.closest('.acc-check-zone, .acc-check, .acc-acts, .el-checkbox')) return
  pendingDrag = { acc, startX: e.clientX, startY: e.clientY }
}

function onGlobalMouseMove(e: MouseEvent) {
  const pd = pendingDrag
  if (!pd) return

  // 未超过阈值：还没进入拖拽态
  if (!dragState.active) {
    if (Math.abs(e.clientX - pd.startX) < DRAG_THRESHOLD &&
        Math.abs(e.clientY - pd.startY) < DRAG_THRESHOLD) return

    dragState.active = true
    // 进入拖拽态：锁定文本选择 + 让输入框失焦（否则拖完会往输入框里打字）
    document.body.classList.add('dragging-active')
    ;(document.activeElement as HTMLElement | null)?.blur()

    // 拖的是已勾选账号 → 带上整批；否则只拖这一个
    const useChecked = checkedAccounts.value.length > 0 && checkedAccounts.value.includes(accKey(pd.acc))
    dragState.accounts = useChecked ? checkedAccountItems.value.slice() : [pd.acc]
  }

  // 拖拽进行中：阻止浏览器默认的文本选择行为
  if (dragState.active) e.preventDefault()

  dragState.x = e.clientX
  dragState.y = e.clientY
  dragState.targetGroup = groupAtPoint(e.clientX, e.clientY)
}

function onGlobalMouseUp(e: MouseEvent) {
  if (dragState.active) {
    swallowNextClick = true                     // 吞掉紧随其后的 click
    setTimeout(() => { swallowNextClick = false }, 0)

    const grp = groupAtPoint(e.clientX, e.clientY)
    const list = dragState.accounts

    if (grp && list.length > 0) {
      accountStore.addAccountsToGroup(
        list.map(a => ({ platform: a.platform, account: a.account })),
        grp
      )
      ElMessage.success(`已将 ${list.length} 个账号加入「${grp}」`)
      playDropPop(grp)
      maybeShowDragTip()
    }
  }
  resetDrag()
}

function resetDrag() {
  pendingDrag = null
  dragState.active = false
  dragState.accounts = []
  dragState.targetGroup = ''
  document.body.classList.remove('dragging-active')
}

/** 用 elementFromPoint 找出鼠标位置下方的文件夹 */
function groupAtPoint(x: number, y: number): string {
  const el = document.elementFromPoint(x, y) as HTMLElement | null
  const folderEl = el?.closest('[data-group]') as HTMLElement | null
  return folderEl?.dataset.group || ''
}

/** 占位：兼容模板里的 isDragging调用 */
function isDragging(acc: AccountItem) {
  return dragState.active && dragState.accounts.some(
    a => a.platform === acc.platform && a.account === acc.account
  )
}

/** 鼠标离开窗口（拖到窗口外松手时，mouseup 收不到）→ 直接复位 */
function onWindowBlurOrLeave() {
  if (dragState.active || pendingDrag) resetDrag()
}

/** 卡片点击（拖拽结束后吞掉 click） */
function onCardClick(acc: AccountItem) {
  if (swallowNextClick) return
  openAccountTab(acc)
}

/* ───────── 文件夹展开 ───────── */
/** 当前进入的分组（空字符串 = 在分组列表视图） */
const openedGroup = ref('')

/** 双击进入分组详情 */
function openGroupDetail(grp: string) {
  openedGroup.value = grp
}

/** 返回分组列表 */
function backToGroupList() {
  openedGroup.value = ''
}

/** 若当前打开的分组被删了，自动退回列表 */
watch(() => accountStore.groups.length, () => {
  if (openedGroup.value && !accountStore.groups.includes(openedGroup.value)) {
    openedGroup.value = ''
  }
})

function groupMembers(grp: string): AccountItem[] {
  return accountStore.accounts.filter(a => a.groups?.includes(grp))
}

/** 从分组移除单个账号 */
function handleRemoveFromGroup(acc: AccountItem, grp: string) {
  accountStore.removeFromGroup(acc.platform, acc.account, grp)
  ElMessage.success(`已从「${grp}」移除`)
}

/** ⋯ 菜单（仅在弹窗内保留，网格视图不再用） */
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
  maybeShowDragTip()
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

/** 正在就地重命名的分组（空 = 没有在重命名） */
const renamingGroup = ref('')
/** 重命名输入中的草稿 */
const renameDraft = ref('')
/** 重命名输入框引用（用于自动聚焦） */
const renameInputRef = ref<any>(null)

/** 开始重命名 */
function startRename(grp: string) {
  if (dragState.active) return          // 拖拽中禁止
  renamingGroup.value = grp
  renameDraft.value = grp
  nextTick(() => {
    const el = renameInputRef.value
    // el-input 的聚焦：拿内部 input 元素
    const input = Array.isArray(el) ? el[0]?.input : el?.input
    input?.focus()
    input?.select()
  })
}

/** 提交重命名 */
function commitRename() {
  const oldName = renamingGroup.value
  if (!oldName) return
  const newName = renameDraft.value.trim()

  // 没改动 → 直接退出
  if (!newName || newName === oldName) {
    renamingGroup.value = ''
    return
  }

  const err = accountStore.renameGroup(oldName, newName)
  if (err) {
    ElMessage.warning(err)
    // 失败时保持编辑态，让用户改
    nextTick(() => {
      const el = renameInputRef.value
      const input = Array.isArray(el) ? el[0]?.input : el?.input
      input?.focus()
    })
    return
  }

  // 如果当前正在看这个分组，名字要跟着换
  if (openedGroup.value === oldName) openedGroup.value = newName

  ElMessage.success('已重命名')
  renamingGroup.value = ''
}

/** 取消重命名 */
function cancelRename() {
  renamingGroup.value = ''
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

  // 如果正在看这个分组，退回列表
  if (openedGroup.value === name) openedGroup.value = ''
}

let unlistenLoginSuccess: (() => void) | null = null

// 初始化时：打开第一个账号标签页，若无账号则打开新标签页向导
onMounted(() => {
  window.addEventListener('mousemove', onGlobalMouseMove, { passive: false } as AddEventListenerOptions)
  window.addEventListener('mouseup', onGlobalMouseUp)
  window.addEventListener('blur', onWindowBlurOrLeave)
  document.addEventListener('mouseleave', onWindowBlurOrLeave)

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
  window.removeEventListener('mousemove', onGlobalMouseMove)
  window.removeEventListener('mouseup', onGlobalMouseUp)
  window.removeEventListener('blur', onWindowBlurOrLeave)
  document.removeEventListener('mouseleave', onWindowBlurOrLeave)
  document.body.classList.remove('dragging-active')
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
  gap: 12px;
  overflow: hidden;
  padding: 12px 14px 14px;
  box-sizing: border-box;
}

/* 顶部汇总条 */
.account-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: var(--shadow-card);
  margin: 14px 14px 0;
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
.acc-check-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  width: 34px;
  min-width: 34px;
  margin-left: -6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color .15s;
}

.acc-check-zone:hover {
  background: rgba(79, 70, 229, .09);
}

.acc-check-zone.on {
  background: rgba(79, 70, 229, .07);
}

.acc-check {
  margin-right: 0;
  flex-shrink: 0;
  transform: scale(1.2);
  transform-origin: center;
  pointer-events: none;
}

.sum-batch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
  margin-left: auto;
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
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
  padding: 14px 16px;
}
/* ── 两栏卡片通用标题行 ── */
.pane-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 12px;
  flex-shrink: 0;
}
.pane-card-head .el-button {
  min-width: 96px;
  justify-content: center;
}
.pch-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}
.pch-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 20px;
  background: rgba(79, 70, 229, .12);
  color: var(--primary-color);
}
.pch-spacer { flex: 1; }

/* ══════ 分组平铺网格 ══════ */
.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  align-content: start;
  padding: 2px;              /* 给放大后的格子留点空间 */
}

.fcell {
  border: 1px solid var(--border-subtle);
  border-radius: 11px;
  padding: 18px 8px 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  transition: border-color .18s ease, background-color .18s ease,
              transform .18s ease, box-shadow .18s ease;
  position: relative;
}

/* ── 拖拽中：所有格子变「可放置」呼吸动画 ── */
@keyframes fcell-breathe {
  0%, 100% {
    border-color: rgba(79, 70, 229, .40);
    box-shadow: 0 0 0 0 rgba(79, 70, 229, .16);
  }
  50% {
    border-color: rgba(79, 70, 229, .72);
    box-shadow: 0 0 0 4px rgba(79, 70, 229, .10);
  }
}

.folder-grid.dragging .fcell {
  border: 2px dashed rgba(79, 70, 229, .55);
  background: rgba(79, 70, 229, .035);
  animation: fcell-breathe 1.6s ease-in-out infinite;
}
/* 错开延迟 → 视觉上像波纹扩散 */
.folder-grid.dragging .fcell:nth-child(2) { animation-delay: .18s; }
.folder-grid.dragging .fcell:nth-child(3) { animation-delay: .36s; }
.folder-grid.dragging .fcell:nth-child(4) { animation-delay: .54s; }
.folder-grid.dragging .fcell:nth-child(5) { animation-delay: .72s; }
.folder-grid.dragging .fcell:nth-child(6) { animation-delay: .90s; }
.folder-grid.dragging .fcell:nth-child(n+7) { animation-delay: 1.08s; }

/* 非拖拽时保持原来的 hover */
.folder-grid:not(.dragging) .fcell:hover {
  border-color: rgba(79, 70, 229, .35);
  background: rgba(79, 70, 229, .035);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(79, 70, 229, .10);
}

/* ── 悬停目标格子：放大吸住 ── */
@keyframes fcell-pull {
  from { transform: translateY(-2px) scale(1.02); }
  to   { transform: translateY(-4px) scale(1.07); }
}
.folder-grid.dragging .fcell.hot {
  border: 2px solid var(--primary-color);
  background: rgba(79, 70, 229, .13);
  box-shadow: 0 0 0 5px rgba(79, 70, 229, .14), 0 10px 24px rgba(79, 70, 229, .20);
  animation: fcell-pull .5s ease-in-out infinite alternate;
  z-index: 2;
}
.folder-grid.dragging .fcell.hot .fcell-name { color: var(--primary-color); }

/* ── 放下瞬间：弹一下 ── */
@keyframes fcell-pop {
  0%   { transform: scale(1); }
  35%  { transform: scale(1.10); }
  70%  { transform: scale(.97); }
  100% { transform: scale(1); }
}
.fcell.pop {
  animation: fcell-pop .45s cubic-bezier(.34, 1.56, .64, 1);
  border-color: rgba(34, 197, 94, .55) !important;
  background: rgba(34, 197, 94, .08);
}
.fcell.pop .fcell-count {
  background: rgba(34, 197, 94, .14) !important;
  color: #16a34a !important;
  transition: all .3s;
}

/* ── 「松开加入」提示 ── */
.drop-hint {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(79, 70, 229, .12);
  padding: 2px 9px;
  border-radius: 20px;
  white-space: nowrap;
}

.fcell-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-main);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  transition: color .18s;
}

/* 就地重命名输入框 */
.fcell-rename {
  width: 100%;
}
.fcell-rename :deep(.el-input__wrapper) {
  padding: 0 6px;
  height: 24px;
  border-radius: 6px;
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}
.fcell-rename :deep(.el-input__inner) {
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  height: 24px;
}
.fcell-count {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 20px;
  background: rgba(79, 70, 229, .10);
  color: var(--primary-color);
  white-space: nowrap;
  transition: all .2s;
}
.fcell.empty .fcell-count {
  background: rgba(128, 128, 128, .10);
  color: var(--text-muted);
}
.fcell.empty { opacity: .72; }

/* ── 进入分组后的视图 ── */
@keyframes gd-breathe {
  0%, 100% { box-shadow: inset 0 0 0 2px rgba(79, 70, 229, .30); }
  50%      { box-shadow: inset 0 0 0 2px rgba(79, 70, 229, .62); }
}

.group-detail {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  transition: background-color .18s ease, box-shadow .18s ease;
}

/* 拖拽中（还没进入本区域上方） */
.group-detail.droppable {
  background: rgba(79, 70, 229, .035);
  animation: gd-breathe 1.6s ease-in-out infinite;
}

/* 鼠标已经在本区域上方 → 更强提示 */
.group-detail.hot {
  background: rgba(79, 70, 229, .09);
  box-shadow: inset 0 0 0 2px var(--primary-color) !important;
  animation: none;
}

/* 放下瞬间的绿色反馈 */
.group-detail.pop {
  background: rgba(34, 197, 94, .07);
  box-shadow: inset 0 0 0 2px rgba(34, 197, 94, .45) !important;
  animation: none;
}

/* 提示条 */
.gd-drop-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  margin-bottom: 10px;
  border-radius: 8px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--primary-color);
  background: rgba(79, 70, 229, .09);
  border: 1px dashed rgba(79, 70, 229, .45);
  flex-shrink: 0;
}

.gdb-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  flex-shrink: 0;
  animation: gdb-pulse 1s ease-in-out infinite;
}
@keyframes gdb-pulse {
  0%, 100% { opacity: .35; transform: scale(.85); }
  50%      { opacity: 1;   transform: scale(1.15); }
}

.back-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 10px;
  flex-shrink: 0;
}
.crumb-sep { color: var(--border-strong, #d1d5db); }
.crumb-cur {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gd-members {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 分组视图里的账号卡片：复用账号列表的卡片结构 */
.gd-member {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  position: relative;
  background: transparent;
}
.gd-member:hover {
  background: var(--bg-detail);
}
.gd-member.dragging {
  opacity: .45;
  transform: scale(.95);
  border-style: dashed;
}

/* .gdm-x 在 .acc-acts 容器内，受 .acc-act 样式支配，此处微调 */
.gdm-x {
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  opacity: .55;
  transition: all .15s;
}
.gdm-x:hover {
  opacity: 1;
  color: var(--status-danger);
}

.gsp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 34px 0;
  color: var(--text-muted);
  font-size: 12px;
  flex: 1;
}
.gsp-empty-sub { font-size: 11px; opacity: .7; }

.pane-tip {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.6;
  padding-top: 12px;
  margin-top: 4px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* ── 账号筛选 chips ── */
.acc-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  flex-shrink: 0;
}

.acc-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}

.acc-chip:hover:not(.disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.acc-chip.on {
  border-color: var(--primary-color);
  background: rgba(79, 70, 229, .09);
  color: var(--primary-color);
}

.chip-n {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
  background: rgba(79, 70, 229, .13);
}

/* danger chip */
.acc-chip.danger { color: var(--status-danger, #dc2626); border-color: rgba(220, 38, 38, .30); }
.acc-chip.danger .chip-n { background: rgba(220, 38, 38, .11); }
.acc-chip.danger.on { border-color: var(--status-danger, #dc2626); background: rgba(220, 38, 38, .07); }
.acc-chip.danger.on .chip-n { background: rgba(220, 38, 38, .18); }
.acc-chip.danger.disabled { opacity: .5; cursor: default; }

/* warn chip（未分组） */
.acc-chip.warn { color: var(--status-warning, #d97706); border-color: rgba(217, 119, 6, .30); }
.acc-chip.warn .chip-n { background: rgba(217, 119, 6, .11); }
.acc-chip.warn.on { border-color: var(--status-warning, #d97706); background: rgba(217, 119, 6, .07); }
.acc-chip.warn.on .chip-n { background: rgba(217, 119, 6, .18); }
.acc-chip.warn.disabled { opacity: .5; cursor: default; }

/* ── 账号卡片 ── */
.acc-acts { margin-left: auto; display: flex; gap: 6px; flex-shrink: 0; }
.acc-act { font-size: 13px; color: var(--text-muted); cursor: pointer; opacity: .55; }
.acc-act:hover { opacity: 1; color: var(--primary-color); }
.acc-act.spinning { animation: spin 1s linear infinite; opacity: 1; }
@keyframes spin { to { transform: rotate(360deg); } }
.contact-item.dragging {
  opacity: .4;
  transform: scale(.95);
  border-style: dashed;
}
.contact-card-item.dragging {
  opacity: .45;
  transform: scale(.95);
}

/* ── 滚动条统一样式（两栏） ── */
.folder-grid::-webkit-scrollbar,
.gd-members::-webkit-scrollbar,
.account-sidebar-pane ::-webkit-scrollbar {
  width: 6px;
}
.folder-grid::-webkit-scrollbar-thumb,
.gd-members::-webkit-scrollbar-thumb,
.account-sidebar-pane ::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, .22);
  border-radius: 3px;
}
.folder-grid::-webkit-scrollbar-thumb:hover,
.gd-members::-webkit-scrollbar-thumb:hover,
.account-sidebar-pane ::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 128, 128, .38);
}
.folder-grid::-webkit-scrollbar-track,
.gd-members::-webkit-scrollbar-track,
.account-sidebar-pane ::-webkit-scrollbar-track {
  background: transparent;
}

/* 拖拽跟随幽灵标签（pointer-events: none 避免 elementFromPoint 命中它自己） */
/* ══════ 幽灵：摇摆 + 目标提示 ══════ */
@keyframes ghost-wiggle {
  0%, 100% { transform: rotate(-1.5deg); }
  50%      { transform: rotate(1.5deg); }
}
.drag-ghost {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--primary-color), #6366f1);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 10px 26px rgba(79, 70, 229, .42),
              0 0 0 1px rgba(255, 255, 255, .14) inset;
  animation: ghost-wiggle 1s ease-in-out infinite;
  white-space: nowrap;
}
.drag-ghost .dg-target {
  background: rgba(255, 255, 255, .22);
  padding: 1px 8px;
  border-radius: 20px;
  font-size: 11px;
}
.drag-ghost .dg-hint {
  opacity: .75;
  font-weight: 400;
}

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
}

/* 已有的分组（只读提示） */
.gd-existing {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.gd-existing-label {
  font-size: 11.5px;
  color: var(--text-muted);
}
.gd-existing-tag {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 20px;
  background: rgba(79, 70, 229, .08);
  color: var(--primary-color);
}

/* ── 格子 ⋯ 操作菜单 ── */
.fcell { position: relative; }

/* hover 时右上角操作图标 */
.fcell-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 3px;
  opacity: 0;
  transform: translateY(-2px);
  transition: opacity .15s ease, transform .15s ease;
  z-index: 3;
}
.fcell:hover .fcell-actions {
  opacity: 1;
  transform: translateY(0);
}

/* 拖拽中隐藏操作图标，避免误点 */
.folder-grid.dragging .fcell-actions {
  display: none;
}

.fcell-act {
  width: 21px;
  height: 21px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, .82);
  cursor: pointer;
  transition: all .15s;
}

.fcell-act:hover {
  background: rgba(79, 70, 229, .13);
  color: var(--primary-color);
}

/* 删除：hover 才变红，避免视觉上太"危险" */
.fcell-act.danger:hover {
  background: rgba(220, 38, 38, .12);
  color: var(--status-danger);
}

/* 空状态 */
.gd-empty {
  display: flex; flex-direction: column; align-items: center; gap: 9px;
  padding: 30px 0;
  color: var(--text-muted); font-size: 12px;
  line-height: 1.9;
}

/* 底部提示 */
.gd-tip {
  margin-top: 13px;
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.65;
}
</style>

<!-- 全局：拖拽期间禁止选择文字（scoped 只能操作组件内，body 需要全局覆盖） -->
<style>
/* 拖拽进行中：禁止选中文字、光标变抓取 */
body.dragging-active,
body.dragging-active * {
  user-select: none !important;
  -webkit-user-select: none !important;
}
body.dragging-active { cursor: grabbing !important; }
</style>
