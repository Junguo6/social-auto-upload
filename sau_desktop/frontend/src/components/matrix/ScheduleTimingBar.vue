<template>
  <div class="schedule-timing-bar">
    <div class="timing-row">
      <div class="timing-label">排期设置</div>
      <div class="timing-content">
        <el-radio-group v-model="localConfig.scheduleType" size="default">
          <el-radio label="immediate">立即发布</el-radio>
          <el-radio label="interval">间隔排期</el-radio>
          <el-radio label="custom">指定时间</el-radio>
        </el-radio-group>

        <!-- 间隔排期展开 -->
        <div v-if="localConfig.scheduleType === 'interval'" class="sub-param-group">
          <span class="sub-label">起始时间</span>
          <el-date-picker
            v-model="localConfig.startScheduleTime"
            type="datetime"
            placeholder="首个发布时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            size="default"
            class="timing-picker"
          />

          <span class="sub-label">递增间隔</span>
          <el-input-number
            v-model="localConfig.intervalMinutes"
            :min="5"
            :max="1440"
            :step="5"
            size="default"
            style="width: 100px"
          />
          <span class="unit-text">分钟</span>
        </div>

        <!-- 统一定时展开 -->
        <div v-else-if="localConfig.scheduleType === 'custom'" class="sub-param-group">
          <span class="sub-label">发布时间</span>
          <el-date-picker
            v-model="localConfig.startScheduleTime"
            type="datetime"
            placeholder="指定发布时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            size="default"
            class="timing-picker"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BatchRuleConfig } from '../../types/matrix'

const props = withDefaults(defineProps<{
  ruleConfig: BatchRuleConfig
  mediaCount?: number
}>(), {
  mediaCount: 1
})

const emit = defineEmits<{
  (e: 'update:ruleConfig', val: BatchRuleConfig): void
}>()

const localConfig = computed({
  get: () => props.ruleConfig,
  set: (val) => emit('update:ruleConfig', val)
})
</script>

<style scoped>
.schedule-timing-bar {
  background: var(--el-bg-color, #ffffff);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: 8px;
  padding: 14px 20px;
}

.timing-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.timing-label {
  width: 90px;
  flex-shrink: 0;
  font-size: 14px;
  color: #18191c;
  padding-top: 4px;
  text-align: right;
  font-weight: 500;
}

.timing-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sub-param-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 6px;
}

.sub-label {
  font-size: 13px;
  color: #606266;
}

.timing-picker {
  width: 200px;
}

.unit-text {
  font-size: 13px;
  color: #909399;
}
</style>
