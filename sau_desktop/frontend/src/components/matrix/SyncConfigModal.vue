<template>
  <el-dialog
    :model-value="modelValue"
    title="同步配置至其他账号"
    width="660px"
    append-to-body
    class="sync-config-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="sync-dialog-content">
      <!-- 1. 当前源配置信息卡片 -->
      <div class="sync-source-card">
        <div class="source-icon-badge">
          <el-icon><CopyDocument /></el-icon>
        </div>
        <div class="source-info">
          <div class="source-title">
            源配置：<strong>{{ sourceDescription }}</strong>
          </div>
          <div class="source-sub">
            将选定字段内容复制并同步至以下勾选的目标账号
          </div>
        </div>
      </div>

      <!-- 2. 选择要同步的具体字段 -->
      <div class="sync-section">
        <div class="section-title">
          <el-icon><SetUp /></el-icon>
          <span>1. 选择同步配置项：</span>
        </div>
        <div class="sync-fields-grid">
          <el-checkbox v-model="fields.title">专属标题</el-checkbox>
          <el-checkbox v-model="fields.desc">正文描述 / 文案</el-checkbox>
          <el-checkbox v-model="fields.tags">话题标签 (Tags)</el-checkbox>
          <el-checkbox v-model="fields.thumbnail">封面图片</el-checkbox>
          <el-checkbox v-model="fields.schedule">发布时机 / 定时</el-checkbox>
          <el-checkbox v-model="fields.platformExclusive">平台专属特性 (合集/带货/声明/分区)</el-checkbox>
        </div>
      </div>

      <!-- 3. 选择要同步的目标账号列表 -->
      <div class="sync-section">
        <div class="section-header-row">
          <div class="section-title">
            <el-icon><UserFilled /></el-icon>
            <span>2. 选择目标账号：</span>
          </div>
          <div class="quick-select-actions">
            <el-button size="small" type="primary" link @click="selectAllInSamePlatform">全选同平台账号</el-button>
            <el-button size="small" type="primary" link @click="selectAllTargets">全选所有有效账号</el-button>
            <el-button size="small" link @click="targetKeys.clear()">清空</el-button>
          </div>
        </div>

        <div class="target-accounts-grid custom-scrollbar">
          <div
            v-for="acc in availableAccounts"
            :key="`${acc.platform}:${acc.account}`"
            class="target-acc-card"
            :class="{ selected: targetKeys.has(`${acc.platform}:${acc.account}`) }"
            @click="toggleTargetKey(`${acc.platform}:${acc.account}`)"
          >
            <div class="acc-left">
              <div class="plat-mini-tag" :style="{ background: getPlatformStyle(acc.platform).brandColor }">
                {{ getPlatformStyle(acc.platform).name }}
              </div>
              <span class="acc-name">{{ acc.nickname || acc.account }}</span>
              <span class="group-tag" v-if="acc.group">{{ acc.group }}</span>
            </div>
            <div class="acc-check-circle" :class="{ checked: targetKeys.has(`${acc.platform}:${acc.account}`) }">
              <el-icon v-if="targetKeys.has(`${acc.platform}:${acc.account}`)"><Check /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="sync-footer">
        <span class="target-count-text">已选中 <strong>{{ targetKeys.size }}</strong> 个目标账号</span>
        <div class="footer-btns">
          <el-button @click="$emit('update:modelValue', false)">取消</el-button>
          <el-button 
            type="primary" 
            :disabled="targetKeys.size === 0"
            @click="handleConfirmSync"
          >
            <el-icon><Check /></el-icon> 确认同步覆盖 ({{ targetKeys.size }})
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import { useAccountStore } from '../../stores/accountStore'
import type { SyncConfigFields, SelectedTargetAccount } from '../../types/matrix'

const props = defineProps<{
  modelValue: boolean
  sourceDescription: string
  currentPlatform: string
  currentAccountKey: string
  selectedTargets: SelectedTargetAccount[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'confirm-sync', payload: { fields: SyncConfigFields; targetKeys: string[] }): void
}>()

const accountStore = useAccountStore()

// 选中的同步字段
const fields = reactive<SyncConfigFields>({
  title: true,
  desc: true,
  tags: true,
  thumbnail: true,
  schedule: true,
  platformExclusive: true
})

// 目标账号列表
const targetKeys = ref<Set<string>>(new Set())

const availableAccounts = computed(() => {
  return accountStore.accounts.filter(a => !(a.checked === true && a.isValid === false))
})

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const toggleTargetKey = (key: string) => {
  if (targetKeys.value.has(key)) {
    targetKeys.value.delete(key)
  } else {
    targetKeys.value.add(key)
  }
}

const selectAllInSamePlatform = () => {
  availableAccounts.value.forEach(a => {
    if (a.platform === props.currentPlatform) {
      targetKeys.value.add(`${a.platform}:${a.account}`)
    }
  })
}

const selectAllTargets = () => {
  availableAccounts.value.forEach(a => {
    targetKeys.value.add(`${a.platform}:${a.account}`)
  })
}

const handleConfirmSync = () => {
  if (targetKeys.value.size === 0) {
    ElMessage.warning('请至少勾选一个需要同步的目标账号')
    return
  }
  emit('confirm-sync', {
    fields: { ...fields },
    targetKeys: Array.from(targetKeys.value)
  })
  emit('update:modelValue', false)
  ElMessage.success(`已成功将配置同步至 ${targetKeys.value.size} 个目标账号`)
}
</script>

<style scoped>
.sync-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sync-source-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.source-icon-badge {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
}

.source-title {
  font-size: 12px;
  color: var(--text-main);
}

.source-title strong {
  color: #818cf8;
}

.source-sub {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 1px;
}

.sync-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 5px;
}

.sync-fields-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  background: var(--bg-detail);
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.target-accounts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

.target-acc-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.target-acc-card:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--border-highlight);
}

.target-acc-card.selected {
  background: rgba(99, 102, 241, 0.1);
  border-color: #6366f1;
}

.acc-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.plat-mini-tag {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  padding: 1px 4px;
  border-radius: 2px;
}

.acc-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-tag {
  font-size: 9px;
  color: #a855f7;
  background: rgba(168, 85, 247, 0.1);
  padding: 1px 3px;
  border-radius: 2px;
}

.acc-check-circle {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 1.5px solid var(--border-highlight);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: #fff;
}

.acc-check-circle.checked {
  background: #6366f1;
  border-color: #6366f1;
}

.sync-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.target-count-text {
  font-size: 11px;
  color: var(--text-secondary);
}

.target-count-text strong {
  color: #818cf8;
}
</style>
