<template>
  <el-dialog
    v-model="dialogVisible"
    title="插入内容"
    width="480px"
    destroy-on-close
    append-to-body
    class="variable-select-modal"
  >
    <input
    ref="txtFileInputRef"
    type="file"
    accept=".txt,text/plain"
    style="display: none"
    @change="onTxtFileSelected"
  />
  <div class="modal-form">
      <!-- 步骤 1：选择插入的内容 -->
      <div class="step-title">
        <span class="step-n">1</span>
        <span>选择插入的内容</span>
      </div>

      <div class="var-tabs">
        <button
          v-for="t in varTabs"
          :key="t.id"
          type="button"
          class="var-tab"
          :class="{ on: activeVarTab === t.id }"
          @click="activeVarTab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- Tab 内容：内容 / 文件夹 / 时间（都是变量） -->
      <div class="var-list" v-if="activeVarTab !== 'txt'">
        <div
          v-for="opt in filteredVarOptions"
          :key="opt.value"
          class="var-opt"
          :class="{ on: selectedVarKey === opt.value }"
          @click="selectedVarKey = opt.value; handleSelectChange(opt.value)"
        >
          <span class="vo-radio"></span>
          <span class="vo-ic">{{ opt.icon }}</span>
          <div class="vo-meta">
            <div class="vo-name">{{ opt.title }}</div>
            <div class="vo-sub" v-if="opt.desc">{{ opt.desc }}</div>
          </div>
          <span class="vo-val" :title="opt.sample">{{ opt.sample }}</span>
        </div>
      </div>

      <!-- Tab 内容：文案库 -->
      <div
        v-else
        class="var-list"
      >
        <!-- 已有文案库（列表在上） -->
        <template v-if="existingTxtSources.length > 0">
          <div
            v-for="src in existingTxtSources"
            :key="src.fileName"
            class="var-opt"
            :class="{ on: selectedTxtName === src.fileName }"
            @click="selectTxtSource(src.fileName)"
          >
            <span class="vo-radio"></span>
            <span class="vo-ic">📄</span>
            <div class="vo-meta">
              <div class="vo-name">{{ src.fileName.replace(/\.txt$/, '') }}</div>
              <div class="vo-sub">{{ src.lines.length }} 行 · {{ modeLabel }}</div>
            </div>
            <span class="vo-val" :title="src.lines[0]">{{ src.lines[0] || '（空）' }}</span>
            <button
              type="button"
              class="vo-del"
              title="从列表中移除"
              @click.stop="removeTxtSource(src.fileName)"
            >🗑</button>
          </div>
          <!-- 列表与动作之间的分隔线 -->
          <div class="vo-sep"></div>
        </template>

        <!-- ① 选择文件导入（主色高亮） -->
        <div class="var-opt vo-new vo-primary" @click="triggerTxtFileInput">
          <span class="vo-radio" style="visibility:hidden"></span>
          <span class="vo-ic">📂</span>
          <div class="vo-meta">
            <div class="vo-name">选择文件导入</div>
            <div class="vo-sub">支持 .txt，每行一条文案</div>
          </div>
        </div>
      </div>

      <!-- 文案库的诊断模式（选中后出现） -->
      <div class="txt-mode-row" v-if="activeVarTab === 'txt' && selectedTxtName">
        <span class="tm-label">轮换方式</span>
        <div class="tm-seg">
          <button type="button" :class="{ on: selectedMode === 'seq' }" @click="selectedMode = 'seq'">顺序循环</button>
          <button type="button" :class="{ on: selectedMode === 'random' }" @click="selectedMode = 'random'">随机抽取</button>
        </div>
        <span class="tm-hint">
          {{ selectedMode === 'seq' ? '多视频依次按行填入，超出后循环' : '每个视频随机分配一行，防重复' }}
        </span>
      </div>

      <!-- 步骤 2：命名 -->
      <div class="step-title" style="margin-top:18px;">
        <span class="step-n">2</span>
        <span>给这个变量起个名字</span>
      </div>
      <el-input
        ref="varNameInputRef"
        v-model="customVarName"
        placeholder="选填，如：剧名、专题名、商品名…"
        size="large"
        clearable
        class="variable-input"
        @input="onVarNameManualInput"
        @keyup.enter="confirmInsert"
      />
      <div class="name-hint">只是个名字，不影响实际内容 · 留空自动用默认名</div>

      <!-- 预览 -->
      <div class="preview-card">
        <div class="preview-item">
          <span class="preview-label">插入后</span>
          <span class="token-code">{{ displayChipName }}</span>
          <span style="opacity:.4">→</span>
          <span class="preview-value" :title="currentPreviewValue">
            {{ currentPreviewValue || '（空）' }}
          </span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!canConfirm" @click="confirmInsert">
          确定插入
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  EditPen
} from '@element-plus/icons-vue'
import FolderIcon from '../../common/FolderIcon.vue'
import {
  parseFolderHierarchy,
  resolveTemplateString,
  registerCustomVariable,
  getAllTxtSources,
  registerTxtSource,
  deleteTxtSource
} from '../../../utils/matrixHelper'
import type { BatchRuleConfig } from '../../../types/matrix'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Props {
  modelValue: boolean
  sampleMedia?: {
    fileName?: string
    filePath?: string
    folderCrumbs?: string[]
    parsedEpisode?: number
  }
  unitLevel?: number
  ruleConfig?: Partial<BatchRuleConfig>
  initialKey?: string
  /** 打开时要预先选中的文案文件（点已插入的标签来重新配置时用） */
  initialTxtName?: string
  initialTxtMode?: 'seq' | 'random'
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  unitLevel: 1,
  initialKey: '',
  initialTxtName: '',
  initialTxtMode: 'seq'
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'select', varKey: string, chipName?: string): void
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const varNameInputRef = ref<any>(null)

// 解析示例媒体的各级目录树
const folderHierarchy = computed(() => {
  return parseFolderHierarchy(props.sampleMedia)
})

/** 图标映射 */
function getIcon(value: string): string {
  if (value === '{视频名}') return '📄'
  if (value.startsWith('{第') && value.includes('层目录}')) return '📁'
  if (value === '{日期}' || value === '{时间}') return '📅'
  if (value === '{文件夹名}') return '📁'
  return '📋'
}

// 下拉框选项：文件夹层级结构 + 视频素材 + 内容 + 时间
const folderOptions = computed(() => {
  const list: Array<{
    value: string
    label: string
    title: string
    chipName: string
    desc?: string
    badge?: string
    badgeClass?: string
    sample: string
    defaultName: string
    icon: string
    group: string
  }> = []

  // 内容组
  list.push({
    value: '{视频名}',
    label: `{视频名} (${folderHierarchy.value.sampleFileName})`,
    title: '视频文件名',
    chipName: '视频名',
    desc: '自动去掉 .mp4 这类扩展名',
    badge: '当前素材',
    badgeClass: 'is-file',
    sample: folderHierarchy.value.sampleFileName.replace(/\.[^/.]+$/, ''),
    defaultName: '视频名',
    icon: '📄',
    group: 'content'
  })

  // 文件夹层级
  folderHierarchy.value.nodes.forEach(node => {
    let badge = `第${node.level}层`
    let badgeClass = ''
    const desc = '取该文件夹的名字'
    if (node.isRoot) {
      badge = '根目录'
      badgeClass = 'is-root'
    } else if (node.isDirectParent) {
      badge = '直属目录'
      badgeClass = 'is-parent'
    }

    list.push({
      value: node.varKey,
      label: `${node.varKey} (${node.folderName})`,
      title: `第 ${node.level} 层文件夹`,
      chipName: `第${node.level}层`,
      desc,
      badge,
      badgeClass,
      sample: node.folderName,
      defaultName: `第${node.level}层`,
      icon: '📁',
      group: 'folder'
    })
  })

  // 时间组
  list.push({
    value: '{日期}',
    label: '{日期}',
    title: '日期',
    chipName: '日期',
    desc: '发布当天的日期',
    sample: new Date().toISOString().slice(0, 10),
    defaultName: '日期',
    icon: '📅',
    group: 'time'
  })

  list.push({
    value: '{时间}',
    label: '{时间}',
    title: '时间',
    chipName: '时间',
    desc: '发布时的时刻',
    sample: new Date().toTimeString().slice(0, 5),
    defaultName: '时间',
    icon: '🕐',
    group: 'time'
  })

  return list
})

/** 文案库相关 */
const selectedTxtName = ref('')
const selectedMode = ref<'seq' | 'random'>('seq')
const existingTxtSources = computed(() => getAllTxtSources())
const modeLabel = computed(() => selectedMode.value === 'random' ? '随机' : '顺序循环')

/* ───── 文案库：导入 ───── */
const txtFileInputRef = ref<HTMLInputElement | null>(null)

function selectTxtSource(fileName: string) {
  selectedTxtName.value = fileName
}

/** 隐藏的文件选择 input → 点一下直接弹系统文件选择器 */
function triggerTxtFileInput() {
  txtFileInputRef.value?.click()
}

async function onTxtFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const text = await file.text()
  registerTxtSource(file.name, text)
  selectedTxtName.value = file.name
  ElMessage.success(`已导入：${file.name}`)
  input.value = ''
}

/** 移除文案文件 */
function removeTxtSource(fileName: string) {
  ElMessageBox.confirm(
    `确定移除「${fileName.replace(/\.txt$/, '')}」吗？已插入的文字不会受影响。`,
    '移除文案文件',
    { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' }
  ).then(() => {
    deleteTxtSource(fileName)
    if (selectedTxtName.value === fileName) selectedTxtName.value = ''
    ElMessage.success('已移除')
  }).catch(() => {})
}

/** Tab 定义（固定顺序：导入文本 / 内容 / 文件夹 / 时间，去掉数字徽章） */
const varTabs = [
  { id: 'txt' as const,      label: '导入文本' },
  { id: 'content' as const,  label: '内容' },
  { id: 'folder' as const,   label: '文件夹' },
  { id: 'time' as const,     label: '时间' }
]

/** 记住上次 Tab：首次为导入文本，之后从 localStorage 读取 */
const LAST_TAB_KEY = 'sau_matrix_last_var_tab'
function loadLastTab(): typeof varTabs[number]['id'] {
  const saved = localStorage.getItem(LAST_TAB_KEY)
  if (saved && varTabs.some(t => t.id === saved)) return saved as typeof varTabs[number]['id']
  return 'txt'
}
const activeVarTab = ref<typeof varTabs[number]['id']>(loadLastTab())

/** 监听 Tab 切换，持久化到 localStorage */
watch(activeVarTab, (tabId) => {
  localStorage.setItem(LAST_TAB_KEY, tabId)
})

/** 当前 Tab 下的变量选项 */
const filteredVarOptions = computed(() =>
  folderOptions.value.filter(o => o.group === activeVarTab.value)
)

// 1. 变量名称
const customVarName = ref<string>('')
// 用户是否主动自定义编辑过变量名
const isUserManuallyEdited = ref<boolean>(false)

function onVarNameManualInput() {
  isUserManuallyEdited.value = true
}

// 2. 选择变量类型
const selectedVarKey = ref<string>('{第1层目录}')

// 当用户切换变量类型时
function handleSelectChange(val: string) {
  const opt = folderOptions.value.find(o => o.value === val)
  // 如果用户未手动输入过名称，或者当前名称恰好是之前的默认值，自动同步为所选类型的短名
  if (!isUserManuallyEdited.value || !customVarName.value.trim()) {
    if (opt) {
      customVarName.value = opt.chipName
    } else {
      customVarName.value = val.replace(/^\{+/, '').replace(/\}+$/, '')
    }
  }
}

// 清理后的变量名
const cleanVarName = computed(() => {
  return customVarName.value.replace(/^\{+/, '').replace(/\}+$/, '').trim()
})

// 最终将要生成的 Token 标签（变量模式）
const formattedToken = computed(() => {
  if (!cleanVarName.value) return ''
  return `{${cleanVarName.value}}`
})

// 最终将要生成的 Token 标签（文案库模式）
const currentTxtToken = computed(() => {
  if (!selectedTxtName.value) return ''
  return selectedMode.value === 'random'
    ? `{TXT:${selectedTxtName.value}:random}`
    : `{TXT:${selectedTxtName.value}}`
})

// 显示用的胶囊名称：用户填了用用户的，没填用来源的短名
const displayChipName = computed(() => {
  if (customVarName.value.trim()) return customVarName.value.trim()
  if (activeVarTab.value === 'txt') {
    return selectedTxtName.value.replace(/\.txt$/, '') || '文案库'
  }
  const opt = folderOptions.value.find(o => o.value === selectedVarKey.value)
  return opt?.chipName || '变量'
})

// 是否可以确认
const canConfirm = computed(() => {
  if (activeVarTab.value === 'txt') {
    return !!selectedTxtName.value
  }
  return !!formattedToken.value
})

// 实时示例计算值
const currentPreviewValue = computed(() => {
  if (activeVarTab.value === 'txt') {
    if (!selectedTxtName.value) return ''
    const src = existingTxtSources.value.find(s => s.fileName === selectedTxtName.value)
    return src?.lines[0] || '（空）'
  }

  if (!formattedToken.value) return ''

  // 1. 若下拉框有选中的类型节点，优先根据选中的类型节点展示计算值
  const matchedOpt = folderOptions.value.find(o => o.value === selectedVarKey.value)
  if (matchedOpt) {
    return matchedOpt.sample
  }

  // 2. 尝试直接求值
  const directVal = resolveTemplateString(
    formattedToken.value,
    props.sampleMedia || { fileName: folderHierarchy.value.sampleFileName },
    0,
    props.ruleConfig,
    props.unitLevel
  )
  if (directVal && directVal !== formattedToken.value) {
    return directVal
  }

  return '（空）'
})

// 确认插入
function confirmInsert() {
  const token = activeVarTab.value === 'txt' ? currentTxtToken.value : formattedToken.value
  if (!token) return

  // 注册自定义别名映射 (如果用户起了个性化名称，将其绑定到选中的文件夹层级类型)
  if (selectedVarKey.value && activeVarTab.value !== 'txt') {
    registerCustomVariable(cleanVarName.value, selectedVarKey.value)
  }

  emit('select', token, displayChipName.value)
  dialogVisible.value = false
}

// 监听弹窗打开，初始化默认值（不重置 activeVarTab，保持上次记忆）
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    isUserManuallyEdited.value = false

    // 如果有指定要重新配置的文案文件 → 直接切到导入文本 Tab 并选中它
    if (props.initialTxtName) {
      activeVarTab.value = 'txt'
      selectedTxtName.value = props.initialTxtName
      if (props.initialTxtMode) {
        selectedMode.value = props.initialTxtMode
      }
    } else {
      selectedTxtName.value = ''
      selectedMode.value = 'seq'
    }

    if (props.initialKey) {
      selectedVarKey.value = props.initialKey
      const opt = folderOptions.value.find(o => o.value === props.initialKey)
      if (opt) {
        customVarName.value = opt.chipName
      } else {
        customVarName.value = props.initialKey.replace(/^\{+/, '').replace(/\}+$/, '')
        isUserManuallyEdited.value = true
      }
    } else if (!props.initialTxtName) {
      // 默认选中第一个文件夹层级（只有非 txt 模式才默认选中变量）
      const first = folderOptions.value[0]
      if (first) {
        selectedVarKey.value = first.value
        customVarName.value = first.chipName
      }
    }

    nextTick(() => {
      varNameInputRef.value?.focus()
    })
  }
})
</script>

<style scoped>
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 4px 0 8px 0;
}

.step-title {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 700;
  margin-bottom: 10px;
}
.step-n {
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--primary-color); color: #fff;
  font-size: 10.5px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.var-tabs {
  display: flex; gap: 2px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 12px;
}
.var-tab {
  padding: 7px 13px;
  font-size: 12.5px; font-weight: 600;
  color: var(--text-muted);
  background: none; border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  display: flex; align-items: center; gap: 5px;
  transition: all .15s;
}
.var-tab:hover { color: var(--text-main); }
.var-tab.on { color: var(--primary-color); border-bottom-color: var(--primary-color); }

.var-list { max-height: 240px; overflow-y: auto; }

.var-opt {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px; border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  margin-bottom: 3px;
  transition: all .15s;
}
.var-opt:hover { background: rgba(79,70,229,.055); border-color: rgba(79,70,229,.22); }
.var-opt.on { background: rgba(79,70,229,.09); border-color: var(--primary-color); }

.vo-radio {
  width: 14px; height: 14px; border-radius: 50%;
  border: 1.5px solid var(--border-strong, #c4c8d0);
  flex-shrink: 0; position: relative;
}
.var-opt.on .vo-radio { border-color: var(--primary-color); }
.var-opt.on .vo-radio::after {
  content: ""; position: absolute; inset: 2px;
  border-radius: 50%; background: var(--primary-color);
}

.vo-ic {
  width: 24px; height: 24px; border-radius: 6px;
  background: rgba(79,70,229,.10);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; flex-shrink: 0;
}
.vo-new .vo-ic { background: rgba(128,128,128,.10); }

.vo-meta { min-width: 0; flex: 1; }
.vo-name { font-size: 12.5px; font-weight: 600; color: var(--text-main); }
.vo-sub { font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }

.vo-val {
  margin-left: auto;
  font-family: ui-monospace, monospace;
  font-size: 11.5px;
  color: var(--primary-color);
  background: rgba(79,70,229,.08);
  padding: 2px 8px; border-radius: 5px;
  white-space: nowrap; max-width: 140px;
  overflow: hidden; text-overflow: ellipsis;
}

.var-empty {
  padding: 22px 12px; text-align: center;
  font-size: 11.5px; color: var(--text-muted);
}

/* 列表与动作项之间的分隔线 */
.vo-sep {
  height: 1px;
  background: var(--border-subtle);
  margin: 6px 2px;
}

/* 文案文件行的删除按钮 */
.vo-del {
  margin-left: 6px;
  flex-shrink: 0;
  width: 22px; height: 22px;
  border: none; background: transparent;
  border-radius: 5px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: all .15s;
}
.var-opt:hover .vo-del { opacity: 1; }
.vo-del:hover {
  background: rgba(239, 68, 68, .12);
  color: #ef4444;
}

/* 主操作项：选择文件导入（主色高亮） */
.var-opt.vo-primary {
  border-color: rgba(79, 70, 229, .28);
  background: rgba(79, 70, 229, .045);
}
.var-opt.vo-primary:hover {
  border-color: var(--primary-color);
  background: rgba(79, 70, 229, .09);
}
.var-opt.vo-primary .vo-ic {
  background: rgba(79, 70, 229, .16);
}
.var-opt.vo-primary .vo-name {
  color: var(--primary-color);
}

.name-hint {
  font-size: 11px; color: var(--text-muted);
  margin-top: 5px; padding-left: 2px;
}

.txt-mode-row {
  display: flex; align-items: center; gap: 10px;
  margin-top: 12px; flex-wrap: wrap;
  padding: 9px 11px;
  background: rgba(0,0,0,.02);
  border-radius: 8px;
}
.tm-label { font-size: 11.5px; color: var(--text-muted); white-space: nowrap; }
.tm-seg { display: flex; gap: 3px; background: rgba(0,0,0,.05); padding: 2px; border-radius: 6px; }
.tm-seg button {
  padding: 4px 11px; font-size: 11.5px; font-weight: 600;
  border: none; background: transparent; border-radius: 4px;
  color: var(--text-muted); cursor: pointer;
}
.tm-seg button.on { background: var(--card, #fff); color: var(--primary-color); box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.tm-hint { font-size: 11px; color: var(--text-muted); }

/* 实时预览卡片 */
.preview-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  margin-top: 12px;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.preview-label {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  flex-shrink: 0;
}

.token-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-weight: 600;
  color: #4f46e5;
  background: #eef2ff;
  padding: 2px 7px;
  border-radius: 5px;
  border: 1px solid #e0e7ff;
  white-space: nowrap;
  flex-shrink: 0;
}

.preview-value {
  font-size: 12px;
  font-weight: 600;
  color: #059669;
  max-width: 170px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.variable-input {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
