<template>
  <div class="platform-custom-content">
    <!-- 1. 平台头部导航与信息栏 -->
    <div class="custom-card-header">
      <div class="custom-plat-title">
        <div class="plat-icon-circle" :style="{ background: platformConfig.gradient }">
          <component :is="platformConfig.icon" />
        </div>
        <div class="title-meta">
          <div class="name-row">
            <span class="name">{{ platformConfig.name }} 差异化配置</span>
            <span class="account-tag-list" v-if="accountList.length > 0">
              {{ accountList.length }} 个账号
            </span>
          </div>
          <div class="breadcrumb-context">
            <span>正在配置: </span>
            <span class="context-plat">{{ platformConfig.name }}</span>
            <el-icon class="context-sep"><ArrowRight /></el-icon>
            <span class="context-target" :class="{ 'is-account': currentSubTarget !== '__platform__' }">
              {{ currentSubTarget === '__platform__' ? '平台统一配置 (默认作用于所有账号)' : getCurrentAccountDisplayName() }}
            </span>
            <span v-if="currentEditingOverride.isCustomized" class="custom-badge-pill">
              独立定制
            </span>
            <span v-else class="inherit-badge-pill">
              跟随{{ currentSubTarget === '__platform__' ? '全局模板' : '平台统一配置' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 右侧魔术同步与独立定制开关 -->
      <div class="header-right-actions">
        <el-button 
          size="small" 
          type="primary" 
          plain 
          class="sync-action-btn"
          @click="$emit('open-sync-modal', {
            sourceDesc: `${platformConfig.name} - ${currentSubTarget === '__platform__' ? '平台统一配置' : getCurrentAccountDisplayName()}`,
            currentPlatform: platformId,
            currentAccountKey: currentSubTarget === '__platform__' ? '__platform__' : `${platformId}:${currentSubTarget}`
          })"
        >
          <el-icon><CopyDocument /></el-icon> 同步配置至其他账号...
        </el-button>

        <div class="sync-switch-box">
          <span class="switch-label">{{ currentEditingOverride.isCustomized ? '独立定制' : '实时跟随' }}</span>
          <el-switch
            v-model="currentEditingOverride.isCustomized"
            size="small"
            style="--el-switch-on-color: #6366f1; --el-switch-off-color: #10b981;"
          />
        </div>
      </div>
    </div>

    <!-- 2. 二级账号胶囊分段栏 (Account Segmented Pill Bar) -->
    <div class="account-segmented-dock" v-if="accountList.length > 0">
      <div class="segmented-inner custom-scrollbar">
        <!-- 平台统一默认项 -->
        <div 
          class="account-pill-item"
          :class="{ 
            active: currentSubTarget === '__platform__',
            is_customized: platformOverride.isCustomized 
          }"
          @click="currentSubTarget = '__platform__'"
        >
          <el-icon><Grid /></el-icon>
          <span>平台统一配置</span>
          <span class="dot-indicator" v-if="platformOverride.isCustomized" title="已开启平台定制"></span>
        </div>

        <!-- 当前平台下的具体账号列表 -->
        <div
          v-for="acc in accountList"
          :key="acc.account"
          class="account-pill-item"
          :class="{
            active: currentSubTarget === acc.account,
            is_customized: accountOverrides[`${platformId}:${acc.account}`]?.isCustomized
          }"
          @click="currentSubTarget = acc.account"
        >
          <el-icon><User /></el-icon>
          <span class="pill-name" :title="acc.nickname || acc.account">
            {{ acc.nickname || acc.account }}
          </span>
          <span 
            class="dot-indicator" 
            v-if="accountOverrides[`${platformId}:${acc.account}`]?.isCustomized" 
            title="该账号已独立定制"
          ></span>
        </div>
      </div>
    </div>

    <!-- 3. A: 实时跟随模式简明提示 -->
    <div v-if="!currentEditingOverride.isCustomized" class="sync-preview-banner">
      <div class="sync-banner-left">
        <el-icon class="pulse-icon"><Connection /></el-icon>
        <div class="sync-banner-text">
          <span class="sync-title">
            当前处于「实时跟随{{ currentSubTarget === '__platform__' ? '全局主模板' : '平台统一配置' }}」模式
          </span>
          <span class="sync-sub">
            {{ currentSubTarget === '__platform__' ? '将默认使用全局主模板的标题、文案、媒体素材与标签。' : `【${getCurrentAccountDisplayName()}】将自动继承当前平台的统一配置。` }}
          </span>
        </div>
      </div>
      <el-button size="small" type="primary" plain class="switch-custom-btn" @click="currentEditingOverride.isCustomized = true">
        <el-icon><EditPen /></el-icon> 开启专属定制
      </el-button>
    </div>

    <!-- 4. B: 独立定制模式编辑区 -->
    <div v-else class="custom-editor-scroll custom-scrollbar">
      <!-- 专属标题 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text">专属作品标题</span>
          <el-button size="small" link type="primary" @click="currentEditingOverride.title = getInheritedTitle()">
            复制继承标题
          </el-button>
        </div>
        <el-input 
          v-model="currentEditingOverride.title" 
          :placeholder="`留空自动继承: ${getInheritedTitle() || '全局标题'}`"
          clearable
          class="stylish-input"
        />
      </div>

      <!-- 专属正文描述 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text">专属正文描述 / 文案</span>
          <el-button size="small" link type="primary" @click="currentEditingOverride.desc = getInheritedDesc()">
            复制继承文案
          </el-button>
        </div>
        <el-input 
          v-model="currentEditingOverride.desc" 
          type="textarea" 
          :rows="3" 
          :placeholder="`填写专属正文简介 (留空将自动继承)`"
          class="stylish-textarea"
        />
      </div>

      <!-- 专属话题标签 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text">专属话题标签</span>
          <el-button size="small" link type="primary" @click="currentEditingOverride.tags = getInheritedTags()">
            复制继承标签
          </el-button>
        </div>
        <el-input 
          v-model="currentEditingOverride.tags" 
          :placeholder="`以逗号分隔专属热门话题 (留空将继承: ${getInheritedTags() || '无'})`"
          clearable
          class="stylish-input"
        />
      </div>

      <!-- 专属主封面与发布时机 -->
      <div class="form-section form-row-2">
        <div class="form-col">
          <div class="section-label"><span class="label-text">专属封面图</span></div>
          <el-input v-model="currentEditingOverride.thumbnail" placeholder="留空自动继承" clearable class="stylish-input">
            <template #append>
              <el-button @click="choosePlatformCover"><el-icon><Picture /></el-icon></el-button>
            </template>
          </el-input>
        </div>

        <div class="form-col">
          <div class="section-label"><span class="label-text">专属发布时机</span></div>
          <el-date-picker 
            v-model="currentEditingOverride.schedule"
            type="datetime"
            placeholder="留空自动继承"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            class="stylish-datepicker"
          />
        </div>
      </div>

      <!-- 5. 平台专属特性参数扩展区 (即插即用独立组件) -->
      <div class="platform-exclusive-box">
        <div class="exclusive-title">
          <el-icon><Setting /></el-icon>
          <span>{{ platformConfig.name }} 专属高级特性配置</span>
        </div>

        <TencentForm v-if="platformId === 'tencent'" :override="currentEditingOverride" />
        <BilibiliForm v-else-if="platformId === 'bilibili'" :override="currentEditingOverride" />
        <DouyinForm v-else-if="platformId === 'douyin'" :override="currentEditingOverride" />
        <XiaohongshuForm v-else-if="platformId === 'xiaohongshu'" :override="currentEditingOverride" />
        <GenericForm v-else :override="currentEditingOverride" />
      </div>

      <!-- 底部还原按钮 -->
      <div class="custom-reset-row">
        <el-button size="small" type="info" link @click="resetCurrentTargetToSync">
          <el-icon><RefreshLeft /></el-icon> 放弃当前定制并还原为实时跟随
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import { SelectLocalFile } from '../../../wailsjs/go/main/App'
import type { MasterForm, PlatformOverrideSetting } from '../../types/matrix'

// 平台专属表单子组件
import TencentForm from './platforms/TencentForm.vue'
import DouyinForm from './platforms/DouyinForm.vue'
import BilibiliForm from './platforms/BilibiliForm.vue'
import XiaohongshuForm from './platforms/XiaohongshuForm.vue'
import GenericForm from './platforms/GenericForm.vue'

const props = defineProps<{
  platformId: string
  platformOverride: PlatformOverrideSetting
  accountOverrides: Record<string, PlatformOverrideSetting>
  masterForm: MasterForm
  accountList: Array<{ account: string; nickname?: string }>
}>()

defineEmits<{
  (e: 'open-sync-modal', payload: { sourceDesc: string; currentPlatform: string; currentAccountKey: string }): void
}>()

// 二级子目标选择：'__platform__' 为平台统一配置；具体 account 为单个账号
const currentSubTarget = ref<string>('__platform__')

// 切换平台时重置为 '__platform__'
watch(() => props.platformId, () => {
  currentSubTarget.value = '__platform__'
})

const platformConfig = computed(() => {
  return getPlatformConfig(props.platformId)
})

// 确保账号独立配置存在
const ensureAccountOverrideExists = (account: string): PlatformOverrideSetting => {
  const key = `${props.platformId}:${account}`
  if (!props.accountOverrides[key]) {
    props.accountOverrides[key] = {
      isCustomized: false,
      title: '',
      desc: '',
      tags: '',
      thumbnail: '',
      thumbnailLandscape: '',
      thumbnailPortrait: '',
      tid: props.platformId === 'bilibili' ? 230 : 0,
      shortTitle: '',
      category: '',
      draft: false,
      schedule: '',
      declaration: '',
      collection: '',
      productLink: '',
      productTitle: '',
      visibility: '0',
      playlist: '',
      bgm: '',
      note: '',
      notef: ''
    }
  }
  return props.accountOverrides[key]
}

// 当前正在编辑的配置对象
const currentEditingOverride = computed<PlatformOverrideSetting>(() => {
  if (currentSubTarget.value === '__platform__') {
    return props.platformOverride
  }
  return ensureAccountOverrideExists(currentSubTarget.value)
})

const getCurrentAccountDisplayName = () => {
  const found = props.accountList.find(a => a.account === currentSubTarget.value)
  return found?.nickname || currentSubTarget.value
}

// 获取继承值
const getInheritedTitle = () => {
  if (currentSubTarget.value === '__platform__') {
    return props.masterForm.title
  }
  return props.platformOverride.title || props.masterForm.title
}

const getInheritedDesc = () => {
  if (currentSubTarget.value === '__platform__') {
    return props.masterForm.desc
  }
  return props.platformOverride.desc || props.masterForm.desc
}

const getInheritedTags = () => {
  if (currentSubTarget.value === '__platform__') {
    return props.masterForm.tags
  }
  return props.platformOverride.tags || props.masterForm.tags
}

const resetCurrentTargetToSync = () => {
  currentEditingOverride.value.isCustomized = false
  ElMessage.info('已将当前配置还原为实时跟随模式')
}

const choosePlatformCover = async () => {
  try {
    const file = await SelectLocalFile(`选择专属封面`, ['*.png', '*.jpg', '*.jpeg', '*.webp'])
    if (file) {
      currentEditingOverride.value.thumbnail = file
      ElMessage.success(`已设置专属封面`)
    }
  } catch (err: any) {
    ElMessage.error(`选择封面失败: ${err.message || err}`)
  }
}
</script>

<style scoped>
.platform-custom-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.custom-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.03);
  flex-shrink: 0;
}

.custom-plat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plat-icon-circle {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
}

.title-meta .name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-meta .name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.account-tag-list {
  font-size: 10px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.05);
  padding: 1px 6px;
  border-radius: 3px;
}

.breadcrumb-context {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.context-plat {
  color: var(--text-secondary);
}

.context-sep {
  font-size: 9px;
  color: var(--text-muted);
}

.context-target {
  color: var(--primary-light);
  font-weight: 600;
}

.context-target.is-account {
  color: #a855f7;
}

.custom-badge-pill {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #818cf8;
  font-weight: 600;
  margin-left: 4px;
}

.inherit-badge-pill {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  color: #10b981;
  font-weight: 500;
  margin-left: 4px;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sync-action-btn {
  font-size: 11px;
  height: 28px;
  border-radius: 5px;
}

.sync-switch-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.switch-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.account-segmented-dock {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.08);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.segmented-inner {
  display: flex;
  align-items: center;
  gap: 5px;
  overflow-x: auto;
  width: 100%;
}

.account-pill-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  user-select: none;
  position: relative;
}

.account-pill-item:hover {
  border-color: var(--border-highlight);
  color: var(--text-main);
}

.account-pill-item.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--primary-light);
  color: #fff;
  font-weight: 600;
}

.pill-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dot-indicator {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #818cf8;
}

.sync-preview-banner {
  margin: 14px 16px;
  padding: 14px 16px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sync-banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pulse-icon {
  font-size: 18px;
  color: #10b981;
}

.sync-banner-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sync-title {
  font-size: 12px;
  font-weight: 600;
  color: #10b981;
}

.sync-sub {
  font-size: 11px;
  color: var(--text-secondary);
}

.switch-custom-btn {
  font-size: 11px;
  height: 28px;
}

.custom-editor-scroll {
  padding: 14px 16px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-text {
  color: var(--text-main);
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.platform-exclusive-box {
  border: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  padding: 12px;
}

.exclusive-title {
  font-size: 12px;
  font-weight: 700;
  color: #818cf8;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.custom-reset-row {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}
</style>
