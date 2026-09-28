<template>
  <div
    class="token-template-input-wrapper"
    :class="{ 'is-focused': isFocused, 'is-textarea': type === 'textarea' }"
  >
    <!-- 富标签编辑器主体 -->
    <div
      ref="editorRef"
      class="token-editor-box custom-scrollbar"
      contenteditable="true"
      :data-placeholder="placeholder"
      :style="{ minHeight: type === 'textarea' ? `${(rows || 3) * 24 + 16}px` : '38px' }"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeyDown"
      @paste="onPaste"
      @click="onEditorClick"
    ></div>

    <!-- 底部极简工具栏（直接点击唤起直观可视化弹窗） -->
    <div v-if="!hideTools" class="editor-bottom-bar">
      <div class="bottom-tools-left">
        <!-- 1. 插入变量入口 (直观树状层级弹窗) -->
        <button type="button" class="mini-tool-btn var-btn" @mousedown.prevent @click="openVarModal">
          <span class="btn-symbol">+</span>
          <span>插入变量</span>
        </button>

        <!-- 2. 插入 TXT 文案入口 (模式配置与多行预览弹窗) -->
        <button type="button" class="mini-tool-btn txt-btn" @mousedown.prevent @click="openTxtModal">
          <el-icon class="btn-icon"><Document /></el-icon>
          <span>插入 TXT 文案</span>
        </button>
      </div>

      <!-- 右侧：实时示例预览与字数 -->
      <div class="bottom-tools-right">
        <span v-if="previewText" class="preview-mini-tag" :title="previewText">
          <span class="preview-label">示例:</span>
          <span class="preview-content">{{ previewText }}</span>
          <button
            v-if="isContainingRandomMode"
            type="button"
            class="shuffle-tag-btn"
            title="随机换一行演示"
            @click.stop="shuffleRandomPreview"
          >
             换一行
          </button>
        </span>
        <span v-if="maxlength" class="word-count" :class="{ 'is-exceed': currentPlainText.length > maxlength }">
          {{ currentPlainText.length }}/{{ maxlength }}
        </span>
      </div>
    </div>

    <!-- 点击标签弹出的微调/切换浮层 -->
    <el-popover
      :visible="chipPopoverVisible"
      :virtual-ref="activeChipElement"
      virtual-triggering
      trigger="click"
      :width="280"
      placement="bottom-start"
      popper-class="token-chip-popover"
    >
      <div class="chip-popover-content" v-if="activeChipInfo">
        <div class="popover-header">
          <span class="popover-title">
            {{ activeChipInfo.type === 'var' ? '已选变量标签' : '已选 TXT 文案标签' }}
          </span>
          <el-button link type="danger" size="small" @click="removeActiveChip">
            <el-icon><Delete /></el-icon> 移除
          </el-button>
        </div>

        <div class="chip-popover-body">
          <div class="popover-token-badge">
            {{ activeChipInfo.rawKey }}
          </div>
          <div class="popover-action-row">
            <el-button size="small" type="primary" plain @click="reconfigureActiveChip">
              <el-icon><Operation /></el-icon> 更换 / 重新设置
            </el-button>
          </div>
        </div>
      </div>
    </el-popover>

    <!-- 变量可视化选择中心弹窗 (含路径树状图) -->
    <VariableSelectModal
      v-model="varModalVisible"
      :sample-media="sampleMedia"
      :unit-level="unitLevel"
      :rule-config="ruleConfig"
      :initial-key="modalInitialVarKey"
      @select="handleVarSelectFromModal"
    />

    <!-- TXT 文案模式与源配置弹窗 -->
    <TxtSourceModal
      v-model="txtModalVisible"
      :initial-txt-name="modalInitialTxtName"
      :initial-mode="modalInitialTxtMode"
      @confirm="handleTxtConfirmFromModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { Document, Delete, Operation, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import VariableSelectModal from '../dialogs/VariableSelectModal.vue'
import TxtSourceModal from '../dialogs/TxtSourceModal.vue'
import {
  buildDynamicVariables,
  resolveTemplateString,
  getTxtSource,
  getAllTxtSources,
  AVAILABLE_VARIABLES,
  type AvailableVariable,
  type TxtDistributionMode
} from '../../../utils/matrixHelper'
import type { MediaItem, BatchRuleConfig } from '../../../types/matrix'

const props = withDefaults(defineProps<{
  modelValue: string
  type?: 'input' | 'textarea'
  placeholder?: string
  maxlength?: number
  rows?: number
  hideTools?: boolean
  sampleMedia?: Partial<MediaItem>
  unitLevel?: number
  ruleConfig?: Partial<BatchRuleConfig>
}>(), {
  modelValue: '',
  type: 'input',
  placeholder: '请输入内容，支持插入变量或导入TXT...',
  rows: 3,
  hideTools: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()

const editorRef = ref<HTMLDivElement>()
const fileInputRef = ref<HTMLInputElement>()
const isFocused = ref(false)

// 缓存最后一次光标选区
let lastSavedRange: Range | null = null

// Popover 交互控制
const chipPopoverVisible = ref(false)
const activeChipElement = ref<HTMLElement | null>(null)
const activeChipInfo = ref<{
  type: 'var' | 'txt'
  rawKey: string
  txtName?: string
} | null>(null)

// 正在被重新配置编辑的已有标签节点
const editingChipElement = ref<HTMLElement | null>(null)
// 随机预览触发种子
const randomPreviewSeed = ref(0)

const isContainingRandomMode = computed(() => {
  return props.modelValue.includes(':random')
})

function shuffleRandomPreview() {
  randomPreviewSeed.value = Math.floor(Math.random() * 100000) + 1
}

// 弹窗状态管理
const varModalVisible = ref(false)
const modalInitialVarKey = ref('')

const txtModalVisible = ref(false)
const modalInitialTxtName = ref('')
const modalInitialTxtMode = ref<TxtDistributionMode>('seq')

// 计算可选变量
const computedVars = computed<AvailableVariable[]>(() => {
  if (props.sampleMedia && props.sampleMedia.fileName) {
    return buildDynamicVariables(props.sampleMedia, props.unitLevel, props.ruleConfig)
  }
  return AVAILABLE_VARIABLES
})

// 已注册的所有 TXT 源列表
const existingTxtSources = computed(() => {
  return getAllTxtSources()
})

function getTxtLines(txtName?: string): string[] {
  if (!txtName) return []
  return getTxtSource(txtName) || []
}

// 实时预览文本（以第 1 个视频为例，过滤回车保持单行规整）
const previewText = computed(() => {
  if (!props.modelValue) return ''
  const dummyMedia = props.sampleMedia || { fileName: '示例视频_第01集.mp4' }
  try {
    const raw = resolveTemplateString(
      props.modelValue,
      dummyMedia,
      0,
      props.ruleConfig,
      props.unitLevel,
      randomPreviewSeed.value
    )
    return raw.replace(/[\r\n]+/g, ' ').trim()
  } catch {
    return props.modelValue.replace(/[\r\n]+/g, ' ').trim()
  }
})

// 当前纯文本长度（过滤掉标签内部结构）
const currentPlainText = computed(() => {
  return props.modelValue || ''
})

/* ────────── DOM 与 modelValue 互转逻辑 ────────── */

/** 将标准模板字符串解析并渲染为富 DOM */
function renderModelValueToDOM(val: string) {
  if (!editorRef.value) return

  // 防止正在输入时重绘破坏光标
  const serialized = serializeDOMToValue()
  if (serialized === val && (editorRef.value.childNodes.length > 0 || !val)) {
    return
  }

  editorRef.value.innerHTML = ''
  if (!val) return

  // 正则切分普通文本与占位符 {TXT:xxx} 或 {xxx}
  const regex = /(\{TXT:[^}]+\}|\{[^}]+\})/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(val)) !== null) {
    if (match.index > lastIndex) {
      const textPiece = val.substring(lastIndex, match.index)
      insertTextNodeToEditor(textPiece)
    }
    const tokenStr = match[1]
    const chipNode = createChipDOM(tokenStr)
    editorRef.value.appendChild(chipNode)
    // 关键：在每个 chip 后追加一个零宽占位符，为光标移动与退格删除提供物理着陆点
    editorRef.value.appendChild(document.createTextNode('\u200B'))
    lastIndex = regex.lastIndex
  }

  if (lastIndex < val.length) {
    insertTextNodeToEditor(val.substring(lastIndex))
  }
}

function insertTextNodeToEditor(text: string) {
  if (!editorRef.value) return
  // 处理换行符
  const parts = text.split('\n')
  for (let i = 0; i < parts.length; i++) {
    if (parts[i]) {
      editorRef.value.appendChild(document.createTextNode(parts[i]))
    }
    if (i < parts.length - 1) {
      editorRef.value.appendChild(document.createElement('br'))
    }
  }
}

/** 创建标签 DOM 节点 */
function createChipDOM(token: string): HTMLSpanElement {
  const span = document.createElement('span')
  span.className = 'rich-token-chip'
  span.contentEditable = 'false'
  span.setAttribute('data-token', token)

  if (token.startsWith('{TXT:')) {
    const rawInner = token.replace(/^\{TXT:/, '').replace(/\}$/, '').trim()
    const parts = rawInner.split(':')
    const txtName = parts[0]
    const mode = parts[1] === 'random' ? '随机' : '循环'
    span.classList.add('is-txt')
    const lines = getTxtSource(txtName) || []
    const countText = lines.length ? `(${lines.length}行·${mode})` : `(${mode})`
    span.innerHTML = `
      <span class="chip-inner">
        <span class="chip-ico">📄</span>
        <span class="chip-lbl">${escapeHtml(txtName)} ${countText}</span>
        <span class="chip-caret">▾</span>
      </span>
    `
  } else {
    span.classList.add('is-var')
    const varDef = computedVars.value.find(v => v.key === token)
    const label = varDef ? varDef.label : token.replace(/[\{\}]/g, '')
    span.innerHTML = `
      <span class="chip-inner">
        <span class="chip-ico">🏷️</span>
        <span class="chip-lbl">${escapeHtml(label)}</span>
        <span class="chip-caret">▾</span>
      </span>
    `
  }

  return span
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

/** 将 DOM 序列化为标准模板字符串 */
function serializeDOMToValue(): string {
  if (!editorRef.value) return ''
  let result = ''
  
  function traverse(node: Node) {
    if (node.nodeType === Node.TEXT_NODE) {
      result += node.textContent || ''
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      const el = node as HTMLElement
      if (el.classList.contains('rich-token-chip')) {
        result += el.getAttribute('data-token') || ''
      } else if (el.tagName === 'BR') {
        result += '\n'
      } else if (el.tagName === 'DIV' || el.tagName === 'P') {
        if (result.length > 0 && !result.endsWith('\n')) {
          result += '\n'
        }
        el.childNodes.forEach(traverse)
      } else {
        el.childNodes.forEach(traverse)
      }
    }
  }

  editorRef.value.childNodes.forEach(traverse)
  // 剥离不可见零宽占位符 \u200B
  return result.replace(/\u200B/g, '')
}

/* ────────── 编辑器交互与光标事件 ────────── */

function saveSelection() {
  const sel = window.getSelection()
  if (sel && sel.rangeCount > 0 && editorRef.value) {
    const range = sel.getRangeAt(0)
    if (editorRef.value.contains(range.commonAncestorContainer)) {
      lastSavedRange = range.cloneRange()
    }
  }
}

let isInternalUpdate = false
let internalUpdateTimer: any = null

function restoreSelection() {
  if (lastSavedRange && editorRef.value) {
    const sel = window.getSelection()
    if (sel) {
      if (sel.setBaseAndExtent && lastSavedRange.startContainer === lastSavedRange.endContainer) {
        try {
          sel.setBaseAndExtent(
            lastSavedRange.startContainer,
            lastSavedRange.startOffset,
            lastSavedRange.endContainer,
            lastSavedRange.endOffset
          )
          return
        } catch {}
      }
      sel.removeAllRanges()
      sel.addRange(lastSavedRange)
    }
  }
}

function onInput() {
  saveSelection()
  const val = serializeDOMToValue()
  isInternalUpdate = true
  if (internalUpdateTimer) {
    clearTimeout(internalUpdateTimer)
  }
  internalUpdateTimer = setTimeout(() => {
    isInternalUpdate = false
  }, 150)
  emit('update:modelValue', val)
}

function onFocus() {
  isFocused.value = true
  saveSelection()
}

function onBlur() {
  isFocused.value = false
  saveSelection()
}

function isChipNode(node: Node | null | undefined): boolean {
  if (!node || node.nodeType !== Node.ELEMENT_NODE) return false
  return (node as HTMLElement).classList?.contains('rich-token-chip') || false
}

/** 识别非折叠选区是否选中了单个标签 */
function getSelectedChip(range: Range): HTMLElement | null {
  if (range.collapsed) return null
  if (range.startContainer === range.endContainer) {
    const container = range.startContainer
    if (container.nodeType === Node.ELEMENT_NODE) {
      if (range.endOffset === range.startOffset + 1) {
        const node = container.childNodes[range.startOffset]
        if (isChipNode(node)) return node as HTMLElement
      }
    }
  }
  if (range.commonAncestorContainer) {
    const common = range.commonAncestorContainer
    if (isChipNode(common)) return common as HTMLElement
  }
  return null
}

function removeChipAndPlaceCaret(chipNode: Node) {
  if (!editorRef.value) return

  const parent = chipNode.parentNode
  if (!parent) return

  const prev = chipNode.previousSibling
  const next = chipNode.nextSibling

  // 1. 优先确定目标定位节点与偏移量，并在物理移除 chipNode 前就将光标安全迁移
  // 彻底避免在 removeChild 时浏览器因选区节点被孤立而默认将光标回退到最顶部 (editorRef, 0)
  let targetNode: Node
  let targetOffset: number

  if (prev && prev.nodeType === Node.TEXT_NODE) {
    targetNode = prev
    targetOffset = prev.textContent?.length || 0
  } else if (next && next.nodeType === Node.TEXT_NODE) {
    targetNode = next
    targetOffset = 0
  } else {
    // 若前后均无文本节点，在 chipNode 前插入一个零宽文本节点作为安全着陆点
    const zws = document.createTextNode('\u200B')
    parent.insertBefore(zws, chipNode)
    targetNode = zws
    targetOffset = 0
  }

  // 先把光标原子定位到 targetNode（此时 chipNode 还在 DOM 中，选区迁移绝不会异常）
  const sel = window.getSelection()
  if (sel) {
    if (sel.setBaseAndExtent) {
      try {
        sel.setBaseAndExtent(targetNode, targetOffset, targetNode, targetOffset)
      } catch {}
    } else {
      try {
        const range = document.createRange()
        range.setStart(targetNode, targetOffset)
        range.collapse(true)
        sel.removeAllRanges()
        sel.addRange(range)
      } catch {}
    }
  }

  // 2. 光标已经安全脱离 chipNode，此时移除 chipNode 不会造成选区孤立或归零
  parent.removeChild(chipNode)

  // 3. 再次确认光标位置（防止某些浏览器在 removeChild 时强制重置）
  if (sel && targetNode.parentNode) {
    if (sel.setBaseAndExtent) {
      try {
        sel.setBaseAndExtent(targetNode, targetOffset, targetNode, targetOffset)
      } catch {}
    }
  }

  saveSelection()
  onInput()
}

function handleBackspace(e: KeyboardEvent): boolean {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || !editorRef.value) return false

  const range = sel.getRangeAt(0)
  if (!range.collapsed) {
    const selectedChip = getSelectedChip(range)
    if (selectedChip) {
      e.preventDefault()
      removeChipAndPlaceCaret(selectedChip)
      return true
    }
    return false
  }

  const container = range.startContainer
  const offset = range.startOffset

  // 1. 光标在元素节点（editorRef 或内部多行 div/p）的直接子节点之间
  if (container.nodeType === Node.ELEMENT_NODE && editorRef.value.contains(container)) {
    if (offset > 0) {
      const prev = container.childNodes[offset - 1]
      if (isChipNode(prev)) {
        e.preventDefault()
        removeChipAndPlaceCaret(prev)
        return true
      }
    }
  }

  // 2. 光标在文本节点内部且在开头（光标前无任何可见字符）
  if (container.nodeType === Node.TEXT_NODE && editorRef.value.contains(container)) {
    const textBeforeCaret = (container.textContent || '').slice(0, offset)
    const isAtStart = offset === 0 || textBeforeCaret.replace(/\u200B/g, '').length === 0
    if (isAtStart) {
      let prev = container.previousSibling
      while (prev && prev.nodeType === Node.TEXT_NODE && (prev.textContent || '').replace(/\u200B/g, '') === '') {
        prev = prev.previousSibling
      }
      if (isChipNode(prev)) {
        e.preventDefault()
        removeChipAndPlaceCaret(prev!)
        return true
      }
    }
  }

  return false
}

function handleDelete(e: KeyboardEvent): boolean {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || !editorRef.value) return false

  const range = sel.getRangeAt(0)
  if (!range.collapsed) {
    const selectedChip = getSelectedChip(range)
    if (selectedChip) {
      e.preventDefault()
      removeChipAndPlaceCaret(selectedChip)
      return true
    }
    return false
  }

  const container = range.startContainer
  const offset = range.startOffset

  // 1. 光标在元素节点（editorRef 或内部多行 div/p）的直接子节点之间
  if (container.nodeType === Node.ELEMENT_NODE && editorRef.value.contains(container)) {
    if (offset < container.childNodes.length) {
      const next = container.childNodes[offset]
      if (isChipNode(next)) {
        e.preventDefault()
        removeChipAndPlaceCaret(next)
        return true
      }
    }
  }

  // 2. 光标在文本节点内部且在末尾（光标后无任何可见字符）
  if (container.nodeType === Node.TEXT_NODE && editorRef.value.contains(container)) {
    const textAfterCaret = (container.textContent || '').slice(offset)
    const isAtEnd = offset === (container.textContent || '').length || textAfterCaret.replace(/\u200B/g, '').length === 0
    if (isAtEnd) {
      let next = container.nextSibling
      while (next && next.nodeType === Node.TEXT_NODE && (next.textContent || '').replace(/\u200B/g, '') === '') {
        next = next.nextSibling
      }
      if (isChipNode(next)) {
        e.preventDefault()
        removeChipAndPlaceCaret(next!)
        return true
      }
    }
  }

  return false
}

function onKeyDown(e: KeyboardEvent) {
  // 单行模式下回车禁止换行
  if (props.type === 'input' && e.key === 'Enter') {
    e.preventDefault()
    return
  }

  if (e.key === 'Backspace') {
    if (handleBackspace(e)) return
  }

  if (e.key === 'Delete') {
    if (handleDelete(e)) return
  }
}

function onPaste(e: ClipboardEvent) {
  e.preventDefault()
  const text = e.clipboardData?.getData('text/plain') || ''
  if (!text) return

  // 纯文本插值
  document.execCommand('insertText', false, text)
  onInput()
}

/** 监听编辑区内点击，若是标签则弹出交互浮层 */
function onEditorClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.rich-token-chip') as HTMLElement | null
  if (target && editorRef.value?.contains(target)) {
    e.stopPropagation()
    const token = target.getAttribute('data-token') || ''
    activeChipElement.value = target

    if (token.startsWith('{TXT:')) {
      const rawInner = token.replace(/^\{TXT:/, '').replace(/\}$/, '').trim()
      const parts = rawInner.split(':')
      const txtName = parts[0]
      activeChipInfo.value = {
        type: 'txt',
        rawKey: token,
        txtName
      }
    } else {
      activeChipInfo.value = {
        type: 'var',
        rawKey: token
      }
    }
    chipPopoverVisible.value = true
  } else {
    chipPopoverVisible.value = false
    saveSelection()
  }
}

/* ────────── 插入标签逻辑 ────────── */

function insertTokenToEditor(tokenStr: string) {
  if (!editorRef.value) return
  editorRef.value.focus()
  restoreSelection()

  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) {
    // 兜底插入在最后
    const chip = createChipDOM(tokenStr)
    editorRef.value.appendChild(chip)
    // 补一个空格
    editorRef.value.appendChild(document.createTextNode(' '))
  } else {
    const range = sel.getRangeAt(0)
    range.deleteContents()
    const chip = createChipDOM(tokenStr)
    range.insertNode(chip)
    
    // 光标移到标签之后并加空格
    const spaceNode = document.createTextNode(' ')
    if (chip.nextSibling) {
      editorRef.value.insertBefore(spaceNode, chip.nextSibling)
    } else {
      editorRef.value.appendChild(spaceNode)
    }

    const newRange = document.createRange()
    newRange.setStartAfter(spaceNode)
    newRange.collapse(true)
    sel.removeAllRanges()
    sel.addRange(newRange)
    saveSelection()
  }

  onInput()
}

function openVarModal() {
  saveSelection()
  editingChipElement.value = null
  modalInitialVarKey.value = ''
  varModalVisible.value = true
}

function openTxtModal() {
  saveSelection()
  editingChipElement.value = null
  modalInitialTxtName.value = ''
  modalInitialTxtMode.value = 'seq'
  txtModalVisible.value = true
}

function applyToken(tokenStr: string) {
  if (editingChipElement.value && editorRef.value?.contains(editingChipElement.value)) {
    const newChip = createChipDOM(tokenStr)
    editingChipElement.value.replaceWith(newChip)
    editingChipElement.value = null
    onInput()
  } else {
    insertTokenToEditor(tokenStr)
  }
}

function handleVarSelectFromModal(varKey: string) {
  applyToken(varKey)
}

function handleTxtConfirmFromModal(payload: { fileName: string; mode: TxtDistributionMode; tokenKey: string }) {
  applyToken(payload.tokenKey)
}

function reconfigureActiveChip() {
  chipPopoverVisible.value = false
  if (!activeChipInfo.value || !activeChipElement.value) return
  editingChipElement.value = activeChipElement.value

  if (activeChipInfo.value.type === 'var') {
    modalInitialVarKey.value = activeChipInfo.value.rawKey
    varModalVisible.value = true
  } else if (activeChipInfo.value.type === 'txt') {
    modalInitialTxtName.value = activeChipInfo.value.txtName || ''
    modalInitialTxtMode.value = activeChipInfo.value.rawKey.includes(':random') ? 'random' : 'seq'
    txtModalVisible.value = true
  }
}

/* ────────── Popover 浮层动作 ────────── */

function removeActiveChip() {
  if (activeChipElement.value) {
    const el = activeChipElement.value
    chipPopoverVisible.value = false
    editorRef.value?.focus()
    removeChipAndPlaceCaret(el)
    activeChipElement.value = null
  }
}

function switchChipVariable(newKey: string) {
  if (activeChipElement.value) {
    const newChip = createChipDOM(newKey)
    activeChipElement.value.replaceWith(newChip)
    chipPopoverVisible.value = false
    onInput()
  }
}

function triggerUploadReplace() {
  chipPopoverVisible.value = false
  fileInputRef.value?.click()
}

/** 在光标处安全插入文本（如添加话题 #），并保持光标跟随在插入字符之后 */
function insertText(text: string) {
  if (!editorRef.value) return
  editorRef.value.focus()
  restoreSelection()

  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || !editorRef.value.contains(sel.anchorNode)) {
    setCursorToEnd()
  }

  document.execCommand('insertText', false, text)
  onInput()
  saveSelection()
}

/** 将光标定位至文本末尾 */
function setCursorToEnd() {
  if (!editorRef.value) return
  editorRef.value.focus()
  const sel = window.getSelection()
  if (!sel) return

  if (sel.setBaseAndExtent && editorRef.value.lastChild) {
    const last = editorRef.value.lastChild
    const len = last.nodeType === Node.TEXT_NODE ? (last.textContent?.length || 0) : 1
    try {
      sel.setBaseAndExtent(last, len, last, len)
      saveSelection()
      return
    } catch {}
  }

  const range = document.createRange()
  range.selectNodeContents(editorRef.value)
  range.collapse(false)
  sel.removeAllRanges()
  sel.addRange(range)
  saveSelection()
}

/* ────────── 监听与挂载 ────────── */

watch(() => props.modelValue, (newVal) => {
  // 1. 若是输入框内部触发的变更，跳过 DOM 重绘，保护光标绝不跳动
  if (isInternalUpdate) {
    return
  }
  // 2. 关键防御：若当前 DOM 序列化后的内容与新值一致，绝不进行全量 DOM 重绘！
  if (editorRef.value) {
    const currentVal = serializeDOMToValue()
    if (currentVal === (newVal || '')) {
      return
    }
  }
  renderModelValueToDOM(newVal || '')
})

onMounted(() => {
  renderModelValueToDOM(props.modelValue || '')
})

defineExpose({
  insertText,
  focus: () => {
    editorRef.value?.focus()
    setCursorToEnd()
  },
  setCursorToEnd
})
</script>

<style scoped>
.token-template-input-wrapper {
  background: var(--bg-input, #ffffff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
  overflow: hidden;
}

.token-template-input-wrapper:hover {
  border-color: var(--primary-color, #4f46e5);
}

.token-template-input-wrapper.is-focused {
  border-color: var(--primary-color, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}

/* ── 富标签可编辑区域 ── */
.token-editor-box {
  width: 100%;
  padding: 8px 12px;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-main, #1e293b);
  outline: none;
  cursor: text;
  word-break: break-word;
  white-space: pre-wrap;
  box-sizing: border-box;
  overflow-y: auto;
  position: relative;
}

/* 占位符处理 */
.token-editor-box:empty::before {
  content: attr(data-placeholder);
  color: var(--text-muted, #94a3b8);
  pointer-events: none;
  display: block;
}

/* ── 标签胶囊样式（全局类名，注入在 contenteditable 中） ── */
:deep(.rich-token-chip) {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
  margin: 1px 3px;
  padding: 1px 7px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 500;
  user-select: all;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 20px;
}

:deep(.rich-token-chip.is-var) {
  background: rgba(79, 70, 229, 0.1);
  color: var(--primary-color, #4f46e5);
  border: 1px solid rgba(79, 70, 229, 0.25);
}

:deep(.rich-token-chip.is-var:hover) {
  background: rgba(79, 70, 229, 0.18);
  border-color: var(--primary-color, #4f46e5);
}

:deep(.rich-token-chip.is-txt) {
  background: rgba(14, 165, 233, 0.1);
  color: #0284c7;
  border: 1px solid rgba(14, 165, 233, 0.28);
}

:deep(.rich-token-chip.is-txt:hover) {
  background: rgba(14, 165, 233, 0.18);
  border-color: #0284c7;
}

:deep(.rich-token-chip .chip-inner) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

:deep(.rich-token-chip .chip-caret) {
  font-size: 10px;
  opacity: 0.6;
}

/* ── 底部精炼工具栏 (防御性单行防挤压) ── */
.editor-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.015);
  border-top: 1px solid var(--border-subtle, #f1f5f9);
  min-height: 32px;
  box-sizing: border-box;
  gap: 8px;
  width: 100%;
  overflow: hidden;
}

.bottom-tools-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0; /* 铁律: 左侧操作按钮区绝对禁止被挤压收缩 */
  white-space: nowrap;
}

.mini-tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 8px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--border-subtle, #e2e8f0);
  background: #ffffff;
  color: var(--text-main, #334155);
  transition: all 0.15s ease;
  flex-shrink: 0;
  white-space: nowrap;
}

.mini-tool-btn:hover {
  border-color: var(--primary-color, #4f46e5);
  color: var(--primary-color, #4f46e5);
}

.mini-tool-btn.txt-btn:hover {
  border-color: #0284c7;
  color: #0284c7;
}

.btn-symbol {
  font-weight: 700;
  font-size: 13px;
  color: var(--primary-color, #4f46e5);
}

.btn-arrow {
  font-size: 10px;
  opacity: 0.7;
}

.bottom-tools-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  min-width: 0; /* 允许在空间受限时整体自适应收缩 */
  flex-shrink: 1;
  overflow: hidden;
  justify-content: flex-end;
}

.preview-mini-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted, #64748b);
  max-width: 190px; /* 严格限制最大宽度，绝不侵占左侧按钮 */
  min-width: 0;
  flex-shrink: 1;
  overflow: hidden;
  white-space: nowrap;
  background: rgba(79, 70, 229, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
}

.preview-label {
  font-weight: 600;
  color: var(--primary-color, #4f46e5);
  flex-shrink: 0;
}

.preview-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.word-count {
  font-size: 11.5px;
  color: var(--text-muted, #94a3b8);
  flex-shrink: 0;
  white-space: nowrap;
}

.word-count.is-exceed {
  color: var(--status-danger, #ef4444);
  font-weight: 700;
}

/* ── 下拉菜单样式 ── */
.token-dropdown-menu {
  max-height: 280px;
  overflow-y: auto;
}

.token-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
}

.var-badge-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(79, 70, 229, 0.1);
  color: var(--primary-color, #4f46e5);
  font-weight: 600;
}

.var-badge-tag.is-level {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.var-badge-key {
  font-size: 12px;
  color: var(--text-muted, #64748b);
  font-family: monospace;
}

.var-badge-sample {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  margin-left: auto;
}

.txt-badge-tag {
  font-size: 12px;
  font-weight: 600;
  color: #0284c7;
}

.txt-badge-desc {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  margin-left: auto;
}

/* ── Popover 浮层内容 ── */
.chip-popover-content {
  padding: 6px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #f1f5f9);
}

.popover-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main, #1e293b);
}

.chip-popover-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.popover-token-badge {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-color, #4f46e5);
  background: rgba(79, 70, 229, 0.08);
  padding: 6px 10px;
  border-radius: 6px;
  text-align: center;
  word-break: break-all;
}

.popover-action-row {
  display: flex;
  justify-content: flex-end;
}

.shuffle-tag-btn {
  border: none;
  background: rgba(79, 70, 229, 0.15);
  color: var(--primary-color, #4f46e5);
  font-size: 10px;
  font-weight: 600;
  border-radius: 3px;
  padding: 1px 5px;
  cursor: pointer;
  margin-left: 4px;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
  flex-shrink: 0;
  white-space: nowrap;
}

.shuffle-tag-btn:hover {
  background: var(--primary-color, #4f46e5);
  color: #ffffff;
}

</style>
