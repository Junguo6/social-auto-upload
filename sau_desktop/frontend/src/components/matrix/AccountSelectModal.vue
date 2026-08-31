<template>
  <el-dialog
    :model-value="modelValue"
    title="选择矩阵目标发布账号"
    width="780px"
    append-to-body
    class="account-select-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="account-dialog-body">
      <!-- 1. 顶部搜索与批量快捷操作 -->
      <div class="dialog-filter-row">
        <el-input 
          v-model="searchKeyword" 
          placeholder="搜索账号昵称、UID 或平台名称..." 
          prefix-icon="Search"
          clearable
          style="width: 260px"
        />

        <div class="dialog-quick-buttons">
          <el-button 
            size="small" 
            type="info" 
            plain 
            :loading="accountStore.checkingAll"
            @click="handleCheckAllInModal"
          >
            <el-icon><Refresh /></el-icon> 检查状态
          </el-button>
          <el-button size="small" type="primary" plain @click="selectAllAccounts">全选可用</el-button>
          <el-button size="small" plain @click="invertAccountSelection">反选</el-button>
          <el-button size="small" plain @click="clearAccountSelection">清空</el-button>
        </div>
      </div>

      <!-- 2. 状态健康过滤快捷切换 -->
      <div class="dialog-filter-section">
        <div class="status-filter-row">
          <div class="filter-section-title">
            <el-icon><CircleCheck /></el-icon>
            <span>账号健康状态：</span>
          </div>
          <div class="status-chips-row">
            <div 
              class="status-chip"
              :class="{ active: statusFilter === 'valid_only' }"
              @click="statusFilter = 'valid_only'"
            >
              <span>仅显示可用 ({{ validAccountCount }})</span>
            </div>
            <div 
              class="status-chip"
              :class="{ active: statusFilter === 'all' }"
              @click="statusFilter = 'all'"
            >
              <span>显示全部 ({{ accountStore.accounts.length }})</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. 业务矩阵分组过滤栏 (带一键勾选该分组按钮) -->
      <div class="dialog-filter-section">
        <div class="filter-section-title">
          <el-icon><Folder /></el-icon>
          <span>按业务分组筛选 / 批量选择：</span>
        </div>
        <div class="group-chips-row">
          <div 
            class="group-chip-btn"
            :class="{ active: groupFilter === 'all' }"
            @click="groupFilter = 'all'"
          >
            全部分组 ({{ accountStore.accounts.length }})
          </div>
          <div 
            v-for="grp in accountStore.groups" 
            :key="grp"
            class="group-chip-btn"
            :class="{ active: groupFilter === grp }"
            @click="groupFilter = grp"
          >
            <span>{{ grp }} ({{ getStoreAccountCountByGroup(grp) }})</span>
            <el-tooltip :content="'一键勾选/取消「' + grp + '」的所有可用账号'" placement="top">
              <span class="group-select-trigger" @click.stop="toggleSelectAllInGroup(grp)">
                {{ isAllSelectedInGroup(grp) ? '取消' : '+全选' }}
              </span>
            </el-tooltip>
          </div>
        </div>
      </div>

      <!-- 4. 平台类型过滤栏 -->
      <div class="dialog-filter-section">
        <div class="filter-section-title">
          <el-icon><Grid /></el-icon>
          <span>按媒体平台筛选：</span>
        </div>
        <div class="platform-chips-row">
          <div 
            class="plat-filter-chip"
            :class="{ active: platformFilter === 'all' }"
            @click="platformFilter = 'all'"
          >
            全部平台 ({{ accountStore.accounts.length }})
          </div>
          <div 
            v-for="p in availablePlatformsInStore" 
            :key="p.id"
            class="plat-filter-chip"
            :class="{ active: platformFilter === p.id }"
            @click="platformFilter = p.id"
          >
            <span class="plat-dot" :style="{ background: p.brandColor }"></span>
            <span>{{ p.name }} ({{ getStoreAccountCountByPlat(p.id) }})</span>
          </div>
        </div>
      </div>

      <!-- 5. 账号网格列表 -->
      <div class="modal-account-grid custom-scrollbar">
        <div 
          v-for="acc in filteredAccounts" 
          :key="`${acc.platform}:${acc.account}`"
          class="modal-account-card"
          :class="{ 
            selected: selectedKeys.has(`${acc.platform}:${acc.account}`),
            disabled: isAccountInvalid(acc)
          }"
          @click="handleAccountCardClick(acc)"
        >
          <div class="card-left">
            <div class="plat-avatar" :style="{ background: getPlatformStyle(acc.platform).gradient }">
              <component :is="getPlatformStyle(acc.platform).icon" />
            </div>
            <div class="acc-info">
              <div class="acc-name" :title="acc.nickname || acc.account">
                {{ acc.nickname || acc.account }}
              </div>
              <div class="acc-meta">
                <span class="plat-text" :style="{ color: getPlatformStyle(acc.platform).brandColor }">
                  {{ getPlatformStyle(acc.platform).name }}
                </span>
                <span class="group-pill" v-if="acc.group">{{ acc.group }}</span>

                <!-- 状态健康标签 (去除 emoji，采用微点状态标签) -->
                <span v-if="acc.checked && acc.isValid === false" class="status-pill status-invalid">
                  <span class="status-dot"></span> 凭证失效 (不可选)
                </span>
                <span v-else-if="acc.checked && acc.isValid === true" class="status-pill status-valid">
                  <span class="status-dot"></span> 凭证正常
                </span>
                <span v-else class="status-pill status-unchecked">
                  未检测
                </span>
              </div>
            </div>
          </div>

          <div class="card-right-check">
            <div 
              class="checkbox-circle" 
              :class="{ 
                checked: selectedKeys.has(`${acc.platform}:${acc.account}`),
                disabled: isAccountInvalid(acc)
              }"
            >
              <el-icon v-if="selectedKeys.has(`${acc.platform}:${acc.account}`)"><Check /></el-icon>
            </div>
          </div>
        </div>

        <div v-if="filteredAccounts.length === 0" class="modal-empty-tip">
          未找到匹配的可用平台账号
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer-row">
        <span class="footer-selected-count">
          当前已勾选 <strong>{{ selectedKeys.size }}</strong> / {{ validAccountCount }} 个有效账号
        </span>
        <div class="footer-btns">
          <el-button @click="$emit('update:modelValue', false)">取消</el-button>
          <el-button type="primary" @click="$emit('update:modelValue', false)">确认 (已选 {{ selectedKeys.size }})</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { PLATFORMS, getPlatformConfig } from '../../config/platforms'
import { useAccountStore, AccountItem } from '../../stores/accountStore'

const props = defineProps<{
  modelValue: boolean
  selectedKeys: Set<string>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'select-platform', platformId: string): void
}>()

const accountStore = useAccountStore()

// 过滤状态
const searchKeyword = ref('')
const platformFilter = ref('all')
const groupFilter = ref('all')
const statusFilter = ref<'valid_only' | 'all'>('valid_only')

const isAccountInvalid = (acc: AccountItem) => {
  return acc.checked === true && acc.isValid === false
}

const validAccountCount = computed(() => {
  return accountStore.accounts.filter(a => !isAccountInvalid(a)).length
})

const filteredAccounts = computed(() => {
  return accountStore.accounts.filter(a => {
    if (statusFilter.value === 'valid_only' && isAccountInvalid(a)) {
      return false
    }
    if (groupFilter.value !== 'all' && (a.group || '默认分组') !== groupFilter.value) {
      return false
    }
    if (platformFilter.value !== 'all' && a.platform !== platformFilter.value) {
      return false
    }
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      const matchAcc = a.account.toLowerCase().includes(kw)
      const matchNick = a.nickname ? a.nickname.toLowerCase().includes(kw) : false
      const matchPlat = a.platform.toLowerCase().includes(kw)
      const matchGrp = a.group ? a.group.toLowerCase().includes(kw) : false
      return matchAcc || matchNick || matchPlat || matchGrp
    }
    return true
  })
})

const availablePlatformsInStore = computed(() => {
  const platIds = new Set<string>()
  accountStore.accounts.forEach(a => {
    if (!isAccountInvalid(a)) platIds.add(a.platform)
  })
  return PLATFORMS.filter(p => platIds.has(p.id))
})

const getStoreAccountCountByPlat = (platId: string) => {
  return accountStore.accounts.filter(a => a.platform === platId && !isAccountInvalid(a)).length
}

const getStoreAccountCountByGroup = (groupName: string) => {
  return accountStore.accounts.filter(a => (a.group || '默认分组') === groupName && !isAccountInvalid(a)).length
}

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const handleAccountCardClick = (acc: AccountItem) => {
  if (isAccountInvalid(acc)) {
    ElMessage.warning(`【${acc.nickname || acc.account}】的登录凭证已失效，不可勾选。请前往平台账号管理重新扫码。`)
    return
  }
  const key = `${acc.platform}:${acc.account}`
  if (props.selectedKeys.has(key)) {
    props.selectedKeys.delete(key)
  } else {
    props.selectedKeys.add(key)
    emit('select-platform', acc.platform)
  }
}

const selectAllAccounts = () => {
  props.selectedKeys.clear()
  accountStore.accounts.forEach(a => {
    if (!isAccountInvalid(a)) {
      props.selectedKeys.add(`${a.platform}:${a.account}`)
    }
  })
  ElMessage.success(`已全选所有可用账号 (${props.selectedKeys.size})`)
}

const invertAccountSelection = () => {
  accountStore.accounts.forEach(a => {
    if (isAccountInvalid(a)) return
    const key = `${a.platform}:${a.account}`
    if (props.selectedKeys.has(key)) {
      props.selectedKeys.delete(key)
    } else {
      props.selectedKeys.add(key)
    }
  })
}

const clearAccountSelection = () => {
  props.selectedKeys.clear()
}

const isAllSelectedInGroup = (groupName: string) => {
  const groupValidAccs = accountStore.accounts.filter(a => (a.group || '默认分组') === groupName && !isAccountInvalid(a))
  if (groupValidAccs.length === 0) return false
  return groupValidAccs.every(a => props.selectedKeys.has(`${a.platform}:${a.account}`))
}

const toggleSelectAllInGroup = (groupName: string) => {
  const groupValidAccs = accountStore.accounts.filter(a => (a.group || '默认分组') === groupName && !isAccountInvalid(a))
  if (groupValidAccs.length === 0) {
    ElMessage.info(`「${groupName}」暂无可用的有效账号`)
    return
  }
  const allSelected = isAllSelectedInGroup(groupName)
  groupValidAccs.forEach(a => {
    const key = `${a.platform}:${a.account}`
    if (allSelected) {
      props.selectedKeys.delete(key)
    } else {
      props.selectedKeys.add(key)
    }
  })
}

const handleCheckAllInModal = async () => {
  try {
    await accountStore.checkAllAccounts()
    // 剔除已失效账号
    props.selectedKeys.forEach(key => {
      const [plat, acc] = key.split(':')
      const found = accountStore.accounts.find(a => a.platform === plat && a.account === acc)
      if (found && isAccountInvalid(found)) {
        props.selectedKeys.delete(key)
      }
    })
    ElMessage.success('全网矩阵账号状态检查完成')
  } catch (err: any) {
    ElMessage.error(`检测异常: ${err.message || err}`)
  }
}
</script>

<style scoped>
.account-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 520px;
}

.dialog-filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-filter-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.status-filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.1);
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.status-chips-row {
  display: flex;
  gap: 6px;
}

.status-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 5px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.status-chip.active {
  background: rgba(16, 185, 129, 0.15);
  border-color: #10b981;
  color: #10b981;
  font-weight: 600;
}

.filter-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 5px;
}

.group-chips-row, .platform-chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.group-chip-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.group-chip-btn:hover {
  border-color: var(--border-highlight);
  color: var(--text-main);
}

.group-chip-btn.active {
  background: rgba(168, 85, 247, 0.15);
  border-color: #a855f7;
  color: #f8fafc;
  font-weight: 600;
}

.group-select-trigger {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  cursor: pointer;
}

.group-select-trigger:hover {
  background: #6366f1;
  color: #fff;
}

.plat-filter-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.plat-filter-chip:hover {
  border-color: var(--border-highlight);
  color: var(--text-main);
}

.plat-filter-chip.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--primary-light);
  color: var(--text-main);
  font-weight: 600;
}

.plat-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.modal-account-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  overflow-y: auto;
  max-height: 240px;
  padding-right: 4px;
  margin-top: 2px;
}

.modal-account-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.modal-account-card:hover:not(.disabled) {
  border-color: var(--border-highlight);
  background: rgba(255, 255, 255, 0.03);
}

.modal-account-card.selected {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--primary-light);
}

.modal-account-card.disabled {
  opacity: 0.5;
  background: rgba(239, 68, 68, 0.03);
  border-color: rgba(239, 68, 68, 0.2);
  cursor: not-allowed;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.plat-avatar {
  width: 26px;
  height: 26px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}

.acc-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.acc-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.acc-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 1px;
  font-size: 10px;
}

.plat-text {
  font-weight: 600;
}

.group-pill {
  color: #c084fc;
  background: rgba(168, 85, 247, 0.1);
  padding: 0 4px;
  border-radius: 2px;
}

.status-pill {
  font-size: 9px;
  padding: 0 4px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  gap: 3px;
}

.status-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
}

.status-invalid {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}
.status-invalid .status-dot {
  background: #ef4444;
}

.status-valid {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}
.status-valid .status-dot {
  background: #10b981;
}

.status-unchecked {
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
}

.checkbox-circle {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--border-highlight);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #fff;
  transition: all 0.15s ease;
}

.checkbox-circle.checked {
  background: #6366f1;
  border-color: #6366f1;
}

.checkbox-circle.disabled {
  border-color: rgba(255, 255, 255, 0.15);
  background: transparent;
}

.modal-empty-tip {
  grid-column: span 2;
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 12px;
}

.modal-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-selected-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.footer-selected-count strong {
  color: #818cf8;
}
</style>
