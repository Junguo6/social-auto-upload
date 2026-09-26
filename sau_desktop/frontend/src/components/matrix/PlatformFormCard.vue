<template>
  <div class="platform-form-card">
    <!-- 极简工具栏 -->
    <div class="card-toolbar">
      <div class="toolbar-title">{{ platformMeta?.name || platform }}</div>

      <!-- 一键同步到其他平台 Popover -->
      <div v-if="otherPlatforms && otherPlatforms.length > 0" class="toolbar-actions">
        <el-popover
          v-model:visible="syncPopoverVisible"
          trigger="click"
          placement="bottom-end"
          :width="280"
          popper-class="sync-popover"
        >
          <template #reference>
            <el-button link size="small" type="primary" class="sync-link-btn">
              同步文案至其他平台
            </el-button>
          </template>

          <div class="sync-popover-content">
            <div class="sync-popover-title">同步本平台文案至：</div>

            <div class="target-platforms-list">
              <el-checkbox-group v-model="targetPlatformIds">
                <div
                  v-for="target in otherPlatforms"
                  :key="target.id"
                  class="target-checkbox-item"
                >
                  <el-checkbox :label="target.id">
                    {{ target.name }}
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>

            <div class="sync-fields-divider">同步内容</div>
            <div class="sync-fields-row">
              <el-checkbox v-model="syncFields.title">标题与变量</el-checkbox>
              <el-checkbox v-model="syncFields.desc">描述</el-checkbox>
              <el-checkbox v-model="syncFields.tags">话题</el-checkbox>
            </div>

            <div class="sync-actions-row">
              <el-button size="small" @click="syncPopoverVisible = false">取消</el-button>
              <el-button
                size="small"
                type="primary"
                :disabled="targetPlatformIds.length === 0"
                @click="confirmSync"
              >
                确认同步
              </el-button>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <!-- 平台表单内容区 -->
    <div class="card-form-container">
      <component
        :is="activeFormComponent"
        :override="override"
        :rule-config="ruleConfig"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue'
import { ElMessage } from 'element-plus'
import { PLATFORMS } from '../../config/platforms'
import type { PlatformOverrideSetting, BatchRuleConfig } from '../../types/matrix'

// 动态载入平台独立表单组件
const BilibiliForm = defineAsyncComponent(() => import('./platforms/BilibiliForm.vue'))
const TencentForm = defineAsyncComponent(() => import('./platforms/TencentForm.vue'))
const DouyinForm = defineAsyncComponent(() => import('./platforms/DouyinForm.vue'))
const XiaohongshuForm = defineAsyncComponent(() => import('./platforms/XiaohongshuForm.vue'))
const GenericForm = defineAsyncComponent(() => import('./platforms/GenericForm.vue'))

const props = defineProps<{
  platform: string
  override: PlatformOverrideSetting
  ruleConfig: BatchRuleConfig
  otherPlatforms?: Array<{ id: string; name: string }>
}>()

const emit = defineEmits<{
  (e: 'sync-to-platforms', payload: {
    sourcePlatform: string
    targetPlatformIds: string[]
    fields: { title: boolean; desc: boolean; tags: boolean }
  }): void
}>()

const platformMeta = computed(() => {
  return PLATFORMS.find(p => p.id === props.platform)
})

const activeFormComponent = computed(() => {
  switch (props.platform) {
    case 'bilibili':
      return BilibiliForm
    case 'tencent':
      return TencentForm
    case 'douyin':
      return DouyinForm
    case 'xiaohongshu':
      return XiaohongshuForm
    default:
      return GenericForm
  }
})

// 一键同步弹窗状态
const syncPopoverVisible = ref(false)
const targetPlatformIds = ref<string[]>([])
const syncFields = ref({
  title: true,
  desc: true,
  tags: true
})

function confirmSync() {
  if (targetPlatformIds.value.length === 0) {
    ElMessage.warning('请至少选择 1 个目标平台')
    return
  }
  emit('sync-to-platforms', {
    sourcePlatform: props.platform,
    targetPlatformIds: targetPlatformIds.value,
    fields: { ...syncFields.value }
  })
  syncPopoverVisible.value = false
  ElMessage.success(`已将文案同步至 ${targetPlatformIds.value.length} 个平台`)
}
</script>

<style scoped>
.platform-form-card {
  background: var(--el-bg-color, #ffffff);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, #f2f3f5);
}

.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary, #18191c);
}

.sync-link-btn {
  font-size: 13px;
}

.sync-popover-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sync-popover-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
}

.target-platforms-list {
  max-height: 120px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sync-fields-divider {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
  padding-top: 4px;
  border-top: 1px dashed var(--el-border-color-lighter, #f2f3f5);
}

.sync-fields-row {
  display: flex;
  align-items: center;
  /* gap: 10px; */
}

.sync-actions-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 2px;
}

.card-form-container {
  width: 100%;
}
</style>
