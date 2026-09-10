<template>
  <el-drawer
    v-model="visible"
    :title="drawerTitle"
    size="620px"
    direction="rtl"
    destroy-on-close
    class="cell-config-drawer"
  >
    <div v-if="cellData" class="drawer-body custom-scrollbar">
      <!-- 1. 顶部渠道与内容全景卡片 -->
      <div class="summary-banner glass-card">
        <div class="banner-top">
          <div class="plat-badge" :style="{ background: getPlatformColor(cellData.platform) }">
            {{ getPlatformName(cellData.platform) }}
          </div>
          <div class="acc-nick">
            <span class="nick-main">@{{ cellData.nickname || cellData.account }}</span>
            <span class="plat-sub">{{ getPlatformName(cellData.platform) }}发布通道</span>
          </div>
          <el-tag :type="cellData.cell.enabled ? 'success' : 'info'" size="small" class="status-tag">
            {{ cellData.cell.enabled ? '已启用发布' : '暂停不发布' }}
          </el-tag>
        </div>
        <div class="banner-media-info">
          <el-icon class="media-icon"><Film /></el-icon>
          <span class="media-name" :title="cellData.mediaName">{{ cellData.mediaName }}</span>
        </div>
      </div>

      <!-- 2. 【核心创新】：全局继承原值实时对照卡片 (Live Inherited Preview) -->
      <div class="inherited-context-card">
        <div class="context-header">
          <div class="context-title">
            <el-icon><CopyDocument /></el-icon>
            <span>全局继承预演 (若留空则系统默认采用此套参数)</span>
          </div>
          <el-button size="small" link type="primary" class="copy-btn" @click="copyInheritedToOverride">
            <el-icon><DocumentCopy /></el-icon> 一键带入原值微调
          </el-button>
        </div>
        <div class="context-body">
          <div class="context-item">
            <span class="c-label">继承标题:</span>
            <span class="c-val" :title="cellData.inheritedTitle">{{ cellData.inheritedTitle || '无标题' }}</span>
          </div>
          <div class="context-item" v-if="cellData.inheritedDesc">
            <span class="c-label">继承正文:</span>
            <span class="c-val text-clamp-2" :title="cellData.inheritedDesc">{{ cellData.inheritedDesc }}</span>
          </div>
          <div class="context-item" v-if="cellData.inheritedTags">
            <span class="c-label">继承标签:</span>
            <span class="c-val">{{ cellData.inheritedTags }}</span>
          </div>
          <div class="context-item">
            <span class="c-label">预计时机:</span>
            <span class="c-val timing-text">{{ cellData.inheritedSchedule || '立即发布' }}</span>
          </div>
        </div>
      </div>

      <!-- 3. 发布状态与时机控制 -->
      <div class="config-section">
        <div class="section-title">
          <el-icon><Timer /></el-icon>
          <span>发布状态与时机模式</span>
        </div>
        <div class="field-row">
          <span class="field-label">启用该通道发布:</span>
          <el-switch
            v-model="cellData.cell.enabled"
            active-text="启用发布"
            inactive-text="跳过不发布"
            @change="handleDirty"
          />
        </div>
        <div class="field-row" v-if="cellData.cell.enabled">
          <span class="field-label">发布时机模式:</span>
          <el-radio-group v-model="cellData.cell.scheduleMode" size="small" @change="handleDirty">
            <el-radio-button value="inherit">继承全局排期</el-radio-button>
            <el-radio-button value="immediate">强制立即发布</el-radio-button>
            <el-radio-button value="scheduled">专属定时发布</el-radio-button>
          </el-radio-group>
        </div>
        <div class="field-row" v-if="cellData.cell.enabled && cellData.cell.scheduleMode === 'scheduled'">
          <span class="field-label">定时发布时间:</span>
          <el-date-picker
            v-model="cellData.cell.customSchedule"
            type="datetime"
            placeholder="选择该账号专属定时时间"
            value-format="YYYY-MM-DD HH:mm"
            size="small"
            style="flex: 1;"
            @change="handleDirty"
          />
        </div>
      </div>

      <!-- 4. 专属标题与文案微调 -->
      <div class="config-section" v-if="cellData.cell.enabled">
        <div class="section-title-row">
          <div class="section-title">
            <el-icon><EditPen /></el-icon>
            <span>专属标题与文案微调</span>
          </div>
          <el-button v-if="cellData.cell.isCustomized" size="small" link type="warning" @click="resetToInherit">
            恢复继承全局
          </el-button>
        </div>

        <div class="field-col">
          <div class="label-with-hint">
            <span class="field-label">该账号专属标题:</span>
            <span class="field-hint">留空则自动继承全局批量标题</span>
          </div>
          <el-input
            v-model="cellData.cell.customTitle"
            placeholder="如：【独家专享】原标题内容..."
            clearable
            size="small"
            @input="handleDirty"
          />
        </div>

        <div class="field-col">
          <div class="label-with-hint">
            <span class="field-label">该账号专属正文描述:</span>
            <span class="field-hint">留空则继承全局简介正文</span>
          </div>
          <el-input
            v-model="cellData.cell.override.desc"
            type="textarea"
            :rows="3"
            placeholder="输入针对该账号定制的文案、专属引导语或活动口播..."
            size="small"
            @input="handleDirty"
          />
        </div>

        <div class="field-col">
          <div class="label-with-hint">
            <span class="field-label">该账号专属话题标签:</span>
            <span class="field-hint">逗号分隔</span>
          </div>
          <el-input
            v-model="cellData.cell.override.tags"
            placeholder="如：专属话题A, 专属话题B"
            clearable
            size="small"
            @input="handleDirty"
          />
        </div>
      </div>

      <!-- 5. 平台专属特性参数 (必填与特色特性) -->
      <div class="config-section" v-if="cellData.cell.enabled">
        <div class="section-title">
          <el-icon><Setting /></el-icon>
          <span>{{ getPlatformName(cellData.platform) }} 平台专属特性</span>
          <span class="sub-hint">(必填或平台独有能力)</span>
        </div>

        <!-- Bilibili 专属分区 -->
        <div v-if="cellData.platform === 'bilibili'" class="platform-specific-box">
          <div class="field-row">
            <span class="field-label">B站投稿分区 ID <span style="color:var(--status-danger)">*</span>:</span>
            <el-select v-model="cellData.cell.override.tid" size="small" style="width: 200px;" @change="handleDirty">
              <el-option :value="230" label="科技 (230)" />
              <el-option :value="171" label="电子竞技 (171)" />
              <el-option :value="21" label="日常 (21)" />
              <el-option :value="188" label="数码 (188)" />
              <el-option :value="138" label="搞笑 (138)" />
              <el-option :value="76" label="美食 (76)" />
              <el-option :value="160" label="生活 (160)" />
            </el-select>
          </div>
          <div class="field-row">
            <span class="field-label">作品可见性:</span>
            <el-select v-model="cellData.cell.override.visibility" size="small" style="width: 160px;" @change="handleDirty">
              <el-option value="public" label="公开" />
              <el-option value="unlisted" label="仅链接可见" />
              <el-option value="private" label="私密" />
            </el-select>
          </div>
        </div>

        <!-- 腾讯微信视频号专属 -->
        <div v-else-if="cellData.platform === 'tencent'" class="platform-specific-box">
          <div class="field-row">
            <span class="field-label">存为草稿箱 (不直接公开发布):</span>
            <el-switch v-model="cellData.cell.override.draft" active-text="存为草稿" inactive-text="立即发布" @change="handleDirty" />
          </div>
          <div class="field-col">
            <span class="field-label">视频号短标题 (≤16字):</span>
            <el-input
              v-model="cellData.cell.override.shortTitle"
              placeholder="微信卡片转发时展示的短标题"
              maxlength="16"
              size="small"
              @input="handleDirty"
            />
          </div>
          <div class="field-col">
            <span class="field-label">原创分类:</span>
            <el-input
              v-model="cellData.cell.override.category"
              placeholder="如：科技互联网、短剧、教育科普"
              size="small"
              @input="handleDirty"
            />
          </div>
        </div>

        <!-- 抖音专属带货与合集 -->
        <div v-else-if="cellData.platform === 'douyin'" class="platform-specific-box">
          <div class="field-col">
            <span class="field-label">挂载抖音合集:</span>
            <el-input
              v-model="cellData.cell.override.collection"
              placeholder="输入已有抖音合集名称"
              size="small"
              @input="handleDirty"
            />
          </div>
          <div class="field-col">
            <span class="field-label">小黄车商品短标题:</span>
            <el-input
              v-model="cellData.cell.override.productTitle"
              placeholder="商品短标题"
              size="small"
              @input="handleDirty"
            />
          </div>
          <div class="field-col">
            <span class="field-label">小黄车商品链接:</span>
            <el-input
              v-model="cellData.cell.override.productLink"
              placeholder="https://haohuo.jinritemai.com/..."
              size="small"
              @input="handleDirty"
            />
          </div>
        </div>

        <!-- 通用合规声明与指引 -->
        <div class="field-col" style="margin-top: 10px;">
          <span class="field-label">原创 / AI内容合规声明:</span>
          <el-input
            v-model="cellData.cell.override.declaration"
            placeholder="如：该内容由AI生成，或本视频为原创"
            size="small"
            @input="handleDirty"
          />
        </div>
      </div>
    </div>

    <!-- 底部操作栏 (结构饱满) -->
    <template #footer>
      <div class="drawer-footer">
        <el-button size="small" type="primary" link @click="$emit('open-sync')">
          <el-icon><Connection /></el-icon> 一键克隆同步到同平台其他账号
        </el-button>
        <div class="btn-group">
          <el-button size="small" type="primary" class="gradient-btn-sm" @click="visible = false">
            完成微调
          </el-button>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../../config/platforms'
import type { MatrixCellConfig } from '../../types/matrix'

export interface CellDataWrap {
  mediaId: string
  mediaName: string
  platform: string
  account: string
  nickname?: string
  cell: MatrixCellConfig
  inheritedTitle?: string
  inheritedDesc?: string
  inheritedTags?: string
  inheritedSchedule?: string
}

const props = defineProps<{
  modelValue: boolean
  cellData: CellDataWrap | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'open-sync'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const drawerTitle = computed(() => {
  if (!props.cellData) return '渠道微调面板'
  const plat = getPlatformName(props.cellData.platform)
  const nick = props.cellData.nickname || props.cellData.account
  return `发布微调 · ${plat} @${nick}`
})

// 标记为已定制
const handleDirty = () => {
  if (props.cellData?.cell) {
    props.cellData.cell.isCustomized = true
  }
}

// 一键复制继承原值到覆盖输入框
const copyInheritedToOverride = () => {
  if (!props.cellData) return
  if (props.cellData.inheritedTitle) {
    props.cellData.cell.customTitle = props.cellData.inheritedTitle
  }
  if (props.cellData.inheritedDesc) {
    props.cellData.cell.override.desc = props.cellData.inheritedDesc
  }
  if (props.cellData.inheritedTags) {
    props.cellData.cell.override.tags = props.cellData.inheritedTags
  }
  handleDirty()
  ElMessage.success('已将全局继承原值带入下方输入框，您可稍作修改')
}

// 恢复继承全局
const resetToInherit = () => {
  if (!props.cellData) return
  props.cellData.cell.customTitle = ''
  props.cellData.cell.override.desc = ''
  props.cellData.cell.override.tags = ''
  props.cellData.cell.isCustomized = false
  ElMessage.info('已恢复为继承全局通用规则')
}

const getPlatformName = (pid: string) => getPlatformConfig(pid)?.name || pid
const getPlatformColor = (pid: string) => getPlatformConfig(pid)?.color || '#6366f1'
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 4px 16px 0;
}

/* 顶部渠道全景摘要 */
.summary-banner {
  padding: 16px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.banner-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plat-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.acc-nick {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.nick-main {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plat-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.status-tag {
  font-weight: 600;
}

.banner-media-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding-top: 8px;
  border-top: 1px dashed var(--border-subtle);
}

.media-icon {
  color: var(--primary-color);
  font-size: 15px;
}

.media-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

/* 继承原值对照卡片 (Live Context Preview) */
.inherited-context-card {
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.22);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.context-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.context-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 6px;
}

.copy-btn {
  font-size: 11px;
  font-weight: 600;
}

.context-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  background: var(--bg-card);
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.context-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.c-label {
  color: var(--text-muted);
  font-weight: 600;
  width: 58px;
  flex-shrink: 0;
}

.c-val {
  color: var(--text-main);
  flex: 1;
  word-break: break-all;
}

.text-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.timing-text {
  color: var(--status-warning);
  font-weight: 600;
}

/* 调优卡片区块 */
.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-hint {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: normal;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.field-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label-with-hint {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.platform-specific-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-detail);
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
</style>
