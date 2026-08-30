<template>
  <div class="account-workspace">
    <!-- 1. 顶部操作与筛选大栏 -->
    <div class="header-section">
      <div class="header-main">
        <div class="title-box">
          <h2 class="section-title">全网自媒体矩阵账号中心</h2>
          <span class="section-subtitle">支持按平台分类与业务分组双重维度矩阵隔离与 Cookie 凭证检测</span>
        </div>

        <div class="header-actions">
          <el-button size="default" type="info" plain @click="showGroupDialog = true">
            <el-icon><FolderAdd /></el-icon>
            <span>管理/新建业务分组</span>
          </el-button>
          <el-button size="default" type="primary" class="gradient-btn" @click="showLoginDialog = true">
            <el-icon><Plus /></el-icon>
            <span>扫码添加新平台账号</span>
          </el-button>
        </div>
      </div>

      <!-- 双维度过滤卡片 -->
      <div class="filter-control-card glass-card">
        <!-- 维度一：平台快速切换胶囊 -->
        <div class="filter-row">
          <span class="filter-label">所属平台：</span>
          <div class="platform-chips">
            <div 
              class="plat-chip" 
              :class="{ active: currentPlatformFilter === 'all' }"
              @click="currentPlatformFilter = 'all'"
            >
              <span>全部平台</span>
              <el-tag size="small" type="info" round class="count-tag">{{ accountStore.accounts.length }}</el-tag>
            </div>

            <div 
              v-for="plat in availablePlatforms" 
              :key="plat.id"
              class="plat-chip"
              :class="{ active: currentPlatformFilter === plat.id }"
              @click="currentPlatformFilter = plat.id"
            >
              <div class="mini-plat-icon" :style="{ background: plat.gradient }">
                <el-icon><component :is="plat.icon" /></el-icon>
              </div>
              <span>{{ plat.name }}</span>
              <el-tag size="small" type="info" round class="count-tag">{{ getPlatformCount(plat.id) }}</el-tag>
            </div>
          </div>
        </div>

        <!-- 维度二：业务矩阵分组与搜索 -->
        <div class="filter-row sub-row">
          <div class="group-tabs-wrap">
            <span class="filter-label">业务分组：</span>
            <el-radio-group v-model="currentGroupFilter" size="small">
              <el-radio-button label="all">全部分组 ({{ accountStore.accounts.length }})</el-radio-button>
              <el-radio-button 
                v-for="grp in accountStore.groups" 
                :key="grp" 
                :label="grp"
              >
                {{ grp }} ({{ getGroupCount(grp) }})
              </el-radio-button>
            </el-radio-group>
          </div>

          <div class="search-box">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索账号名称..." 
              prefix-icon="Search" 
              clearable 
              size="small"
              style="width: 200px"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 账号卡片网格列表 -->
    <div class="account-grid-container">
      <div v-if="filteredAccounts.length === 0" class="empty-state glass-card">
        <el-icon class="empty-icon"><UserFilled /></el-icon>
        <span class="empty-title">未找到匹配条件的矩阵账号</span>
        <span class="empty-desc">您可以点击上方「扫码添加新平台账号」绑定新矩阵账号</span>
      </div>

      <div 
        v-for="acc in filteredAccounts" 
        :key="acc.platform + acc.account"
        class="account-card glass-card"
        :style="{ '--plat-gradient': getPlatformStyle(acc.platform).gradient }"
      >
        <!-- 顶部平台标识与操作 -->
        <div class="card-top">
          <div class="plat-badge" :style="{ background: getPlatformStyle(acc.platform).gradient }">
            <el-icon><component :is="getPlatformStyle(acc.platform).icon" /></el-icon>
            <span class="plat-name">{{ getPlatformStyle(acc.platform).name }}</span>
          </div>

          <div class="card-actions">
            <el-button 
              size="small" 
              type="primary" 
              link 
              :loading="acc.loading"
              @click="checkStatus(acc)"
            >
              检测状态
            </el-button>
            <el-button size="small" type="danger" link @click="confirmDelete(acc.platform, acc.account)">
              解绑
            </el-button>
          </div>
        </div>

        <!-- 账号主体信息 -->
        <div class="card-body">
          <div class="account-name-title">{{ acc.nickname || acc.account }}</div>
          <div class="account-meta">
            <span class="status-dot" :class="acc.isValid ? 'valid' : 'invalid'"></span>
            <span class="status-text">{{ acc.checked ? (acc.isValid ? '登录凭证有效' : '凭证失效需重新登录') : '待检测' }}</span>
            <el-tag v-if="acc.finderUid" size="small" type="info" class="uid-tag">ID: {{ acc.finderUid }}</el-tag>
          </div>
        </div>

        <!-- 底部业务分组快速分配下拉 -->
        <div class="card-footer">
          <div class="group-select-row">
            <span class="footer-label">矩阵业务组:</span>
            <el-select 
              :model-value="acc.group || '默认分组'" 
              size="small" 
              style="width: 140px"
              @change="(val: string) => accountStore.updateAccountGroup(acc.platform, acc.account, val)"
            >
              <el-option 
                v-for="grp in accountStore.groups" 
                :key="grp" 
                :label="grp" 
                :value="grp" 
              />
            </el-select>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 扫码添加新账号弹窗 -->
    <el-dialog 
      v-model="showLoginDialog" 
      title="扫码添加绑定新平台账号" 
      width="480px"
      append-to-body
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="选择目标媒体平台">
          <el-select v-model="loginForm.platform" placeholder="选择需要授权的平台" style="width: 100%">
            <el-option 
              v-for="p in PLATFORMS" 
              :key="p.id" 
              :label="p.name" 
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="自定义账号别名 / 备注 (可选)">
          <el-input 
            v-model="loginForm.account" 
            placeholder="选填：留空将全自动提取平台真实昵称与唯一UID" 
            clearable
          />
        </el-form-item>

        <el-form-item label="归属业务分组">
          <el-select v-model="loginForm.group" style="width: 100%">
            <el-option 
              v-for="grp in accountStore.groups" 
              :key="grp" 
              :label="grp" 
              :value="grp" 
            />
          </el-select>
        </el-form-item>

        <div class="login-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>点击开始后将拉起 Chrome 浏览器页面，请使用对应 App 扫码登录，完成后将自动读取平台昵称并持久化凭证至本地。</span>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="showLoginDialog = false">取消</el-button>
        <el-button type="primary" class="gradient-btn" :loading="isLoggingIn" @click="handleStartLogin">
          拉起浏览器并扫码登录
        </el-button>
      </template>
    </el-dialog>


    <!-- 4. 管理/新建分组弹窗 -->
    <el-dialog
      v-model="showGroupDialog"
      title="业务矩阵分组管理"
      width="420px"
      append-to-body
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
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PLATFORMS, getPlatformConfig } from '../config/platforms'
import { useAccountStore, AccountItem } from '../stores/accountStore'

const accountStore = useAccountStore()

const currentPlatformFilter = ref('all')
const currentGroupFilter = ref('all')
const searchKeyword = ref('')

const showLoginDialog = ref(false)
const isLoggingIn = ref(false)
const showGroupDialog = ref(false)
const newGroupName = ref('')

const loginForm = reactive({
  platform: 'douyin',
  account: '',
  group: '美食矩阵组'
})

const availablePlatforms = computed(() => {
  return PLATFORMS
})

const getPlatformCount = (platId: string) => {
  return accountStore.accounts.filter(a => a.platform === platId).length
}

const getGroupCount = (groupName: string) => {
  return accountStore.accounts.filter(a => a.group === groupName).length
}

// 综合双维度筛选 + 关键字模糊匹配 (支持匹配昵称、UID或底层标识)
const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(acc => {
    // 平台过滤
    if (currentPlatformFilter.value !== 'all' && acc.platform !== currentPlatformFilter.value) {
      return false
    }
    // 矩阵分组过滤
    if (currentGroupFilter.value !== 'all' && acc.group !== currentGroupFilter.value) {
      return false
    }
    // 搜索关键字
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

const checkStatus = async (acc: AccountItem) => {
  try {
    await accountStore.checkAccount(acc)
    const displayName = acc.nickname || acc.account || acc.finderUid || '当前账号'
    if (acc.isValid) {
      ElMessage.success(`[${displayName}] 凭证状态有效`)
    } else {
      ElMessage.warning(`[${displayName}] 凭证已失效: ${acc.msg || 'invalid'}`)
    }
  } catch (err: any) {
    ElMessage.error(`检测失败: ${err.message || err}`)
  }
}

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
  }).catch(() => {})
}

const handleStartLogin = async () => {
  isLoggingIn.value = true
  try {
    ElMessage.info('已拉起授权浏览器，请在弹出窗口中完成扫码登录...')
    const res: any = await accountStore.loginAccount(loginForm.platform, loginForm.account.trim(), loginForm.group, true)
    const displayNick = res.nickname || res.account || loginForm.account || '新账号'
    ElMessage.success(`🎉 账号「${displayNick}」授权登录成功，已自动保存凭证！`)
    showLoginDialog.value = false
    loginForm.account = ''
  } catch (err: any) {
    ElMessage.error(`登录异常: ${err.message || err}`)
  } finally {
    isLoggingIn.value = false
  }
}


const handleCreateGroup = () => {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  accountStore.addGroup(newGroupName.value.trim())
  ElMessage.success(`已创建矩阵分组「${newGroupName.value.trim()}」`)
  newGroupName.value = ''
}
</script>

<style scoped>
.account-workspace {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.header-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
}

.section-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  display: block;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 双维度过滤卡片 */
.filter-control-card {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-radius: 12px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-row.sub-row {
  justify-content: space-between;
  border-top: 1px dashed var(--border-subtle);
  padding-top: 12px;
}

.group-tabs-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  white-space: nowrap;
}

.platform-chips {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.plat-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.plat-chip:hover {
  border-color: var(--border-highlight);
}

.plat-chip.active {
  background: rgba(99, 102, 241, 0.12);
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

.mini-plat-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
}

.count-tag {
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
  font-size: 10px;
}

/* 账号卡片网格 */
.account-grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: var(--text-disabled);
  margin-bottom: 12px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.empty-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

.account-card {
  padding: 16px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.account-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.plat-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.account-name-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.account-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-dot.valid {
  background: var(--status-success);
  box-shadow: 0 0 6px var(--status-success);
}

.status-dot.invalid {
  background: var(--status-danger);
  box-shadow: 0 0 6px var(--status-danger);
}

.status-text {
  font-size: 11px;
  color: var(--text-muted);
}

.card-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 10px;
}

.group-select-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-label {
  font-size: 11px;
  color: var(--text-muted);
}

/* 弹窗样式 */
.login-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: 10px;
}

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
