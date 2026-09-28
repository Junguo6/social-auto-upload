<template>
  <el-dialog
    v-model="dialogVisible"
    title="插入文案库"
    width="520px"
    destroy-on-close
    append-to-body
    class="txt-source-modal"
  >
    <div class="modal-body-container">
      <!-- 1. 文案源快速选择与导入行 (单行防御性防挤压) -->
      <div class="source-select-row">
        <div class="select-label">文案库：</div>
        <div class="select-box-wrap">
          <el-select
            v-model="currentFileName"
            placeholder="选择或新建一个文案库"
            size="default"
            class="source-dropdown"
          >
            <el-option
              v-for="src in txtSources"
              :key="src.fileName"
              :label="`${src.fileName} (${src.lines.length}行)`"
              :value="src.fileName"
            >
              <div class="opt-item-row">
                <span class="opt-name">{{ src.fileName }}</span>
                <span class="opt-meta">{{ src.lines.length }}行</span>
              </div>
            </el-option>
          </el-select>
        </div>

        <!-- 紧凑快捷操作 -->
        <div class="source-btns">
          <button
            type="button"
            class="mini-action-btn primary-btn"
            title="选择本地 .txt 文件"
            @click="triggerFileInput"
          >
            <el-icon><Upload /></el-icon>
            <span>导入</span>
          </button>
          <button
            type="button"
            class="mini-action-btn"
            :class="{ active: isPasting }"
            title="粘贴多行文本创建文案源"
            @click="isPasting = !isPasting"
          >
            <el-icon><EditPen /></el-icon>
            <span>{{ isPasting ? '收起' : '粘贴' }}</span>
          </button>
          <button
            v-if="currentFileName"
            type="button"
            class="mini-action-btn delete-btn"
            title="从列表中移除当前文案源"
            @click="handleDeleteSource(currentFileName)"
          >
            <el-icon><Delete /></el-icon>
            <span>移除</span>
          </button>
        </div>
      </div>

      <!-- 隐藏的文件选择 input -->
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,text/plain"
        style="display: none"
        @change="onFileSelected"
      />

      <!-- 快捷粘贴录入抽屉 (平滑轻量) -->
      <el-collapse-transition>
        <div v-if="isPasting" class="paste-compact-panel">
          <div class="paste-compact-header">
            <el-input
              v-model="pasteFileName"
              placeholder="文案库名称（如：爆款金句）"
              size="small"
              class="paste-name-input"
            />
            <span class="paste-hint">按换行自动分行</span>
          </div>
          <el-input
            v-model="pasteContent"
            type="textarea"
            :rows="3"
            placeholder="粘贴多行文本，每行代表一条视频文案..."
          />
          <div class="paste-compact-footer">
            <el-button size="small" @click="isPasting = false">取消</el-button>
            <el-button type="primary" size="small" :disabled="!pasteContent.trim()" @click="submitPaste">
              确认并选用
            </el-button>
          </div>
        </div>
      </el-collapse-transition>

      <!-- 2. 分发模式切换 (极简分段控制器 Segmented Control) -->
      <div class="mode-control-row">
        <div class="mode-segmented-bar">
          <button
            type="button"
            class="seg-btn"
            :class="{ active: selectedMode === 'seq' }"
            @click="selectedMode = 'seq'"
          >
            <el-icon><RefreshRight /></el-icon>
            <span> 顺序循环轮询</span>
          </button>
          <button
            type="button"
            class="seg-btn"
            :class="{ active: selectedMode === 'random' }"
            @click="selectedMode = 'random'"
          >
            <el-icon><HelpFilled /></el-icon>
            <span> 随机抽取一行</span>
          </button>
        </div>
        <div class="mode-caption">
          {{ selectedMode === 'seq' ? '多视频依次按行填入，超出后循环' : '每个视频发布时随机分配一行，防文案重复' }}
        </div>
      </div>

      <!-- 3. 内容轻量视窗 (清爽微型预览) -->
      <div class="preview-compact-box custom-scrollbar">
        <div v-if="currentLines.length === 0" class="no-content-tip">
          还没有文案库<br>
          点上方「导入」选择 .txt 文件，或点「粘贴」直接输入几行文案
        </div>
        <template v-else>
          <div
            v-for="(line, idx) in currentLines.slice(0, 3)"
            :key="idx"
            class="preview-compact-line"
          >
            <span class="line-idx">#{{ idx + 1 }}</span>
            <span class="line-txt" :title="line">{{ line }}</span>
          </div>
          <div class="preview-summary-row">
            <span>已成功识别 <strong>{{ currentLines.length }}</strong> 行有效文案</span>
            <span v-if="currentLines.length > 3">（仅展示前 3 行预览）</span>
          </div>
        </template>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-split">
        <div class="token-inline-tag" v-if="currentFileName">
          <span class="tag-label">插入后显示为：</span>
          <span class="tag-code">{{ currentGeneratedToken }}</span>
        </div>
        <div class="dialog-footer-actions">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :disabled="!currentFileName || currentLines.length === 0"
            @click="confirmInsert"
          >
            插入
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Upload,
  EditPen,
  Delete,
  RefreshRight,
  HelpFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAllTxtSources,
  registerTxtSource,
  deleteTxtSource,
  getTxtSource,
  type TxtDistributionMode
} from '../../../utils/matrixHelper'

interface Props {
  modelValue: boolean
  initialTxtName?: string
  initialMode?: TxtDistributionMode
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  initialTxtName: '',
  initialMode: 'seq'
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'confirm', payload: { fileName: string; mode: TxtDistributionMode; tokenKey: string }): void
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const txtSources = ref<{ fileName: string; lines: string[] }[]>([])
const currentFileName = ref<string>('')
const selectedMode = ref<TxtDistributionMode>('seq')

const isPasting = ref(false)
const pasteFileName = ref('')
const pasteContent = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

function refreshSources() {
  txtSources.value = getAllTxtSources()
  if (!currentFileName.value && txtSources.value.length > 0) {
    currentFileName.value = txtSources.value[0].fileName
  }
}

const currentLines = computed(() => {
  if (!currentFileName.value) return []
  return getTxtSource(currentFileName.value) || []
})

const currentGeneratedToken = computed(() => {
  if (!currentFileName.value) return ''
  if (selectedMode.value === 'random') {
    return `{TXT:${currentFileName.value}:random}`
  }
  return `{TXT:${currentFileName.value}}`
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    const content = event.target?.result as string
    if (content) {
      registerTxtSource(file.name, content)
      refreshSources()
      currentFileName.value = file.name
      ElMessage.success(`导入成功: ${file.name}`)
    }
  }
  reader.readAsText(file, 'utf-8')
  input.value = ''
}

function submitPaste() {
  const lines = pasteContent.value
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean)

  if (lines.length === 0) {
    ElMessage.warning('请输入有效文本')
    return
  }

  let name = pasteFileName.value.trim()
  if (!name) {
    name = `粘贴文案_${Date.now().toString().slice(-4)}.txt`
  } else if (!name.endsWith('.txt')) {
    name += '.txt'
  }

  registerTxtSource(name, lines)
  refreshSources()
  currentFileName.value = name
  isPasting.value = false
  pasteContent.value = ''
  pasteFileName.value = ''
  ElMessage.success(`已创建: ${name}`)
}

function handleDeleteSource(fileName: string) {
  ElMessageBox.confirm(`确定要移除 "${fileName}" 吗？`, '提示', {
    confirmButtonText: '移除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    deleteTxtSource(fileName)
    refreshSources()
    if (currentFileName.value === fileName) {
      currentFileName.value = txtSources.value.length > 0 ? txtSources.value[0].fileName : ''
    }
  }).catch(() => {})
}

function confirmInsert() {
  if (!currentFileName.value || currentLines.value.length === 0) return
  emit('confirm', {
    fileName: currentFileName.value,
    mode: selectedMode.value,
    tokenKey: currentGeneratedToken.value
  })
  dialogVisible.value = false
}

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    refreshSources()
    if (props.initialTxtName) {
      currentFileName.value = props.initialTxtName
    }
    if (props.initialMode) {
      selectedMode.value = props.initialMode
    }
  }
})
</script>

<style scoped>
.modal-body-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px 0;
}

/* ── 1. 单行文案源选择行 ── */
.source-select-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  flex-shrink: 0;
}

.select-box-wrap {
  flex: 1;
  min-width: 0;
}

.source-dropdown {
  width: 100%;
}

.opt-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.opt-name {
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.opt-meta {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

.source-btns {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.mini-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--el-border-color);
  background: #ffffff;
  color: var(--el-text-color-regular);
  transition: all 0.15s;
}

.mini-action-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.mini-action-btn.primary-btn {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
}

.mini-action-btn.primary-btn:hover {
  background: var(--el-color-primary-light-3);
}

.mini-action-btn.active {
  background: rgba(79, 70, 229, .09);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.mini-action-btn.delete-btn {
  padding: 0 10px;
  color: var(--el-text-color-placeholder);
}

.mini-action-btn.delete-btn:hover {
  border-color: var(--el-color-danger);
  color: var(--el-color-danger);
}

/* 粘贴文本抽屉 */
.paste-compact-panel {
  padding: 10px;
  background: var(--el-fill-color-lighter);
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.paste-compact-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.paste-name-input {
  max-width: 220px;
}

.paste-hint {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

.paste-compact-footer {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

/* ── 2. 分段控制器 Segmented Control ── */
.mode-control-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mode-segmented-bar {
  display: flex;
  background: var(--el-fill-color-light);
  padding: 3px;
  border-radius: 6px;
  gap: 4px;
}

.seg-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 30px;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: all 0.15s ease;
}

.seg-btn:hover {
  color: var(--el-text-color-primary);
}

.seg-btn.active {
  background: #ffffff;
  color: var(--el-color-primary);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.mode-caption {
  font-size: 11.5px;
  color: var(--el-text-color-placeholder);
  padding-left: 2px;
}

/* ── 3. 紧凑内容视窗 ── */
.preview-compact-box {
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 8px 12px;
  max-height: 120px;
  overflow-y: auto;
}

.no-content-tip {
  text-align: center;
  padding: 16px 0;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.9;
}

.preview-compact-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
  line-height: 20px;
}

.line-idx {
  font-family: monospace;
  color: var(--el-color-primary);
  font-weight: 600;
  width: 22px;
  flex-shrink: 0;
}

.line-txt {
  flex: 1;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-summary-row {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--el-border-color-lighter);
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.preview-summary-row strong {
  color: var(--el-color-primary);
}

/* ── Footer ── */
.dialog-footer-split {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.token-inline-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.tag-label {
  color: var(--el-text-color-secondary);
}

.tag-code {
  font-family: monospace;
  font-weight: 600;
  color: var(--el-color-primary);
  background: rgba(79, 70, 229, .10);
  padding: 1px 6px;
  border-radius: 4px;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
