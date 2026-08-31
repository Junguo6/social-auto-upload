<template>
  <div class="platform-icon-dock">
    <!-- 1. 有已选平台时：展示动态过滤的精选平台 Dock -->
    <div v-if="displayedPlatforms.length > 0" class="dock-inner">
      <div class="dock-platforms-scroll custom-scrollbar">
        <el-tooltip
          v-for="plat in displayedPlatforms"
          :key="plat.id"
          :content="getPlatformTooltip(plat)"
          placement="top"
          :show-after="150"
        >
          <div
            class="dock-icon-item"
            :class="{
              active: modelValue === plat.id,
              has_accounts: getPlatformSelectedCount(plat.id) > 0,
              is_customized: platformOverrides[plat.id]?.isCustomized
            }"
            @click="$emit('update:modelValue', plat.id)"
          >
            <!-- 平台专属品牌图标 -->
            <div 
              class="icon-glyph-box"
              :style="{
                background: modelValue === plat.id ? plat.gradient : 'transparent',
                color: modelValue === plat.id ? '#ffffff' : plat.brandColor
              }"
            >
              <component :is="plat.icon" />
            </div>

            <!-- 底部平台微标题 -->
            <span class="icon-label">{{ plat.name }}</span>

            <!-- 右上角已选账号角标 -->
            <span class="dock-badge" v-if="getPlatformSelectedCount(plat.id) > 0">
              {{ getPlatformSelectedCount(plat.id) }}
            </span>

            <!-- 左上角独立定制状态光标 -->
            <span class="dock-custom-dot" v-if="platformOverrides[plat.id]?.isCustomized" title="已开启专属定制"></span>

            <!-- 激活态下划光条 -->
            <div class="active-indicator" v-if="modelValue === plat.id" :style="{ background: plat.brandColor }"></div>
          </div>
        </el-tooltip>
      </div>

      <!-- 右侧：平台展示模式切换 (已选平台 vs 全网平台) -->
      <div class="dock-filter-toggle">
        <el-tooltip :content="showAllPlatforms ? '切换为仅展示已选账号的平台' : '切换为展示全部 10 大平台'" placement="top">
          <button 
            class="filter-toggle-btn"
            :class="{ 'show-all': showAllPlatforms }"
            @click="showAllPlatforms = !showAllPlatforms"
          >
            <el-icon><Filter /></el-icon>
            <span>{{ showAllPlatforms ? '全部平台' : `已选平台 (${activePlatformIds.length})` }}</span>
          </button>
        </el-tooltip>
      </div>
    </div>

    <!-- 2. 暂未勾选任何账号时的空状态 -->
    <div v-else class="dock-empty-box">
      <div class="empty-left">
        <el-icon class="empty-icon"><InfoFilled /></el-icon>
        <span>尚未勾选任何发布账号，平台标签将根据所选账号自动生成</span>
      </div>
      <div class="empty-actions">
        <el-button size="small" type="primary" plain @click="$emit('open-account-modal')">
          <el-icon><UserFilled /></el-icon> 选择矩阵账号
        </el-button>
        <el-button size="small" link type="info" @click="showAllPlatforms = true">
          查看全部平台
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { PLATFORMS } from '../../config/platforms'
import type { PlatformOverrideSetting } from '../../types/matrix'

const props = defineProps<{
  modelValue: string
  platformOverrides: Record<string, PlatformOverrideSetting>
  selectedTargetKeys: Set<string>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'open-account-modal'): void
}>()

// 是否强制显示全部平台
const showAllPlatforms = ref(false)

const getPlatformSelectedCount = (platformId: string) => {
  let count = 0
  props.selectedTargetKeys.forEach(k => {
    if (k.startsWith(platformId + ':')) count++
  })
  return count
}

const activePlatformIds = computed(() => {
  const ids: string[] = []
  PLATFORMS.forEach(p => {
    if (getPlatformSelectedCount(p.id) > 0) {
      ids.push(p.id)
    }
  })
  return ids
})

// 根据当前勾选的账号动态计算展示的平台列表
const displayedPlatforms = computed(() => {
  if (showAllPlatforms.value) {
    return PLATFORMS
  }
  return PLATFORMS.filter(p => activePlatformIds.value.includes(p.id))
})

// 监听展示平台变化，如果当前激活的平台不在展示列表中，自动切换到第一个可用平台
watch(displayedPlatforms, (newList) => {
  if (newList.length > 0) {
    const isCurrentStillActive = newList.some(p => p.id === props.modelValue)
    if (!isCurrentStillActive) {
      emit('update:modelValue', newList[0].id)
    }
  }
}, { immediate: true })

const getPlatformTooltip = (plat: any) => {
  const count = getPlatformSelectedCount(plat.id)
  const isCust = props.platformOverrides[plat.id]?.isCustomized
  let tip = `${plat.name}`
  if (count > 0) {
    tip += ` · 已选 ${count} 个账号`
  } else {
    tip += ` · 未选账号`
  }
  if (isCust) {
    tip += ' (独立定制中)'
  } else {
    tip += ' (同步全局)'
  }
  return tip
}
</script>

<style scoped>
.platform-icon-dock {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.12);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  min-height: 52px;
}

.dock-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 10px;
}

.dock-platforms-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow-x: auto;
}

.dock-icon-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 10px 3px;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 54px;
  user-select: none;
  background: transparent;
  border: 1px solid transparent;
}

.dock-icon-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--border-subtle);
  transform: translateY(-1px);
}

.dock-icon-item.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.25);
}

.icon-glyph-box {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  transition: all 0.15s ease;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.dock-icon-item.active .icon-glyph-box {
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.35);
  border-color: rgba(255, 255, 255, 0.15);
}

.icon-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 3px;
  font-weight: 500;
  white-space: nowrap;
  letter-spacing: -0.2px;
}

.dock-icon-item.active .icon-label {
  color: var(--text-main);
  font-weight: 600;
}

.dock-badge {
  position: absolute;
  top: 1px;
  right: 4px;
  font-size: 9px;
  font-weight: 700;
  background: #6366f1;
  color: #fff;
  padding: 0 4px;
  height: 13px;
  line-height: 13px;
  border-radius: 6px;
}

.dock-custom-dot {
  position: absolute;
  top: 3px;
  left: 5px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 5px #f59e0b;
}

.active-indicator {
  position: absolute;
  bottom: 0;
  left: 15%;
  right: 15%;
  height: 2px;
  border-radius: 2px;
}

.dock-filter-toggle {
  flex-shrink: 0;
}

.filter-toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-main);
}

.filter-toggle-btn.show-all {
  color: #818cf8;
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.08);
}

.dock-empty-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 2px 4px;
}

.empty-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 15px;
  color: #f59e0b;
}

.empty-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
