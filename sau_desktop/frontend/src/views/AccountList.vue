<template>
  <div class="account-browser-workspace">
    <!-- 👈 左侧：矩阵账号通讯录侧边栏 (WeChat-style Contact List) -->
    <div class="account-sidebar-pane">
      <!-- 1. 顶部操作与搜索中枢 -->
      <div class="sidebar-header-section">
        <div class="sidebar-title-bar">
          <div class="title-with-pill">
            <span class="sidebar-title">矩阵账号通讯录</span>
            <span class="account-count-badge">{{ accountStore.accounts.length }}</span>
          </div>

          <el-button 
            size="small" 
            type="primary" 
            class="add-account-gradient-btn"
            @click="openNewTab"
          >
            <el-icon><Plus /></el-icon>
            <span>添加账号</span>
          </el-button>
        </div>

        <!-- 搜索框 (适配亮色与暗色模式) -->
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

          <el-tooltip content="管理/新建业务分组" placement="top">
            <el-button size="small" type="info" plain circle @click="showGroupDialog = true">
              <el-icon><FolderAdd /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- 2. 账号联系人滚动列表 -->
      <div class="sidebar-contact-list custom-scrollbar">
        <!-- 空状态 -->
        <div v-if="filteredAccounts.length === 0" class="contact-empty-state">
          <el-icon class="empty-icon"><UserFilled /></el-icon>
          <p class="empty-title">未找到匹配的矩阵账号</p>
          <el-button size="small" type="primary" link @click="openNewTab">
            接入新账号
          </el-button>
        </div>

        <!-- 账号联系人单元 (微信项风格，深度适配浅色/暗黑主题) -->
        <div 
          v-for="acc in filteredAccounts" 
          :key="acc.platform + ':' + acc.account"
          class="contact-card-item"
          :class="{ 'is-active': activeTabId === `${acc.platform}:${acc.account}` }"
          @click="openAccountTab(acc)"
        >
          <!-- 头像模块：平台渐变背景 + 字母大写 Monogram + 右下平台微标 + 左上健康状态灯 -->
          <div class="contact-avatar-wrapper" :style="{ background: getPlatformStyle(acc.platform).gradient }">
            <span class="avatar-char">{{ getAccountAvatarText(acc) }}</span>
            <!-- 右下角平台微标 -->
            <span class="avatar-plat-icon">
              <el-icon><component :is="getPlatformStyle(acc.platform).icon" /></el-icon>
            </span>
            <!-- 左上角健康度状态呼吸指示灯 -->
            <span 
              class="avatar-status-dot" 
              :class="acc.checked ? (acc.isValid ? 'is-valid' : 'is-invalid') : 'is-unchecked'"
              :title="acc.checked ? (acc.isValid ? '登录凭证健康有效' : '登录凭证已失效') : '凭证待检测'"
            ></span>
          </div>

          <!-- 文本与状态信息 -->
          <div class="contact-meta-content">
            <div class="contact-first-row">
              <span class="contact-name-text">{{ acc.nickname || acc.account }}</span>
              <span class="contact-platform-tag" :style="{ color: getPlatformStyle(acc.platform).brandColor }">
                {{ getPlatformStyle(acc.platform).name }}
              </span>
            </div>

            <div class="contact-second-row">
              <span class="contact-group-name">#{{ acc.group || '默认组' }}</span>
              <span 
                class="contact-status-label" 
                :class="{ 'status-err': acc.checked && !acc.isValid, 'status-ok': acc.checked && acc.isValid }"
              >
                {{ acc.checked ? (acc.isValid ? '凭证有效' : '需重新扫码') : '待检测' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 👉 右侧：完整拟真浏览器窗口 (Full-fledged Tabbed Browser Shell) -->
    <div class="browser-window-pane">
      <!-- 1. 顶部浏览器多标签页栏 (Chrome/Edge Style Tabs Bar) -->
      <div class="browser-tab-bar">
        <div class="tab-list-wrapper">
          <div 
            v-for="tab in openTabs" 
            :key="tab.id"
            class="browser-tab-item"
            :class="{ 'active': activeTabId === tab.id }"
            @click="activateTab(tab.id)"
          >
            <!-- 平台小图标 / Favicon -->
            <span class="tab-favicon" v-if="tab.type === 'account'">
              <el-icon><component :is="getPlatformStyle(tab.platform).icon" /></el-icon>
            </span>
            <span class="tab-favicon tab-new-icon" v-else>
              <el-icon><Compass /></el-icon>
            </span>

            <!-- 标签页标题 -->
            <span class="tab-title">{{ tab.title }}</span>

            <!-- 状态小绿点/红点 -->
            <span 
              v-if="tab.type === 'account' && tab.accountItem?.checked" 
              class="tab-health-dot" 
              :class="tab.accountItem?.isValid ? 'valid' : 'invalid'"
            ></span>

            <!-- 关闭标签页按钮 -->
            <el-icon 
              class="tab-close-btn" 
              @click.stop="closeTab(tab.id)"
              v-if="openTabs.length > 1"
            >
              <Close />
            </el-icon>
          </div>

          <!-- 新建标签页按钮 (+) -->
          <button class="new-tab-plus-btn" @click="openNewTab" title="打开新标签页 / 接入新账号">
            <el-icon><Plus /></el-icon>
          </button>
        </div>

        <!-- 视窗辅助控件 -->
        <div class="browser-window-controls">
          <span class="traffic-dot red" @click="closeCurrentTab" title="关闭当前标签"></span>
          <span class="traffic-dot yellow" @click="isInteractive = !isInteractive" :title="isInteractive ? '已开启鼠标穿透' : '已关闭鼠标穿透'"></span>
          <span class="traffic-dot green" title="浏览器状态良好"></span>
        </div>
      </div>

      <!-- 2. 浏览器导航与地址工具栏 (Omnibox Navigation Bar) -->
      <div class="browser-navigation-bar">
        <!-- 导航按钮 -->
        <div class="nav-button-group">
          <button class="nav-icon-btn" title="后退" disabled>
            <el-icon><Back /></el-icon>
          </button>
          <button class="nav-icon-btn" title="前进" disabled>
            <el-icon><Right /></el-icon>
          </button>
          <button class="nav-icon-btn" @click="handleReloadPage" title="重新刷新网页">
            <el-icon :class="{ 'is-loading': isStartingSession }"><Refresh /></el-icon>
          </button>
          <button class="nav-icon-btn" @click="handleGoHome" title="返回创作者首页">
            <el-icon><HomeFilled /></el-icon>
          </button>
        </div>

        <!-- 拟真 URL 地址栏 (Omnibox) -->
        <div class="browser-omnibox">
          <el-icon class="ssl-lock-icon"><Lock /></el-icon>
          <span class="omnibox-url-text">{{ currentActiveTab?.url || 'sau://new-tab' }}</span>

          <!-- 地址栏内部状态胶囊 -->
          <div class="omnibox-badges" v-if="currentActiveTab?.type === 'account'">
            <span class="platform-omnibox-tag" :style="{ background: getPlatformStyle(currentActiveTab.platform).gradient }">
              {{ getPlatformStyle(currentActiveTab.platform).name }}
            </span>
            <el-tag 
              size="small" 
              :type="currentActiveTab.accountItem?.isValid ? 'success' : 'danger'" 
              effect="dark" 
              round
              class="omnibox-status-tag"
            >
              {{ currentActiveTab.accountItem?.isValid ? '✅ 凭证正常' : '⚠️ 需重新扫码' }}
            </el-tag>
          </div>
        </div>

        <!-- 工具栏右侧操作按钮组 -->
        <div class="browser-toolbar-actions">
          <template v-if="currentActiveTab?.type === 'account' && currentActiveTab.accountItem">
            <el-button 
              size="small" 
              type="primary" 
              plain
              :loading="currentActiveTab.accountItem.loading"
              @click="checkStatus(currentActiveTab.accountItem)"
            >
              <el-icon><Search /></el-icon>
              <span>检测凭证</span>
            </el-button>

            <el-button 
              size="small" 
              type="warning" 
              class="relogin-toolbar-btn"
              :loading="currentActiveTab.isStartingSession"
              @click="startAppWindowForTab(currentActiveTab)"
            >
              <el-icon><RefreshRight /></el-icon>
              <span>{{ currentActiveTab.isSessionActive ? '重新载入' : '启动视窗' }}</span>
            </el-button>

            <el-button 
              v-if="currentActiveTab.isSessionActive"
              size="small" 
              type="danger" 
              plain
              @click="stopSessionForTab(currentActiveTab)"
            >
              <el-icon><CircleClose /></el-icon>
              <span>结束本次会话</span>
            </el-button>

            <!-- 暂时注释：内嵌投屏模式反向交互切换按钮 (原生独立视窗直接支持原生输入与鼠标)
            <el-tooltip :content="isInteractive ? '已开启双向鼠标反向操作' : '已禁用鼠标反向操作'" placement="top">
              <el-button 
                size="small" 
                :type="isInteractive ? 'primary' : 'info'" 
                link
                @click="isInteractive = !isInteractive"
              >
                <el-icon><Pointer /></el-icon>
                <span>{{ isInteractive ? '交互开' : '只读' }}</span>
              </el-button>
            </el-tooltip>
            -->

            <el-button 
              size="small" 
              type="danger" 
              link
              @click="confirmDelete(currentActiveTab.platform, currentActiveTab.account)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </div>
      </div>

      <!-- 3. 浏览器视窗主内容区 (Browser Viewport) - 多标签各自拥有独立 DOM，切换时不销毁、不重新扫码 -->
      <div class="browser-viewport-stage">
        <div 
          v-for="tab in openTabs" 
          :key="tab.id"
          v-show="activeTabId === tab.id"
          class="tab-viewport-container"
        >
          <!-- A. 处于会话中 (统一采用原生超清 Chrome App 视窗模式 · 0 延迟) -->
          <template v-if="tab.isSessionActive">
            <!-- 原生 Chrome App 沉浸式真机视窗模式 (4K Retina · 0 延迟) -->
            <div class="browser-appmode-hub">
              <div class="appmode-card">
                <div class="appmode-header">
                  <div class="appmode-badge-live">
                    <span class="live-pulse-dot"></span>
                    <span>原生 Chrome App 视窗运行中</span>
                  </div>
                  <el-tag size="small" effect="dark" type="success" round>4K 视网膜极清 · 0 延迟直通</el-tag>
                </div>

                <div class="appmode-avatar-box" :style="{ background: getPlatformStyle(tab.platform).gradient }">
                  <span class="avatar-char">{{ getAccountAvatarText(tab.accountItem) }}</span>
                  <span class="avatar-badge">
                    <el-icon><component :is="getPlatformStyle(tab.platform).icon" /></el-icon>
                  </span>
                </div>

                <h3 class="appmode-title">{{ tab.accountItem?.nickname || tab.accountItem?.account || tab.title }}</h3>
                <p class="appmode-url">{{ tab.url }}</p>

                <div class="appmode-guide-tip">
                  <el-icon><CircleCheck /></el-icon>
                  <span>独立真机 Chrome 视窗已为您展开在桌面！拥有 100% 原始视网膜画质与原生手势交互，支持直接使用输入法打字、拖拽上传视频。最新会话凭证每 30 秒自动快照存盘。</span>
                </div>

                <div class="appmode-actions">
                  <el-button 
                    type="primary" 
                    size="large" 
                    class="focus-window-btn"
                    @click="startAppWindowForTab(tab)"
                  >
                    <el-icon><RefreshRight /></el-icon>
                    <span>重新唤起 / 置顶视窗</span>
                  </el-button>

                  <el-button 
                    type="danger" 
                    size="large" 
                    plain
                    class="stop-session-btn"
                    @click="stopSessionForTab(tab)"
                  >
                    <el-icon><CircleClose /></el-icon>
                    <span>结束本次会话并存盘</span>
                  </el-button>
                </div>

                <!-- 暂时注释：内嵌投屏模式切换按钮
                <div class="appmode-switch-mode">
                  <el-button link type="info" size="small" @click="switchToScreencastMode(tab)">
                    <el-icon><VideoPlay /></el-icon>
                    <span>需要在此界面直接呈现投屏？点击切换为「应用内投屏模式」</span>
                  </el-button>
                </div>
                -->
              </div>
            </div>

            <!-- 暂时注释：A2. 轻量无头 Canvas 投屏流模式
            <div v-else class="live-canvas-fill">
              <LiveBrowserCanvas 
                :taskId="tab.taskId"
                :title="`${tab.title} - 实时无头浏览器视窗`"
              />
            </div>
            -->
          </template>

          <!-- B. 待机状态：账号创作者中心就绪面板 -->
          <div v-else-if="tab.type === 'account' && tab.accountItem" class="browser-standby-hub">
            <div class="standby-card-content">
              <div class="standby-brand-avatar" :style="{ background: getPlatformStyle(tab.platform).gradient }">
                <span class="avatar-huge-char">{{ getAccountAvatarText(tab.accountItem) }}</span>
                <span class="brand-sub-badge">
                  <el-icon><component :is="getPlatformStyle(tab.platform).icon" /></el-icon>
                </span>
              </div>

              <h2 class="standby-account-title">{{ tab.accountItem.nickname || tab.accountItem.account }}</h2>
              <div class="standby-meta-pills">
                <el-tag size="default" :type="tab.accountItem.isValid ? 'success' : 'danger'" effect="dark" round>
                  {{ tab.accountItem.isValid ? '✅ 凭证正常 · 随时可执行矩阵任务' : '⚠️ 登录凭证已失效 · 请扫码更新' }}
                </el-tag>
                <el-tag size="default" type="info" round v-if="tab.accountItem.finderUid">
                  UID: {{ tab.accountItem.finderUid }}
                </el-tag>
                <el-tag size="default" type="warning" round>
                  分组: {{ tab.accountItem.group || '默认业务组' }}
                </el-tag>
              </div>

              <p class="standby-intro-desc" v-if="tab.accountItem.isValid">
                本账号登录状态健康，点击下方按钮即可直接在独立原生视窗打开创作者服务平台，享受原生极清字效与顺畅交互。
              </p>
              <p class="standby-intro-desc warning-text" v-else>
                当前账号凭证已失效，点击下方按钮将拉起原生视窗呈现扫码页面，手机微信/抖音扫码即可无缝完成绑定更新。
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
                  <span>{{ tab.accountItem.isValid ? '🚀 启动原生浏览器视窗' : '🚀 立即拉起原生视窗扫码' }}</span>
                </el-button>

                <!-- 暂时注释内嵌投屏模式
                <el-button 
                  type="info" 
                  plain 
                  size="default" 
                  class="launch-screencast-sub-btn"
                  :loading="tab.isStartingSession"
                  @click="startScreencastForTab(tab)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  <span>在应用内嵌投屏中打开 (可选)</span>
                </el-button>
                -->
              </div>

              <div class="standby-feature-tags">
                <span>🚀 原生 Chrome / Edge 视窗</span>
                <span>💎 100% 原始视网膜画质</span>
                <span>🖱️ 零延迟原生输入与交互</span>
                <span>🔒 本地加密持久化</span>
              </div>
            </div>
          </div>

          <!-- C. 新标签页 (New Tab) / 快速接入向导 -->
          <div v-else class="browser-newtab-hub">
            <div class="newtab-content-box">
              <div class="newtab-logo-box">
                <el-icon class="newtab-logo"><Compass /></el-icon>
              </div>
              <h2 class="newtab-heading">接入新自媒体平台账号</h2>
              <p class="newtab-sub">选择您要接入的目标媒体平台，系统将自动拉起原生浏览器视窗并呈现扫码页面：</p>

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

              <!-- 别名输入与启动按钮 -->
              <div class="newtab-launch-form">
                <div class="form-row">
                  <span class="row-label">自定义账号别名:</span>
                  <el-input 
                    v-model="newTabAccountAlias" 
                    placeholder="选填：留空自动读取平台真实昵称与UID" 
                    size="default" 
                    style="flex: 1;"
                    clearable
                  />
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
                    <span>🚀 立即拉起原生浏览器视窗并扫码</span>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. 浏览器底部状态栏 (Browser Status Footer) -->
      <div class="browser-footer-bar" v-if="currentActiveTab?.isSessionActive">
        <div class="footer-status-left">
          <span class="active-pulse-dot"></span>
          <span>{{ currentActiveTab.sessionStatusText }}</span>
        </div>

        <div class="footer-status-right">
          <el-button size="small" type="danger" plain @click="stopSessionForTab(currentActiveTab)">
            <el-icon><CircleClose /></el-icon>
            <span>结束本次会话</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 业务分组管理弹窗 -->
    <el-dialog
      v-model="showGroupDialog"
      title="业务矩阵分组管理"
      width="420px"
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
          <div class="group-list-title">现有业务矩阵分组：</div>
          <div class="group-tags">
            <el-tag 
              v-for="grp in accountStore.groups" 
              :key="grp"
              size="default"
              effect="plain"
              class="group-tag-item"
            >
              {{ grp }}
            </el-tag>
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
import { useAccountStore, AccountItem } from '../stores/accountStore'
import { LoginAccountWithAppWindow, LoginAccountWithScreencast, StopTaskById } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'
// import LiveBrowserCanvas from '../components/matrix/LiveBrowserCanvas.vue'

const accountStore = useAccountStore()

// 浏览器标签页结构定义 (每个标签页独立维护自己的会话与画面状态)
interface BrowserTab {
  id: string // e.g. "douyin:account_1" 或 "new_tab_..."
  type: 'account' | 'new'
  title: string
  platform: string
  account: string
  url: string
  accountItem?: AccountItem
  isSessionActive: boolean
  sessionMode?: 'app' | 'screencast'
  isStartingSession: boolean
  taskId: string
  sessionStatusText: string
}

const openTabs = ref<BrowserTab[]>([])
const activeTabId = ref<string>('')

const currentPlatformFilter = ref('all')
const currentGroupFilter = ref('all')
const searchKeyword = ref('')

const isInteractive = ref(true)

const newTabSelectedPlatform = ref('douyin')
const newTabAccountAlias = ref('')

const showGroupDialog = ref(false)
const newGroupName = ref('')

const platformList = computed(() => PLATFORMS)
const availablePlatforms = computed(() => PLATFORMS)

// 当前激活的标签页
const currentActiveTab = computed<BrowserTab | null>(() => {
  return openTabs.value.find(t => t.id === activeTabId.value) || openTabs.value[0] || null
})

// 筛选后的左侧账号列表
const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(acc => {
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

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
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

const getAccountAvatarText = (acc: AccountItem) => {
  const name = acc.nickname || acc.account || 'U'
  return name.trim().slice(0, 1).toUpperCase()
}

// 激活某个标签页 (平滑切换视窗，保留后台各标签页的投屏连接，绝不关闭会话)
const activateTab = (tabId: string) => {
  activeTabId.value = tabId
}

// 左侧点击用户卡片：在右侧打开或切换到该用户的浏览器标签页！
const openAccountTab = (acc: AccountItem) => {
  const tabId = `${acc.platform}:${acc.account}`
  const existing = openTabs.value.find(t => t.id === tabId)
  if (existing) {
    existing.accountItem = acc
    existing.title = `${getPlatformConfig(acc.platform).name} - ${acc.nickname || acc.account}`
    activeTabId.value = tabId
  } else {
    openTabs.value.push({
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
      sessionStatusText: '等待启动会话...'
    })
    activeTabId.value = tabId
  }
}

// 打开“新建标签页 / 接入新账号”
const openNewTab = () => {
  const newTabId = `new_tab_${Date.now()}`
  openTabs.value.push({
    id: newTabId,
    type: 'new',
    title: '新建标签页',
    platform: newTabSelectedPlatform.value,
    account: '',
    url: 'sau://new-tab',
    isSessionActive: false,
    isStartingSession: false,
    taskId: `login_new_${Date.now()}`,
    sessionStatusText: '就绪'
  })
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

const closeCurrentTab = () => {
  if (currentActiveTab.value) {
    closeTab(currentActiveTab.value.id)
  }
}

// 为指定标签页拉起原生 Chrome App 沉浸式真机视窗 (4K 原生画质与 0 延迟)
const startAppWindowForTab = async (tab: BrowserTab) => {
  const platform = tab.platform
  const account = tab.account || 'auto'
  tab.taskId = `login_${platform}_${account}`
  tab.sessionMode = 'app'
  tab.isSessionActive = true
  tab.isStartingSession = true
  tab.sessionStatusText = '正在拉起原生 Chrome App 沉浸式视窗 (4K 视网膜画质 · 0 延迟)...'

  try {
    const res = await LoginAccountWithAppWindow(platform, account)
    if (res && res.success) {
      tab.sessionStatusText = `🎉 会话已结束，账号 [${res.nickname || res.account}] 凭证已存盘`
      ElMessage.success(`账号 [${res.nickname || res.account}] 凭证已同步存盘`)
      accountStore.saveLoggedInAccount(platform, res.account || account, res.nickname, res.finderUid, true)
    } else {
      tab.sessionStatusText = `会话已结束: ${res?.msg || '操作完成'}`
      if (res?.msg && res.msg !== '操作完成') {
        ElMessage.error({ message: `拉起登录失败: ${res.msg}`, duration: 8000 })
      }
    }
  } catch (err: any) {
    const errStr = err?.message || String(err)
    if (!errStr.includes('手动中止') && !errStr.includes('signal') && !errStr.includes('killed')) {
      tab.sessionStatusText = `会话已结束: ${errStr}`
      const cleanMsg = errStr.startsWith('拉起') ? errStr : `拉起浏览器异常: ${errStr}`
      ElMessage.error({ message: cleanMsg, duration: 8000 })
    }
  } finally {
    tab.isStartingSession = false
    tab.isSessionActive = false
    await accountStore.fetchAccounts()
    const targetAcc = accountStore.accounts.find(a => a.platform === platform && (a.account === account || a.account === tab.account))
    if (targetAcc && !targetAcc.isValid) {
      await accountStore.checkAccount(targetAcc)
    }
  }
}

// 暂时注释内嵌投屏方法，统一使用原生独立视窗模式
/*
const startScreencastForTab = async (tab: BrowserTab) => {
  const platform = tab.platform
  const account = tab.account || 'auto'
  tab.taskId = `login_${platform}_${account}`
  tab.sessionMode = 'screencast'
  tab.isSessionActive = true
  tab.isStartingSession = true
  tab.sessionStatusText = '正在拉起后台无头浏览器并建立 CDP 画面流...'

  try {
    const res = await LoginAccountWithScreencast(platform, account)
    if (res && res.success) {
      tab.sessionStatusText = `🎉 会话已结束，账号 [${res.nickname || res.account}] 凭证已存盘`
      ElMessage.success(`账号 [${res.nickname || res.account}] 凭证已同步存盘`)
      accountStore.saveLoggedInAccount(platform, res.account || account, res.nickname, res.finderUid, true)
    } else {
      tab.sessionStatusText = `会话已结束: ${res?.msg || '操作完成'}`
      if (res?.msg && res.msg !== '操作完成') {
        ElMessage.error({ message: `拉起投屏登录失败: ${res.msg}`, duration: 8000 })
      }
    }
  } catch (err: any) {
    const errStr = err?.message || String(err)
    if (!errStr.includes('手动中止') && !errStr.includes('signal') && !errStr.includes('killed')) {
      tab.sessionStatusText = `会话已结束: ${errStr}`
      ElMessage.error({ message: `拉起投屏异常: ${errStr}`, duration: 8000 })
    }
  } finally {
    tab.isStartingSession = false
    tab.isSessionActive = false
    await accountStore.fetchAccounts()
    const targetAcc = accountStore.accounts.find(a => a.platform === platform && (a.account === account || a.account === tab.account))
    if (targetAcc && !targetAcc.isValid) {
      await accountStore.checkAccount(targetAcc)
    }
  }
}

const switchToScreencastMode = async (tab: BrowserTab) => {
  await stopSessionForTab(tab)
  startScreencastForTab(tab)
}
*/

// 在会话运行中动态切换为原生超清 App 视窗
const switchToAppWindowMode = async (tab: BrowserTab) => {
  await stopSessionForTab(tab)
  startAppWindowForTab(tab)
}

// 新标签页中发起接入
const startNewTabLoginForTab = (tab: BrowserTab) => {
  tab.platform = newTabSelectedPlatform.value
  tab.account = newTabAccountAlias.value.trim() || 'auto'
  startAppWindowForTab(tab)
}

// 停止指定标签页的会话
const stopSessionForTab = async (tab: BrowserTab) => {
  if (tab.taskId) {
    await StopTaskById(tab.taskId)
  }
  tab.isSessionActive = false
  tab.isStartingSession = false
  tab.sessionStatusText = '会话已手动中止'
  ElMessage.info(`已结束「${tab.title}」的浏览器会话`)
}

const handleReloadPage = () => {
  if (currentActiveTab.value && currentActiveTab.value.type === 'account') {
    startAppWindowForTab(currentActiveTab.value)
  }
}

const handleGoHome = () => {
  if (currentActiveTab.value && currentActiveTab.value.type === 'account') {
    currentActiveTab.value.url = getPlatformCreatorUrl(currentActiveTab.value.platform)
  }
}

// 账号凭证检测
const checkStatus = async (acc: AccountItem) => {
  try {
    await accountStore.checkAccount(acc)
    const displayName = acc.nickname || acc.account || '当前账号'
    if (acc.isValid) {
      ElMessage.success(`[${displayName}] 凭证状态正常`)
    } else {
      ElMessage.warning(`[${displayName}] 凭证已失效: ${acc.msg || 'invalid'}`)
    }
  } catch (err: any) {
    ElMessage.error(`检测失败: ${err.message || err}`)
  }
}

// 解除账号绑定
const confirmDelete = (platform: string, account: string) => {
  const accItem = accountStore.accounts.find(a => a.platform === platform && a.account === account)
  const displayName = accItem?.nickname || account
  ElMessageBox.confirm(
    `确定要解除绑定账号「${displayName}」吗？解绑后将从本地移除该账号凭证。`,
    '解除绑定确认',
    {
      confirmButtonText: '确认解绑',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    accountStore.removeAccount(platform, account)
    ElMessage.success('账号已成功解绑')
    closeTab(`${platform}:${account}`)
  }).catch(() => {})
}

// 创建新业务分组
const handleCreateGroup = () => {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  accountStore.addGroup(newGroupName.value.trim())
  ElMessage.success(`已创建矩阵分组「${newGroupName.value.trim()}」`)
  newGroupName.value = ''
}

let unlistenLoginSuccess: (() => void) | null = null

// 初始化时：打开第一个账号标签页，若无账号则打开新标签页向导
onMounted(() => {
  if (accountStore.accounts.length > 0) {
    openAccountTab(accountStore.accounts[0])
  } else {
    openNewTab()
  }

  // 监听后端即时上报的登录/凭证就绪事件（无头浏览器依然常驻运行，不关闭！）
  try {
    unlistenLoginSuccess = EventsOn('sau-login-success', (evt: any) => {
      const platform = evt?.platform
      const account = evt?.account || 'auto'
      const taskId = evt?.taskId
      const targetTab = openTabs.value.find(t => (taskId && t.taskId === taskId) || (t.platform === platform && (t.account === account || t.account === 'auto')))
      if (targetTab) {
        targetTab.sessionStatusText = `🟢 检测到登录成功 · 账号 [${evt?.nickname || account}] 凭证已就绪`
        targetTab.isStartingSession = false
        targetTab.isSessionActive = true
        targetTab.account = account
        const updated = accountStore.saveLoggedInAccount(platform, account, evt?.nickname, evt?.finderUid, true)
        targetTab.accountItem = updated
        targetTab.title = `${getPlatformConfig(platform).name} - ${evt?.nickname || account}`
        ElMessage.success(`🎉 账号 [${evt?.nickname || account}] 登录成功且凭证已就绪！`)
      }
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
/* 一体化浏览器工作空间布局 */
.account-browser-workspace {
  display: flex;
  gap: 14px;
  width: 100%;
  height: calc(100vh - 105px);
  min-height: 640px;
  overflow: hidden;
}

/* 👈 左侧：矩阵通讯录侧边栏 (完美适配浅色/深色主题，杜绝白底下看不清文字) */
.account-sidebar-pane {
  width: 320px;
  min-width: 320px;
  max-width: 320px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-card);
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
  color: var(--text-main); /* 适配浅色为深黑，深色为纯白 */
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
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
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

/* 单个账号联系人项 (微信同款，高对比度清晰排版) */
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

.avatar-char {
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1;
}

.avatar-plat-icon {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: var(--primary-color);
}

.avatar-status-dot {
  position: absolute;
  top: 0px;
  left: 0px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--bg-card);
}

.avatar-status-dot.is-valid {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.avatar-status-dot.is-invalid {
  background: #ef4444;
  box-shadow: 0 0 6px #ef4444;
}

.avatar-status-dot.is-unchecked {
  background: #94a3b8;
}

/* 文本信息 (高清晰度对比) */
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
  color: var(--text-main); /* 浅色为极清晰深色，暗黑为纯白 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.contact-platform-tag {
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.contact-second-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.contact-group-name {
  color: var(--text-secondary); /* 保证浅色模式清晰 */
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

/* 👉 右侧：完整拟真浏览器窗口 (Browser Window Pane) */
.browser-window-pane {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* 1. Chrome 风格多标签栏 (Browser Tab Bar) */
.browser-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 38px;
  min-height: 38px;
  background: var(--bg-detail);
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 10px 0 6px;
  gap: 12px;
}

.tab-list-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-end;
  height: 100%;
  overflow-x: auto;
  gap: 2px;
}

.tab-list-wrapper::-webkit-scrollbar {
  display: none;
}

/* 单个浏览器标签页 (拟真 Chrome 标签页形态) */
.browser-tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  max-width: 220px;
  min-width: 120px;
  padding: 0 12px;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  border: 1px solid transparent;
  border-bottom: none;
  transition: all 0.15s ease;
  position: relative;
}

.browser-tab-item:hover {
  background: rgba(125, 125, 125, 0.08);
  color: var(--text-main);
}

.browser-tab-item.active {
  background: var(--bg-card);
  color: var(--text-main);
  font-weight: 700;
  border-color: var(--border-subtle);
  border-bottom: 1px solid var(--bg-card);
  margin-bottom: -1px;
  z-index: 2;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
}

.tab-favicon {
  font-size: 13px;
  display: flex;
  align-items: center;
}

.tab-new-icon {
  color: var(--primary-color);
}

.tab-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-health-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.tab-health-dot.valid {
  background: #10b981;
}

.tab-health-dot.invalid {
  background: #ef4444;
}

.tab-close-btn {
  font-size: 11px;
  border-radius: 50%;
  padding: 2px;
  color: var(--text-muted);
  transition: all 0.2s;
}

.tab-close-btn:hover {
  background: rgba(125, 125, 125, 0.2);
  color: #ef4444;
}

.new-tab-plus-btn {
  width: 28px;
  height: 28px;
  margin-bottom: 3px;
  border: none;
  background: transparent;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.new-tab-plus-btn:hover {
  background: rgba(125, 125, 125, 0.15);
  color: var(--text-main);
}

.browser-window-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.traffic-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  cursor: pointer;
}

.traffic-dot.red { background: #ef4444; }
.traffic-dot.yellow { background: #f59e0b; }
.traffic-dot.green { background: #10b981; }

/* 2. 浏览器导航与地址工具栏 (Omnibox Bar) */
.browser-navigation-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  gap: 12px;
  z-index: 1;
}

.nav-button-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-icon-btn:hover:not(:disabled) {
  background: var(--bg-detail);
  color: var(--text-main);
}

.nav-icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* 拟真 Omnibox 地址栏 */
.browser-omnibox {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 12px;
  transition: all 0.2s;
}

.browser-omnibox:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.ssl-lock-icon {
  color: #10b981;
  font-size: 12px;
}

.omnibox-url-text {
  flex: 1;
  color: var(--text-main);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.omnibox-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.platform-omnibox-tag {
  font-size: 10px;
  font-weight: 700;
  color: #ffffff;
  padding: 1px 6px;
  border-radius: 10px;
}

.omnibox-status-tag {
  height: 18px;
  line-height: 18px;
  padding: 0 6px;
  font-size: 10px;
}

.browser-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.relogin-toolbar-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important;
  border: none !important;
  font-weight: 700;
  color: #fff !important;
}

/* 3. 浏览器视窗主内容区 (Viewport Stage) */
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

/* 原生 Chrome App 沉浸式伴侣控制台样式 */
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

.avatar-char {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
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
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
  border: none !important;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.stop-session-btn {
  font-weight: 700;
}

.appmode-switch-mode {
  font-size: 12px;
}

.launch-screencast-sub-btn {
  margin-top: 10px;
  width: 100%;
  border-style: dashed !important;
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
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
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

/* 新标签页 (New Tab) 接入向导面板 */
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
  font-weight: 700;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* 4. 浏览器底部状态栏 */
.browser-footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  background: var(--bg-detail);
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
}

.footer-status-left {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--primary-color);
  font-weight: 700;
}

.active-pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

/* 分组管理弹窗 */
.group-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-list-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.group-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
