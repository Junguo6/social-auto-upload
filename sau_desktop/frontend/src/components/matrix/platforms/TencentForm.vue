<template>
  <div class="wechat-form-layout">
    <!-- 1. 视频描述 (视频号核心字段，含话题与占位变量) -->
    <div class="wechat-form-row">
      <div class="row-label">视频描述</div>
      <div class="row-content">
        <div class="desc-box-wrapper">
          <TokenTemplateInput
            v-model="override.desc"
            type="textarea"
            :rows="4"
            placeholder="添加描述，支持插入变量或导入TXT按视频轮询文案..."
            :maxlength="1000"
            :sample-media="sampleMedia"
            :unit-level="unitLevel"
            :rule-config="ruleConfig"
            :hide-tools="hideVariables"
          />
          <div class="desc-action-bar">
            <!-- 快捷操作区：话题 (分集规则暂时隐藏，采用默认智能提取规则) -->
            <div class="tag-insert-group">
              <button type="button" class="wechat-tag-pill topic-pill" @click="addHashTag">
                <span class="hash-symbol">#</span>
                <span class="pill-text">添加话题</span>
              </button>
              <!-- 暂时取消分集规则设置
              <button
                v-if="ruleConfig && !hideVariables"
                type="button"
                class="wechat-tag-pill ep-rule-pill"
                :class="{ 'is-active': showEpisodeRule }"
                @click="showEpisodeRule = !showEpisodeRule"
              >
                <el-icon class="pill-icon"><Operation /></el-icon>
                <span class="pill-text">{{ showEpisodeRule ? '收起规则' : '分集规则' }}</span>
                <el-icon class="arrow-indicator" :class="{ 'is-open': showEpisodeRule }"><ArrowDown /></el-icon>
              </button>
              -->
            </div>
          </div>
        </div>

        <!-- 轻量分集规则面板 (暂时隐藏)
        <el-collapse-transition>
          <div v-if="showEpisodeRule" class="episode-mini-panel">
            <div class="mini-rule-row">
              <span class="mini-label">模式:</span>
              <el-select v-model="safeRuleConfig.episodeMode" size="small" style="width: 130px">
                <el-option label="智能提取文件名" value="auto" />
                <el-option label="强制递增编号" value="sequence" />
              </el-select>

              <span class="mini-label">起始:</span>
              <el-input-number
                v-model="safeRuleConfig.startEpisode"
                :min="1"
                :max="9999"
                size="small"
                style="width: 80px"
              />

              <span class="mini-label">步长:</span>
              <el-input-number
                v-model="safeRuleConfig.episodeStep"
                :min="1"
                :max="10"
                size="small"
                style="width: 70px"
              />

              <el-checkbox v-model="ruleConfig!.padZero" size="small">
                补零 (01, 02)
              </el-checkbox>
            </div>
          </div>
        </el-collapse-transition>
        -->
      </div>
    </div>

    <!-- 2. 短标题 (微信官方 6~16字) -->
    <div class="wechat-form-row">
      <div class="row-label">短标题</div>
      <div class="row-content">
        <TokenTemplateInput
          v-model="override.shortTitle"
          type="input"
          placeholder="填写短标题，支持插入变量或导入TXT按视频轮询文案..."
          :maxlength="30"
          :sample-media="sampleMedia"
          :unit-level="unitLevel"
          :rule-config="ruleConfig"
          :hide-tools="hideVariables"
        />
      </div>
    </div>

    <!-- 3. 位置 (微信官方: 默认按平台定位 / 不显示位置) -->
    <div class="wechat-form-row">
      <div class="row-label">位置</div>
      <div class="row-content">
        <el-select
          v-model="override.location"
          placeholder="选择位置"
          style="width: 100%"
        >
          <el-option label="按平台定位 (默认)" value="auto" />
          <el-option label="不显示位置" value="none" />
        </el-select>
      </div>
    </div>

    <!-- 4. 添加到合集 -->
    <div class="wechat-form-row">
      <div class="row-label">添加到合集</div>
      <div class="row-content">
        <TokenTemplateInput
          v-model="override.collection"
          type="input"
          placeholder="选择或输入合集名称，支持插入变量..."
          :sample-media="sampleMedia"
          :unit-level="unitLevel"
          :rule-config="ruleConfig"
          :hide-tools="hideVariables"
        />
      </div>
    </div>

    <!-- 5. 链接 (微信官方: 公众号文章 / 红包封面 / 视频号剧集 / 小程序短剧) -->
    <div class="wechat-form-row">
      <div class="row-label">链接</div>
      <div class="row-content">
        <div class="link-control-group">
          <el-select
            v-model="currentLinkType"
            placeholder="选择链接类型"
            style="width: 100%"
            @change="handleLinkTypeChange"
          >
            <el-option label="不添加链接" value="none" />
            <el-option label="公众号文章" value="article" />
            <el-option label="红包封面" value="redpacket" />
            <el-option label="视频号剧集" value="series" />
            <el-option label="小程序短剧" value="minidrama" />
          </el-select>

          <!-- 公众号文章 / 红包封面: 直接输入 URL -->
          <div v-if="currentLinkType === 'article' || currentLinkType === 'redpacket'" class="link-sub-input">
            <el-input
              v-model="override.linkUrl"
              :placeholder="currentLinkType === 'article' ? '粘贴公众号文章链接 (https://mp.weixin.qq.com/...)' : '粘贴红包封面链接'"
              clearable
              class="wechat-input"
            />
          </div>

          <!-- 视频号剧集 / 小程序短剧: 弹窗选择/关键字输入 -->
          <div v-else-if="currentLinkType === 'series' || currentLinkType === 'minidrama'" class="link-sub-input">
            <div class="component-choose-box" @click="openLinkDialog">
              <span v-if="override.linkTitle" class="selected-text">{{ override.linkTitle }}</span>
              <span v-else class="placeholder-text">
                {{ currentLinkType === 'series' ? '选择或设置关联的视频号剧集名称' : '选择或设置关联的小程序短剧名称' }}
              </span>
              <el-button size="small" type="primary" link>
                {{ override.linkTitle ? '修改' : '设置' }}
              </el-button>
            </div>
            <VariableChips
              v-if="!hideVariables && override.linkTitle"
              :current-value="override.linkTitle"
              :rule-config="ruleConfig"
              :sample-media="sampleMedia"
              :unit-level="unitLevel"
              @insert="insertVarToLinkTitleDirect"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 6. 活动 (微信官方: 不参与活动 / 搜索活动名) -->
    <div class="wechat-form-row">
      <div class="row-label">活动</div>
      <div class="row-content">
        <div class="activity-control-group">
          <el-select
            v-model="currentActivityMode"
            placeholder="选择活动模式"
            style="width: 100%"
            @change="handleActivityModeChange"
          >
            <el-option label="不参与活动 (默认)" value="none" />
            <el-option label="搜索活动名" value="search" />
          </el-select>

          <!-- 搜索活动输入框 -->
          <div v-if="currentActivityMode === 'search'" class="activity-sub-input">
            <TokenTemplateInput
              v-model="override.activityName"
              type="input"
              placeholder="输入活动名搜索（支持变量，如：{文件夹名}激励计划）"
              :sample-media="sampleMedia"
              :unit-level="unitLevel"
              :rule-config="ruleConfig"
              :hide-tools="hideVariables"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 7. 视频标注 (微信官方标准合规标注) -->
    <div class="wechat-form-row">
      <div class="row-label">视频标注</div>
      <div class="row-content">
        <el-select
          v-model="override.declaration"
          placeholder="选择视频标注"
          style="width: 100%"
          clearable
        >
          <el-option label="无需标注" value="无需标注" />
          <el-option label="含AI生成内容" value="含AI生成内容" />
          <el-option label="内容为虚构剧情，仅供娱乐" value="内容为虚构剧情，仅供娱乐" />
          <el-option label="个人观点，仅供参考" value="个人观点，仅供参考" />
          <el-option label="内容包含营销广告" value="内容包含营销广告" />
          <el-option label="内容为自行拍摄" value="内容为自行拍摄" />
          <el-option label="内容为转载" value="内容为转载" />
        </el-select>
      </div>
    </div>

    <!-- 8. 竖版封面设置 -->
    <div class="wechat-form-row">
      <div class="row-label">封面设置</div>
      <div class="row-content">
        <div class="cover-input-group">
          <el-input
            v-model="override.thumbnailPortrait"
            placeholder="竖版封面文件路径 (专供视频号信息流展示)"
            clearable
            class="wechat-input"
          />
          <el-button size="default" @click="choosePortraitCover">
            选择封面
          </el-button>
        </div>
      </div>
    </div>

    <!-- 9. 草稿选项 -->
    <div class="wechat-form-row">
      <div class="row-label">保存草稿</div>
      <div class="row-content">
        <el-checkbox v-model="override.draft">
          存为草稿，不直接公开发表
        </el-checkbox>
      </div>
    </div>

    <!-- 剧集 / 短剧选择弹窗 -->
    <el-dialog
      v-model="showLinkDialog"
      :title="currentLinkType === 'series' ? '设置需要关联的视频号剧集' : '设置需要关联的小程序短剧'"
      width="520px"
      append-to-body
      destroy-on-close
      class="wechat-dialog"
    >
      <div class="dialog-tip">内容需与视频内容相关，支持直接输入名称或插入变量（如 {文件夹名}）</div>
      <div class="dialog-body">
        <el-input
          v-model="tempDialogKeyword"
          :placeholder="currentLinkType === 'series' ? '输入剧集名称（支持变量，如：{文件夹名}）' : '输入短剧名称（支持变量）'"
          clearable
          @keyup.enter="confirmLinkSelect"
        />
        <VariableChips
          v-if="!hideVariables"
          :current-value="tempDialogKeyword"
          :rule-config="ruleConfig"
          :sample-media="sampleMedia"
          :unit-level="unitLevel"
          @insert="insertVarToLinkKeyword"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showLinkDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmLinkSelect">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Operation, ArrowDown } from '@element-plus/icons-vue'
import { SelectLocalFile } from '../../../../wailsjs/go/main/App'
import type { PlatformOverrideSetting, BatchRuleConfig, MediaItem } from '../../../types/matrix'
import TokenTemplateInput from '../controls/TokenTemplateInput.vue'
import VariableChips from '../VariableChips.vue'

const props = defineProps<{
  override: PlatformOverrideSetting
  ruleConfig?: BatchRuleConfig
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  hideVariables?: boolean
}>()

const defaultRuleConfig: BatchRuleConfig = {
  titleTemplate: '{视频名}',
  episodeMode: 'sequence',
  startEpisode: 1,
  episodeStep: 1,
  padZero: false,
  scheduleType: 'immediate',
  startScheduleTime: '',
  intervalMinutes: 30
}
const safeRuleConfig = computed(() => props.ruleConfig || defaultRuleConfig)

// 默认按平台定位
if (props.override && !props.override.location) {
  props.override.location = 'auto'
}

const showEpisodeRule = ref(false)

// 链接相关
const currentLinkType = computed({
  get: () => props.override.linkType || 'none',
  set: (val: string) => {
    props.override.linkType = val
  }
})

function handleLinkTypeChange(val: string) {
  props.override.linkType = val
  if (val === 'none') {
    props.override.linkUrl = ''
    props.override.linkTitle = ''
  }
}

const showLinkDialog = ref(false)
const tempDialogKeyword = ref('')

function openLinkDialog() {
  tempDialogKeyword.value = props.override.linkTitle || ''
  showLinkDialog.value = true
}

function confirmLinkSelect() {
  props.override.linkTitle = tempDialogKeyword.value.trim()
  showLinkDialog.value = false
  if (props.override.linkTitle) {
    ElMessage.success('已设置关联内容')
  }
}

// 活动相关
const currentActivityMode = computed({
  get: () => props.override.activityMode || 'none',
  set: (val: string) => {
    props.override.activityMode = val
  }
})

function handleActivityModeChange(val: string) {
  props.override.activityMode = val
  if (val === 'none') {
    props.override.activityName = ''
  }
}

// 变量插入辅助函数
function insertVarToDesc(v: string) {
  const current = props.override.desc || ''
  props.override.desc = current ? `${current} ${v}` : v
}

function insertVarToShortTitle(v: string) {
  const current = props.override.shortTitle || ''
  props.override.shortTitle = current ? `${current}${v}` : v
}

function insertVarToCollection(v: string) {
  const current = props.override.collection || ''
  props.override.collection = current ? `${current}${v}` : v
}

function insertVarToActivity(v: string) {
  const current = props.override.activityName || ''
  props.override.activityName = current ? `${current}${v}` : v
}

function insertVarToLinkKeyword(v: string) {
  const current = tempDialogKeyword.value || ''
  tempDialogKeyword.value = current ? `${current}${v}` : v
}

function insertVarToLinkTitleDirect(v: string) {
  const current = props.override.linkTitle || ''
  props.override.linkTitle = current ? `${current}${v}` : v
}

function addHashTag() {
  const current = props.override.desc || ''
  props.override.desc = current ? `${current} #` : '#'
}

const choosePortraitCover = async () => {
  try {
    const file = await SelectLocalFile('选择视频号竖版封面', ['*.png', '*.jpg', '*.jpeg', '*.webp'])
    if (file) {
      props.override.thumbnailPortrait = file
      ElMessage.success('已选择视频号封面')
    }
  } catch (err: any) {
    ElMessage.error(`选择封面失败: ${err.message || err}`)
  }
}
</script>

<style scoped>
.wechat-form-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 0;
  width: 100%;
  box-sizing: border-box;
}

.wechat-form-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  width: 100%;
  box-sizing: border-box;
}

.row-label {
  width: 90px;
  flex-shrink: 0;
  font-size: 14px;
  color: #18191c;
  padding-top: 6px;
  text-align: right;
  font-weight: 500;
}

.row-content {
  flex: 1;
  min-width: 0;
  max-width: 600px;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.desc-box-wrapper {
  width: 100%;
  box-sizing: border-box;
  min-width: 0;
  /* border: 1px solid #e2e8f0; */
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.desc-box-wrapper:focus-within {
  border-color: #07c160;
  box-shadow: 0 0 0 2px rgba(7, 193, 96, 0.12);
}

.wechat-textarea :deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  border-radius: 0;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.5;
}

.desc-action-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  background: #f8fafc;
  border-top: 1px solid #f1f5f9;
  width: 100%;
  box-sizing: border-box;
}

.tag-insert-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.desc-variable-chips-wrap {
  width: 100%;
  min-width: 0;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
  box-sizing: border-box;
}

.wechat-tag-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  border: 1px solid transparent;
  box-sizing: border-box;
}

/* 话题按钮：微信经典薄荷微绿，高级雅致 */
.topic-pill {
  color: #047857;
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.topic-pill:hover {
  background: #d1fae5;
  border-color: #6ee7b7;
  color: #065f46;
  transform: translateY(-0.5px);
  box-shadow: 0 2px 4px rgba(5, 150, 105, 0.12);
}

.topic-pill:active {
  transform: translateY(0);
  background: #a7f3d0;
}

.topic-pill .hash-symbol {
  font-weight: 700;
  font-size: 13px;
  color: #059669;
}

/* 分集规则按钮：微质感设置风格，支持高亮展开指示 */
.ep-rule-pill {
  color: #475569;
  background: #ffffff;
  border-color: #cbd5e1;
}

.ep-rule-pill:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #1e293b;
  transform: translateY(-0.5px);
}

.ep-rule-pill.is-active {
  color: #2563eb;
  background: #eff6ff;
  border-color: #93c5fd;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.12);
}

.ep-rule-pill.is-active:hover {
  background: #dbeafe;
  border-color: #60a5fa;
}

.ep-rule-pill .pill-icon {
  font-size: 12px;
}

.ep-rule-pill .arrow-indicator {
  font-size: 11px;
  transition: transform 0.2s ease;
  margin-left: 1px;
}

.ep-rule-pill .arrow-indicator.is-open {
  transform: rotate(180deg);
}

.episode-mini-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 14px;
  box-sizing: border-box;
  width: 100%;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.mini-rule-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.mini-label {
  font-size: 12px;
  color: #606266;
}

.wechat-input :deep(.el-input__wrapper) {
  font-size: 13px;
}

.cover-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-control-group,
.activity-control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.link-sub-input,
.activity-sub-input {
  width: 100%;
}

.component-choose-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 5px 12px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 32px;
  box-sizing: border-box;
}

.component-choose-box:hover {
  border-color: #1890ff;
}

.component-choose-box .selected-text {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.component-choose-box .placeholder-text {
  font-size: 13px;
  color: #a8abb2;
}

.dialog-tip {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
  line-height: 1.4;
}

.dialog-body {
  margin-bottom: 8px;
}
</style>
