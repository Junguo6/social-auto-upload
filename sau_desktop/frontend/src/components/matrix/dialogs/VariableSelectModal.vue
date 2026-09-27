<template>
  <el-dialog
    v-model="dialogVisible"
    title="插入动态变量"
    width="480px"
    destroy-on-close
    append-to-body
    class="variable-select-modal"
  >
    <div class="modal-form">
      <!-- 1. 先设置变量名称 -->
      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label">
            <el-icon><EditPen /></el-icon>
            <span>变量名称</span>
          </label>
          <span class="form-hint">将以 {变量名} 形式插入至文本中</span>
        </div>
        <el-input
          ref="varNameInputRef"
          v-model="customVarName"
          placeholder="输入变量名称，如：剧集目录 或 第1层目录"
          size="large"
          clearable
          class="variable-input"
          @input="onVarNameManualInput"
          @keyup.enter="confirmInsert"
        >
          <template #prefix>
            <span class="brace-affix">{</span>
          </template>
          <template #suffix>
            <span class="brace-affix">}</span>
          </template>
        </el-input>
      </div>

      <!-- 2. 再选择变量类型 (文件夹层级结构) -->
      <div class="form-group">
        <label class="form-label">
          <el-icon><FolderOpened /></el-icon>
          <span>选择变量类型（文件夹层级结构）</span>
        </label>
        <el-select
          v-model="selectedVarKey"
          placeholder="请选择对应绑定的层级类型"
          class="variable-select"
          size="large"
          @change="handleSelectChange"
        >
          <el-option
            v-for="opt in folderOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <div class="opt-row">
              <div class="opt-left">
                <el-icon class="opt-icon"><Folder /></el-icon>
                <span class="opt-title">{{ opt.title }}</span>
                <span v-if="opt.badge" class="opt-badge" :class="opt.badgeClass">{{ opt.badge }}</span>
              </div>
              <span class="opt-sample" :title="opt.sample">{{ opt.sample }}</span>
            </div>
          </el-option>
        </el-select>
      </div>

      <!-- 3. 极简实时计算预览卡片 -->
      <div class="preview-card">
        <div class="preview-item">
          <span class="preview-label">待插入标签</span>
          <span class="token-code">{{ formattedToken || '—' }}</span>
        </div>
        <div class="preview-divider"></div>
        <div class="preview-item">
          <span class="preview-label">当前计算值</span>
          <span class="preview-value" :title="currentPreviewValue">
            {{ currentPreviewValue || '（空）' }}
          </span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!formattedToken" @click="confirmInsert">
          确定插入
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  Folder,
  FolderOpened,
  EditPen
} from '@element-plus/icons-vue'
import {
  parseFolderHierarchy,
  resolveTemplateString,
  registerCustomVariable,
  type BatchRuleConfig
} from '../../../utils/matrixHelper'

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
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  unitLevel: 1,
  initialKey: ''
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'select', varKey: string): void
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

// 下拉框选项：文件夹层级结构 + 视频素材
const folderOptions = computed(() => {
  const list: Array<{
    value: string
    label: string
    title: string
    badge?: string
    badgeClass?: string
    sample: string
    defaultName: string
  }> = []

  folderHierarchy.value.nodes.forEach(node => {
    let badge = `第${node.level}层`
    let badgeClass = ''
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
      title: `第 ${node.level} 层目录`,
      badge,
      badgeClass,
      sample: node.folderName,
      defaultName: `第${node.level}层目录`
    })
  })

  // 加上当前素材视频名
  list.push({
    value: '{视频名}',
    label: `{视频名} (${folderHierarchy.value.sampleFileName})`,
    title: '视频文件名',
    badge: '当前素材',
    badgeClass: 'is-file',
    sample: folderHierarchy.value.sampleFileName,
    defaultName: '视频名'
  })

  return list
})

// 1. 变量名称
const customVarName = ref<string>('第1层目录')
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
  // 如果用户未手动输入过名称，或者当前名称恰好是之前的默认值，自动同步为所选类型的默认名称
  if (!isUserManuallyEdited.value || !customVarName.value.trim()) {
    if (opt) {
      customVarName.value = opt.defaultName
    } else {
      customVarName.value = val.replace(/^\{+/, '').replace(/\}+$/, '')
    }
  }
}

// 清理后的变量名
const cleanVarName = computed(() => {
  return customVarName.value.replace(/^\{+/, '').replace(/\}+$/, '').trim()
})

// 最终将要生成的 Token 标签
const formattedToken = computed(() => {
  if (!cleanVarName.value) return ''
  return `{${cleanVarName.value}}`
})

// 实时示例计算值
const currentPreviewValue = computed(() => {
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
  if (!formattedToken.value) return

  // 注册自定义别名映射 (如果用户起了个性化名称，将其绑定到选中的文件夹层级类型)
  if (selectedVarKey.value) {
    registerCustomVariable(cleanVarName.value, selectedVarKey.value)
  }

  emit('select', formattedToken.value)
  dialogVisible.value = false
}

// 监听弹窗打开，初始化默认值
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    isUserManuallyEdited.value = false
    if (props.initialKey) {
      selectedVarKey.value = props.initialKey
      const opt = folderOptions.value.find(o => o.value === props.initialKey)
      if (opt) {
        customVarName.value = opt.defaultName
      } else {
        customVarName.value = props.initialKey.replace(/^\{+/, '').replace(/\}+$/, '')
        isUserManuallyEdited.value = true
      }
    } else {
      // 默认选中第一个文件夹层级
      const first = folderOptions.value[0]
      if (first) {
        selectedVarKey.value = first.value
        customVarName.value = first.defaultName
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
  gap: 18px;
  padding: 4px 0 8px 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.form-label .el-icon {
  font-size: 15px;
  color: #4f46e5;
}

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-hint {
  font-size: 11px;
  color: #94a3b8;
}

.variable-select,
.variable-input {
  width: 100%;
}

.brace-affix {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 15px;
  font-weight: 700;
  color: #4f46e5;
  padding: 0 2px;
}

/* 下拉选项行 */
.opt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}

.opt-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.opt-icon {
  font-size: 14px;
  color: #6366f1;
}

.opt-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.opt-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
}

.opt-badge.is-root {
  background: #ede9fe;
  color: #6d28d9;
}

.opt-badge.is-parent {
  background: #ecfdf5;
  color: #047857;
}

.opt-badge.is-file {
  background: #eff6ff;
  color: #1d4ed8;
}

.opt-sample {
  font-size: 12px;
  color: #64748b;
  max-width: 170px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 实时预览卡片 (防御性单行双向布局) */
.preview-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  margin-top: 4px;
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

.preview-divider {
  width: 1px;
  height: 20px;
  background: #e2e8f0;
  margin: 0 12px;
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
