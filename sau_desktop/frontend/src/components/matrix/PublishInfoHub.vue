<template>
  <div class="publish-info-hub">
    <!-- 空状态：若尚未选择任何账号 -->
    <div v-if="activePlatforms.length === 0" class="empty-state-box">
      <p class="empty-text">请先在步骤 ② 选择需要发布的账号</p>
      <el-button size="small" @click="$emit('switch-to-account')">选择账号</el-button>
    </div>

    <!-- 正常工作区 -->
    <div v-else class="hub-container">
      <!-- 高辨识度平台专属图标 Tab 组 -->
      <div class="platform-tabs-bar">
        <div class="tabs-segmented-group">
          <div
            v-for="plat in activePlatforms"
            :key="plat.id"
            class="tab-card-item"
            :class="{ active: currentPlatformId === plat.id }"
            @click="currentPlatformId = plat.id"
          >
            <!-- 平台专属品牌矢量图标 -->
            <PlatformIcon :platform="plat.id" :size="20" class="tab-brand-icon" />

            <!-- 平台名称 -->
            <span class="tab-title">{{ plat.name }}</span>

            <!-- 账号数胶囊标签 -->
            <span class="tab-badge">{{ plat.accountCount }}个账号</span>
          </div>
        </div>
      </div>

      <!-- 单平台配置工作卡片 -->
      <div v-if="currentConfig" class="platform-content-panel">
        <PlatformFormCard
          :key="currentPlatformId"
          :platform="currentPlatformId"
          :override="currentConfig"
          :rule-config="ruleConfig"
          :other-platforms="otherPlatforms"
          :media-list="mediaList"
          :unit-level="unitLevel"
          @sync-to-platforms="handleSyncToPlatforms"
        />
      </div>

      <!-- 批次公共排期控制条 (沉底) -->
      <ScheduleTimingBar
        :rule-config="ruleConfig"
        :media-count="mediaCount"
        @update:rule-config="$emit('update:ruleConfig', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { PLATFORMS } from '../../config/platforms'
import type { PlatformOverrideSetting, BatchRuleConfig, MediaItem } from '../../types/matrix'
import PlatformIcon from './PlatformIcon.vue'
import PlatformFormCard from './PlatformFormCard.vue'
import ScheduleTimingBar from './ScheduleTimingBar.vue'

const props = withDefaults(defineProps<{
  platformConfigs: Record<string, PlatformOverrideSetting>
  ruleConfig: BatchRuleConfig
  selectedAccounts: Array<{ platform: string; account: string; nickname?: string }>
  mediaCount?: number
  mediaList?: MediaItem[]
  unitLevel?: number
}>(), {
  platformConfigs: () => ({}),
  selectedAccounts: () => [],
  mediaCount: 1,
  mediaList: () => [],
  unitLevel: 0
})

const emit = defineEmits<{
  (e: 'update:platformConfigs', val: Record<string, PlatformOverrideSetting>): void
  (e: 'update:ruleConfig', val: BatchRuleConfig): void
  (e: 'switch-to-account'): void
}>()

// 提取已选账号涉及的所有平台
const activePlatforms = computed(() => {
  const map = new Map<string, { id: string; name: string; brandColor: string; accountCount: number }>()
  props.selectedAccounts.forEach(acc => {
    if (!acc.platform) return
    if (!map.has(acc.platform)) {
      const meta = PLATFORMS.find(p => p.id === acc.platform)
      map.set(acc.platform, {
        id: acc.platform,
        name: meta?.name || acc.platform,
        brandColor: meta?.brandColor || '#18191c',
        accountCount: 0
      })
    }
    map.get(acc.platform)!.accountCount++
  })
  return Array.from(map.values())
})

// 当前活跃的平台 Tab
const currentPlatformId = ref<string>('')

// 确保每个涉及的平台都有默认配置对象
function ensurePlatformConfig(platId: string): PlatformOverrideSetting {
  if (!props.platformConfigs[platId]) {
    props.platformConfigs[platId] = {
      isCustomized: true,
      title: '{视频名}',
      desc: '',
      tags: '',
      thumbnail: '',
      thumbnailLandscape: '',
      thumbnailPortrait: '',
      tid: platId === 'bilibili' ? 230 : 0,
      shortTitle: '',
      category: '',
      draft: false,
      schedule: '',
      // 各平台「声明/标注」值域不同：B站 1=自制原创；视频号/抖音/小红书的合法值是中文串或英文枚举。
      // 统一默认「不操作」（空值 → 不传 --declaration → 后端跳过），只有用户主动选择时才发送。
      declaration: platId === 'bilibili' ? '1' : '',
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
  return props.platformConfigs[platId]
}

// 监听平台列表，自适应当前选中的平台
watch(activePlatforms, (list) => {
  if (list.length > 0) {
    list.forEach(p => ensurePlatformConfig(p.id))
    if (!currentPlatformId.value || !list.some(p => p.id === currentPlatformId.value)) {
      currentPlatformId.value = list[0].id
    }
  } else {
    currentPlatformId.value = ''
  }
}, { immediate: true })

// 当前选中平台的配置引用
const currentConfig = computed(() => {
  if (!currentPlatformId.value) return null
  return ensurePlatformConfig(currentPlatformId.value)
})

// 获取当前平台以外的其他平台，供一键同步选择
const otherPlatforms = computed(() => {
  return activePlatforms.value
    .filter(p => p.id !== currentPlatformId.value)
    .map(p => ({ id: p.id, name: p.name }))
})

// 跨平台文案一键同步事件
function handleSyncToPlatforms(payload: {
  sourcePlatform: string
  targetPlatformIds: string[]
  fields: { title: boolean; desc: boolean; tags: boolean }
}) {
  const source = props.platformConfigs[payload.sourcePlatform]
  if (!source) return

  payload.targetPlatformIds.forEach(targetId => {
    const target = ensurePlatformConfig(targetId)
    if (payload.fields.title && source.title) {
      target.title = source.title
    }
    if (payload.fields.desc !== undefined && source.desc) {
      target.desc = source.desc
    }
    if (payload.fields.tags !== undefined && source.tags) {
      target.tags = source.tags
    }
  })
}
</script>

<style scoped>
.publish-info-hub {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.empty-state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 36px 16px;
  background: var(--el-bg-color, #ffffff);
  border: 1px dashed var(--el-border-color, #e4e7ed);
  border-radius: 6px;
  gap: 12px;
}

.empty-text {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary, #909399);
}

.hub-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 高辨识度独立分段 Tab 栏 */
.platform-tabs-bar {
  display: flex;
  align-items: center;
}

.tabs-segmented-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tab-card-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--el-fill-color-light, #f5f7fa);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-card-item:hover {
  background: var(--el-fill-color, #edf0f5);
  border-color: var(--el-border-color, #dcdfe6);
}

.tab-card-item.active {
  background: var(--el-bg-color, #ffffff);
  border-color: var(--el-color-primary, #1890ff);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.tab-brand-icon {
  opacity: 0.85;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.tab-card-item.active .tab-brand-icon {
  opacity: 1;
  transform: scale(1.05);
}

.tab-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular, #606266);
}

.tab-card-item.active .tab-title {
  color: var(--el-text-color-primary, #18191c);
  font-weight: 600;
}

.tab-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--el-text-color-secondary, #909399);
}

.tab-card-item.active .tab-badge {
  background: var(--el-color-primary-light-9, #ecf5ff);
  color: var(--el-color-primary, #1890ff);
}

.platform-content-panel {
  width: 100%;
}
</style>
