<template>
  <div class="publish-rule-form glass-card">
    <div class="card-header">
      <div class="card-title-box">
        <span class="step-badge">3</span>
        <div class="title-text-group">
          <div class="main-title">
            <span>发布信息与批量规则</span>
            <span class="req-star">*</span>
          </div>
          <div class="sub-title">通用文案将默认同步到所有平台账号，支持动态占位符变量一键批量生成标题与排期</div>
        </div>
      </div>
    </div>

    <!-- 表单主体网格 -->
    <div class="form-grid">
      <!-- 1. 全局主标题与变量规则 -->
      <div class="form-item title-item">
        <div class="item-label-row">
          <label class="item-label">
            <el-icon><EditPen /></el-icon>
            <span>通用标题 / 批量规则</span>
          </label>
          <div class="var-chips-box">
            <span class="hint-text">💡 插入批量变量:</span>
            <button type="button" class="var-chip" @click="insertVar('{集数}')">{集数}</button>
            <button type="button" class="var-chip" @click="insertVar('{视频名}')">{视频名}</button>
            <button type="button" class="var-chip" @click="insertVar('{日期}')">{日期}</button>
          </div>
        </div>
        <el-input
          ref="titleInputRef"
          v-model="masterForm.title"
          placeholder="输入主标题，如：短剧第一季 - 第{集数}集 | {视频名}"
          maxlength="80"
          show-word-limit
          clearable
          class="stylish-input"
        />

        <!-- 标题批量生成实时预览 -->
        <div v-if="previewTitles.length > 0 && hasDynamicVars" class="batch-title-preview">
          <span class="preview-label">批量生成效果预演:</span>
          <div class="preview-tags">
            <span v-for="(pt, idx) in previewTitles" :key="idx" class="preview-tag">
              #{{ idx + 1 }} {{ pt }}
            </span>
          </div>
        </div>
      </div>

      <!-- 2. 正文文案 / 描述 -->
      <div class="form-item desc-item">
        <div class="item-label-row">
          <label class="item-label">
            <el-icon><Document /></el-icon>
            <span>正文描述 / 简介</span>
          </label>
          <div class="quick-tags">
            <el-button size="small" link type="primary" @click="appendDesc('#短剧 #追剧')">+短剧追更</el-button>
            <el-button size="small" link type="primary" @click="appendDesc('#自媒体干货')">+自媒体干货</el-button>
            <el-button size="small" link type="primary" @click="appendDesc('#好物分享')">+带货推荐</el-button>
          </div>
        </div>
        <el-input
          v-model="masterForm.desc"
          type="textarea"
          :rows="3"
          placeholder="填写通用视频简介、创作理念或追更指引..."
          maxlength="1000"
          show-word-limit
          class="stylish-textarea"
        />
      </div>

      <!-- 3. 话题标签与发布节奏 -->
      <div class="form-row-two">
        <!-- 话题标签 -->
        <div class="form-item">
          <div class="item-label-row">
            <label class="item-label">
              <el-icon><PriceTag /></el-icon>
              <span>热门话题 (以逗号分隔)</span>
            </label>
          </div>
          <el-input
            v-model="masterForm.tags"
            placeholder="如：短剧, 爆款, AI黑科技"
            clearable
            class="stylish-input"
          />
          <div class="tag-chips">
            <span class="tag-chip" @click="appendTag('短剧')">#短剧</span>
            <span class="tag-chip" @click="appendTag('爆款视频')">#爆款视频</span>
            <span class="tag-chip" @click="appendTag('干货分享')">#干货分享</span>
            <span class="tag-chip" @click="appendTag('日常剪辑')">#日常剪辑</span>
          </div>
        </div>

        <!-- 发布时机与防限流节奏 -->
        <div class="form-item">
          <div class="item-label-row">
            <label class="item-label">
              <el-icon><Timer /></el-icon>
              <span>发布节奏与时机</span>
            </label>
          </div>
          <div class="schedule-selector-box">
            <el-radio-group v-model="ruleConfig.scheduleType" class="schedule-radios">
              <el-radio-button value="immediate">立即发布</el-radio-button>
              <el-radio-button value="interval">递增防限流</el-radio-button>
              <el-radio-button value="custom">固定定时</el-radio-button>
            </el-radio-group>

            <!-- 递增防限流选项 -->
            <div v-if="ruleConfig.scheduleType === 'interval'" class="interval-config-box">
              <div class="sub-field">
                <span class="sub-label">首发时间:</span>
                <el-date-picker
                  v-model="ruleConfig.startScheduleTime"
                  type="datetime"
                  placeholder="首条发布时间"
                  value-format="YYYY-MM-DD HH:mm"
                  format="MM-DD HH:mm"
                  size="small"
                  class="date-picker-sm"
                />
              </div>
              <div class="sub-field">
                <span class="sub-label">每条间隔:</span>
                <el-input-number
                  v-model="ruleConfig.intervalMinutes"
                  :min="5"
                  :max="1440"
                  :step="15"
                  size="small"
                  class="step-num-sm"
                />
                <span class="unit">分钟</span>
              </div>
            </div>

            <!-- 固定定时选项 -->
            <div v-else-if="ruleConfig.scheduleType === 'custom'" class="custom-schedule-box">
              <el-date-picker
                v-model="masterForm.schedule"
                type="datetime"
                placeholder="选择统一定时发布时间"
                value-format="YYYY-MM-DD HH:mm"
                size="small"
                style="width: 100%;"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MasterForm, BatchRuleConfig, MediaItem } from '../../types/matrix'

const props = defineProps<{
  masterForm: MasterForm
  ruleConfig: BatchRuleConfig
  mediaList: MediaItem[]
}>()

const emit = defineEmits<{
  (e: 'update:masterForm', val: MasterForm): void
  (e: 'update:ruleConfig', val: BatchRuleConfig): void
}>()

const titleInputRef = ref<any>(null)

// 是否包含动态变量
const hasDynamicVars = computed(() => {
  const t = props.masterForm.title
  return t.includes('{集数}') || t.includes('{视频名}') || t.includes('{日期}')
})

// 标题预演预览
const previewTitles = computed(() => {
  const tpl = props.masterForm.title
  if (!tpl) return []
  const todayStr = new Date().toISOString().split('T')[0]
  return props.mediaList.slice(0, 3).map((item, idx) => {
    const ep = item.parsedEpisode || (idx + 1)
    const baseName = item.fileName.replace(/\.[^/.]+$/, "")
    return tpl
      .replace(/\{集数\}/g, String(ep))
      .replace(/\{视频名\}/g, baseName)
      .replace(/\{日期\}/g, todayStr)
  })
})

// 插入动态占位符变量
const insertVar = (v: string) => {
  props.masterForm.title = (props.masterForm.title || '') + v
}

// 追加正文描述
const appendDesc = (tagText: string) => {
  if (!props.masterForm.desc) {
    props.masterForm.desc = tagText
  } else if (!props.masterForm.desc.includes(tagText)) {
    props.masterForm.desc += ` ${tagText}`
  }
}

// 追加话题标签
const appendTag = (t: string) => {
  const current = props.masterForm.tags ? props.masterForm.tags.split(/[,，\s]+/) : []
  if (!current.includes(t)) {
    current.push(t)
    props.masterForm.tags = current.filter(Boolean).join(', ')
  }
}
</script>

<style scoped>
.publish-rule-form {
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
}

.card-header {
  margin-bottom: 14px;
}

.card-title-box {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-badge {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--primary-gradient);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
}

.title-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.main-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.req-star {
  color: var(--status-danger);
}

.sub-title {
  font-size: 12px;
  color: var(--text-muted);
}

/* 表单结构 */
.form-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.item-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.var-chips-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hint-text {
  font-size: 11px;
  color: var(--text-muted);
}

.var-chip {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.var-chip:hover {
  background: var(--primary-color);
  color: #fff;
}

.batch-title-preview {
  margin-top: 6px;
  padding: 6px 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-label {
  font-size: 11px;
  color: var(--text-muted);
}

.preview-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preview-tag {
  font-size: 11px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  padding: 1px 7px;
  border-radius: 4px;
}

.quick-tags {
  display: flex;
  gap: 6px;
}

.form-row-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 768px) {
  .form-row-two {
    grid-template-columns: 1fr;
  }
}

.tag-chips {
  display: flex;
  gap: 6px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.tag-chip {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  padding: 1px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-chip:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* 排期选择 */
.schedule-selector-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.schedule-radios {
  width: 100%;
}

.interval-config-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  flex-wrap: wrap;
}

.sub-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sub-label {
  font-size: 11px;
  color: var(--text-muted);
}

.date-picker-sm {
  max-width: 150px;
}

.step-num-sm {
  width: 90px;
}

.unit {
  font-size: 11px;
  color: var(--text-muted);
}

.custom-schedule-box {
  margin-top: 2px;
}
</style>
