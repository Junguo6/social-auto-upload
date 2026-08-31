<template>
  <div class="master-panel glass-card">
    <div class="panel-header">
      <div class="panel-title">
        <span class="badge-dot master-dot"></span>
        <span>1. 全局基础通用模板</span>
      </div>
      <el-tooltip content="将左侧当前配置强制覆盖同步到所有平台" placement="top">
        <el-button size="small" type="primary" link class="sync-all-btn" @click="$emit('sync-all')">
          <el-icon><Connection /></el-icon> 强制同步至所有平台
        </el-button>
      </el-tooltip>
    </div>

    <div class="panel-scroll-content custom-scrollbar">
      <!-- 1. 媒体类型与素材选择 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text"><el-icon><Film /></el-icon> 作品类型与媒体素材</span>
          <el-radio-group v-model="masterForm.action" class="media-type-switch">
            <el-radio-button value="upload-video">高清视频</el-radio-button>
            <el-radio-button value="upload-note">图文图集</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 视频选择 -->
        <div v-if="masterForm.action === 'upload-video'" class="media-picker-zone">
          <div v-if="masterForm.filePath" class="picked-file-card">
            <div class="file-icon-box"><el-icon><VideoPlay /></el-icon></div>
            <div class="file-info">
              <div class="file-name" :title="getFileName(masterForm.filePath)">{{ getFileName(masterForm.filePath) }}</div>
              <div class="file-path" :title="masterForm.filePath">{{ masterForm.filePath }}</div>
            </div>
            <div class="file-actions">
              <el-button size="small" type="primary" plain @click="chooseVideoFile">更换</el-button>
              <el-button size="small" type="danger" link @click="masterForm.filePath = ''">清除</el-button>
            </div>
          </div>

          <div v-else class="upload-placeholder hover-lift" @click="chooseVideoFile">
            <div class="upload-icon-pulse"><el-icon><UploadFilled /></el-icon></div>
            <div class="upload-text">点击浏览或拖入本地短视频文件</div>
            <div class="upload-hint">支持 MP4, MOV, MKV, FLV 常见高清格式</div>
          </div>
        </div>

        <!-- 图文图片选择 -->
        <div v-else class="media-picker-zone">
          <div v-if="masterForm.images.length > 0" class="image-list-grid">
            <div v-for="(img, idx) in masterForm.images" :key="idx" class="image-item-card">
              <span class="img-idx">P{{ idx + 1 }}</span>
              <span class="img-name" :title="getFileName(img)">{{ getFileName(img) }}</span>
              <el-button size="small" type="danger" link @click="removeImage(idx)">×</el-button>
            </div>
            <div class="add-img-btn" @click="chooseImageFiles">
              <el-icon><Plus /></el-icon>
              <span>添加图片</span>
            </div>
          </div>

          <div v-else class="upload-placeholder hover-lift" @click="chooseImageFiles">
            <div class="upload-icon-pulse"><el-icon><PictureFilled /></el-icon></div>
            <div class="upload-text">点击添加本地图文笔记素材 (支持多图)</div>
            <div class="upload-hint">支持 JPG, PNG, WEBP 等高清图片格式</div>
          </div>
        </div>
      </div>

      <!-- 2. 全局标题 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text"><el-icon><EditPen /></el-icon> 全局通用主标题</span>
          <span class="char-count" :class="{ warning: masterForm.title.length > 30 }">{{ masterForm.title.length }}/30 字</span>
        </div>
        <el-input 
          v-model="masterForm.title" 
          placeholder="输入作品通用主标题 (默认同步至各大平台)"
          maxlength="80"
          show-word-limit
          clearable
          class="stylish-input"
        />
      </div>

      <!-- 3. 全局文案 / 描述 -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text"><el-icon><Document /></el-icon> 全局通用正文描述</span>
          <div class="quick-helpers">
            <el-button size="small" link type="primary" @click="appendMasterTag('#自媒体运营')">+自媒体</el-button>
            <el-button size="small" link type="primary" @click="appendMasterTag('#AI黑科技')">+AI工具</el-button>
            <el-button size="small" link type="primary" @click="appendMasterTag('#干货分享')">+干货</el-button>
          </div>
        </div>
        <el-input 
          v-model="masterForm.desc" 
          type="textarea" 
          :rows="4" 
          placeholder="填写作品通用正文文案、创作心得或视频简介..."
          show-word-limit
          maxlength="1000"
          class="stylish-textarea"
        />
      </div>

      <!-- 4. 全局话题标签 (Tags) -->
      <div class="form-section">
        <div class="section-label">
          <span class="label-text"><el-icon><PriceTag /></el-icon> 全局通用热门话题 (以逗号分隔)</span>
        </div>
        <el-input 
          v-model="masterForm.tags" 
          placeholder="如：AI实测, 剪辑技巧, 涨粉干货" 
          clearable
          class="stylish-input"
        />
        <div class="tag-chips">
          <span class="tag-chip" @click="appendMasterTag('#自媒体运营')">#自媒体运营</span>
          <span class="tag-chip" @click="appendMasterTag('#爆款视频')">#爆款视频</span>
          <span class="tag-chip" @click="appendMasterTag('#AI赋能')">#AI赋能</span>
          <span class="tag-chip" @click="appendMasterTag('#创作者计划')">#创作者计划</span>
          <span class="tag-chip" @click="appendMasterTag('#知识分享')">#知识分享</span>
        </div>
      </div>

      <!-- 5. 全局通用主封面与定时发布 -->
      <div class="form-section form-row-2">
        <div class="form-col">
          <div class="section-label">
            <span class="label-text"><el-icon><Picture /></el-icon> 全局通用主封面</span>
          </div>
          <el-input v-model="masterForm.thumbnail" placeholder="选填：通用封面图片路径" clearable class="stylish-input">
            <template #append>
              <el-button @click="chooseMasterCover"><el-icon><FolderOpened /></el-icon></el-button>
            </template>
          </el-input>
        </div>

        <div class="form-col">
          <div class="section-label">
            <span class="label-text"><el-icon><Clock /></el-icon> 全局定时发布</span>
          </div>
          <el-date-picker 
            v-model="masterForm.schedule"
            type="datetime"
            placeholder="留空则立即发布"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            class="stylish-datepicker"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { SelectLocalFile } from '../../../wailsjs/go/main/App'
import type { MasterForm } from '../../types/matrix'

const props = defineProps<{
  masterForm: MasterForm
}>()

defineEmits<{
  (e: 'sync-all'): void
}>()

const getFileName = (pathStr: string) => {
  if (!pathStr) return ''
  const parts = pathStr.split(/[/\\]/)
  return parts[parts.length - 1] || pathStr
}

const chooseVideoFile = async () => {
  try {
    const file = await SelectLocalFile('选择本地发布视频文件', ['*.mp4', '*.mov', '*.mkv', '*.flv', '*.avi'])
    if (file) {
      props.masterForm.filePath = file
      ElMessage.success(`已选择主视频素材`)
    }
  } catch (err: any) {
    ElMessage.error(`选择视频文件失败: ${err.message || err}`)
  }
}

const chooseImageFiles = async () => {
  try {
    const file = await SelectLocalFile('选择图文素材图片', ['*.png', '*.jpg', '*.jpeg', '*.webp'])
    if (file) {
      if (!props.masterForm.images.includes(file)) {
        props.masterForm.images.push(file)
        ElMessage.success(`已添加图片素材`)
      }
    }
  } catch (err: any) {
    ElMessage.error(`选择图片失败: ${err.message || err}`)
  }
}

const removeImage = (index: number) => {
  props.masterForm.images.splice(index, 1)
}

const chooseMasterCover = async () => {
  try {
    const file = await SelectLocalFile('选择全局通用封面图片', ['*.png', '*.jpg', '*.jpeg', '*.webp'])
    if (file) {
      props.masterForm.thumbnail = file
      ElMessage.success(`已设置全局封面`)
    }
  } catch (err: any) {
    ElMessage.error(`选择封面失败: ${err.message || err}`)
  }
}

const appendMasterTag = (tag: string) => {
  const cleanTag = tag.replace(/^#/, '')
  const currentTags = props.masterForm.tags ? props.masterForm.tags.split(/[,，\s]+/).filter(Boolean) : []
  if (!currentTags.includes(cleanTag)) {
    currentTags.push(cleanTag)
    props.masterForm.tags = currentTags.join(', ')
  }
}
</script>

<style scoped>
.master-panel {
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.master-dot {
  background: #6366f1;
  box-shadow: 0 0 10px #6366f1;
}

.sync-all-btn {
  font-size: 13px;
  font-weight: 600;
}

.panel-scroll-content {
  padding: 18px 22px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-main);
  font-size: 13px;
}

.char-count {
  font-size: 12px;
  color: var(--text-muted);
}

.char-count.warning {
  color: #f59e0b;
}

.media-picker-zone {
  margin-top: 4px;
}

.upload-placeholder {
  border: 1.5px dashed var(--border-highlight);
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  background: rgba(255, 255, 255, 0.015);
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-placeholder:hover {
  border-color: var(--primary-light);
  background: rgba(99, 102, 241, 0.05);
}

.upload-icon-pulse {
  font-size: 32px;
  color: var(--primary-light);
  margin-bottom: 6px;
}

.upload-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.picked-file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 10px;
}

.file-icon-box {
  font-size: 26px;
  color: #818cf8;
  display: flex;
  align-items: center;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-path {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.image-list-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-item-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-main);
}

.img-idx {
  color: #818cf8;
  font-weight: 700;
}

.add-img-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px dashed var(--border-highlight);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.add-img-btn:hover {
  border-color: var(--primary-light);
  color: var(--primary-light);
}

.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.tag-chip {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.tag-chip:hover {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.3);
  color: #818cf8;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
</style>
