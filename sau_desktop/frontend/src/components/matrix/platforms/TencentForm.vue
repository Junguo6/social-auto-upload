<template>
  <div class="wechat-form-layout">
    <!-- 1. 视频描述 (视频号核心字段，含话题与占位变量) -->
    <div class="wechat-form-row">
      <div class="row-label">视频描述</div>
      <div class="row-content">
        <div class="desc-box-wrapper">
          <el-input
            v-model="override.desc"
            type="textarea"
            :rows="4"
            placeholder="添加描述"
            maxlength="1000"
            show-word-limit
            class="wechat-textarea"
          />
          <div class="desc-action-bar">
            <div class="var-insert-group">
              <span class="action-caption">变量:</span>
              <span class="action-link" @click="insertVar('{视频名}')">{视频名}</span>
              <span class="action-link" @click="insertVar('{集数}')">{集数}</span>
              <span class="action-link" @click="insertVar('{日期}')">{日期}</span>
              <span
                v-if="ruleConfig"
                class="action-rule-btn"
                @click="showEpisodeRule = !showEpisodeRule"
              >
                {{ showEpisodeRule ? '收起规则' : '分集规则' }}
              </span>
            </div>

            <div class="tag-insert-group">
              <button type="button" class="wechat-tag-pill" @click="addHashTag">
                #话题
              </button>
            </div>
          </div>
        </div>

        <!-- 轻量分集规则面板 -->
        <el-collapse-transition>
          <div v-show="showEpisodeRule && ruleConfig" class="episode-mini-panel">
            <div class="mini-rule-row">
              <span class="mini-label">模式:</span>
              <el-select v-model="ruleConfig!.episodeMode" size="small" style="width: 130px">
                <el-option label="智能提取文件名" value="auto" />
                <el-option label="强制递增编号" value="sequence" />
              </el-select>

              <span class="mini-label">起始:</span>
              <el-input-number
                v-model="ruleConfig!.startEpisode"
                :min="1"
                :max="9999"
                size="small"
                style="width: 80px"
              />

              <span class="mini-label">步长:</span>
              <el-input-number
                v-model="ruleConfig!.episodeStep"
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
      </div>
    </div>

    <!-- 2. 短标题 (微信官方 6~16字) -->
    <div class="wechat-form-row">
      <div class="row-label">短标题</div>
      <div class="row-content">
        <el-input
          v-model="override.shortTitle"
          placeholder="填写短标题有机会获得更多流量"
          maxlength="20"
          clearable
          class="wechat-input"
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
        <el-input
          v-model="override.collection"
          placeholder="选择或输入合集名称"
          clearable
          class="wechat-input"
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
                {{ currentLinkType === 'series' ? '选择需要添加的视频号剧集' : '选择需要添加的小程序短剧' }}
              </span>
              <el-button size="small" type="primary" link>
                {{ override.linkTitle ? '修改' : '选择' }}
              </el-button>
            </div>
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
            <el-input
              v-model="override.activityName"
              placeholder="输入要参与的活动名称搜索（如：微信创作者激励计划）"
              clearable
              class="wechat-input"
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
      :title="currentLinkType === 'series' ? '选择需要关联的视频号剧集' : '选择需要关联的小程序短剧'"
      width="480px"
      append-to-body
      destroy-on-close
      class="wechat-dialog"
    >
      <div class="dialog-tip">内容需与视频内容相关，不相关将减少推荐</div>
      <div class="dialog-body">
        <el-input
          v-model="tempDialogKeyword"
          :placeholder="currentLinkType === 'series' ? '输入视频号剧集名称或关键字' : '输入小程序短剧名称或关键字'"
          clearable
          @keyup.enter="confirmLinkSelect"
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
import { SelectLocalFile } from '../../../../wailsjs/go/main/App'
import type { PlatformOverrideSetting, BatchRuleConfig } from '../../../types/matrix'

const props = defineProps<{
  override: PlatformOverrideSetting
  ruleConfig?: BatchRuleConfig
}>()

// 默认按平台定位
if (!props.override.location) {
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

function insertVar(varStr: string) {
  const current = props.override.desc || ''
  if (!current) {
    props.override.desc = varStr
  } else if (!current.includes(varStr)) {
    props.override.desc = `${current} ${varStr}`
  }
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
}

.wechat-form-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
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
  max-width: 600px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.desc-box-wrapper {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
  transition: border-color 0.2s ease;
}

.desc-box-wrapper:focus-within {
  border-color: #1890ff;
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
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}

.var-insert-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-caption {
  font-size: 12px;
  color: #909399;
}

.action-link {
  font-size: 12px;
  color: #1890ff;
  cursor: pointer;
  user-select: none;
}

.action-link:hover {
  text-decoration: underline;
}

.action-rule-btn {
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  margin-left: 6px;
  padding: 1px 4px;
  border-radius: 3px;
  background: #f0f2f5;
  user-select: none;
}

.action-rule-btn:hover {
  color: #1890ff;
}

.wechat-tag-pill {
  border: none;
  background: #f0f2f5;
  color: #606266;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.wechat-tag-pill:hover {
  background: #e4e7ed;
  color: #18191c;
}

.episode-mini-panel {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px 12px;
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
