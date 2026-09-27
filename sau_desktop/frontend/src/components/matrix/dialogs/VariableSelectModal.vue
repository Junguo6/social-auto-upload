<template>
  <el-dialog
    v-model="dialogVisible"
    title="插入动态变量"
    width="760px"
    destroy-on-close
    append-to-body
    class="variable-select-modal"
  >
    <div class="modal-two-columns">
      <!-- 左栏：文件树层级视图 (真正的树状缩进 + 导轨分支结构) -->
      <div class="column-left tree-panel">
        <div class="panel-header">
          <span class="panel-title">
            <el-icon><FolderOpened /></el-icon>
            <span>文件夹层级结构</span>
          </span>
          <span class="panel-subtitle">点击文件夹节点选用对应层级</span>
        </div>

        <div class="tree-canvas custom-scrollbar">
          <div class="tree-container">
            <!-- 树节点列表：真正的层级缩进与树状连线 -->
            <div
              v-for="(node, index) in folderHierarchy.nodes"
              :key="node.varKey"
              class="tree-branch"
              :style="{ paddingLeft: `${index * 26}px` }"
            >
              <!-- 树形引导线 -->
              <div v-if="index > 0" class="branch-connector">
                <span class="corner-line"></span>
              </div>

              <!-- 节点交互卡片 -->
              <div
                class="tree-node-card"
                :class="{ 'is-selected': isNodeSelected(node) }"
                @click="selectFolderNode(node)"
                @dblclick="confirmInsert"
              >
                <div class="node-icon folder-icon">
                  <el-icon><Folder /></el-icon>
                </div>

                <div class="node-content">
                  <div class="node-main-row">
                    <span class="folder-name" :title="node.folderName">{{ node.folderName }}</span>
                    <!-- 紧凑单行徽章 -->
                    <span v-if="node.isDirectParent" class="node-pill is-parent">视频所在目录</span>
                    <span v-else-if="node.isRoot" class="node-pill is-root">外层根目录</span>
                    <span v-else class="node-pill">第{{ node.level }}层</span>
                  </div>
                </div>

                <div class="node-actions">
                  <span class="var-tag">{{ node.varKey }}</span>
                  <div class="check-dot">
                    <el-icon v-if="isNodeSelected(node)"><Check /></el-icon>
                  </div>
                </div>
              </div>
            </div>

            <!-- 最后一环：挂在最内层目录下的视频文件本身 -->
            <div
              class="tree-branch is-leaf"
              :style="{ paddingLeft: `${folderHierarchy.nodes.length * 26}px` }"
            >
              <div class="branch-connector">
                <span class="corner-line"></span>
              </div>
              <div
                class="tree-node-card is-video-leaf"
                :class="{ 'is-selected': selectedKey === '{视频名}' }"
                @click="selectedKey = '{视频名}'"
                @dblclick="confirmInsert"
              >
                <div class="node-icon video-icon">
                  <el-icon><VideoCamera /></el-icon>
                </div>
                <div class="node-content">
                  <div class="node-main-row">
                    <span class="folder-name" :title="folderHierarchy.sampleFileName">
                      {{ folderHierarchy.sampleFileName }}
                    </span>
                    <span class="node-pill is-file">当前素材</span>
                  </div>
                </div>
                <div class="node-actions">
                  <span class="var-tag">{视频名}</span>
                  <div class="check-dot">
                    <el-icon v-if="selectedKey === '{视频名}'"><Check /></el-icon>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 别名切换栏 (如果该目录既是第N层又是上级目录) -->
        <div v-if="currentFolderNode && currentFolderNode.aliasKeys.length > 0" class="alias-bar">
          <span class="alias-title">亦可作为别名插入:</span>
          <div class="alias-group">
            <span
              v-for="alias in currentFolderNode.aliasKeys"
              :key="alias"
              class="alias-btn"
              :class="{ active: selectedKey === alias }"
              @click="selectedKey = alias"
            >
              {{ alias }}
            </span>
          </div>
        </div>
      </div>

      <!-- 右栏：通用变量卡片 & 实时替换预览 (一屏全览，无需翻页) -->
      <div class="column-right basic-panel">
        <div class="panel-header">
          <span class="panel-title">
            <el-icon><Tickets /></el-icon>
            <span>常用基础变量</span>
          </span>
          <span class="panel-subtitle">自动根据视频信息计算</span>
        </div>

        <!-- 常用变量平整列表 (防御性单行卡片) -->
        <div class="basic-vars-list custom-scrollbar">
          <div
            v-for="item in basicVars"
            :key="item.key"
            class="basic-item-card"
            :class="{ 'is-selected': selectedKey === item.key }"
            @click="selectedKey = item.key"
            @dblclick="confirmInsert"
          >
            <div class="item-left">
              <span class="item-key">{{ item.key }}</span>
              <span class="item-label">{{ item.label }}</span>
            </div>
            <div class="item-right">
              <span class="item-sample" :title="item.sampleVal">{{ item.sampleVal || '（无）' }}</span>
              <div class="check-dot">
                <el-icon v-if="selectedKey === item.key"><Check /></el-icon>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部已选效果卡片 -->
        <div class="selection-card">
          <div class="selection-row">
            <span class="sel-label">待插入:</span>
            <span class="sel-token">{{ selectedKey || '请选择' }}</span>
          </div>
          <div class="selection-row preview-row">
            <span class="sel-label">当前计算值:</span>
            <span class="sel-preview" :title="currentPreviewValue">{{ currentPreviewValue || '（空）' }}</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedKey" @click="confirmInsert">
          确认插入此变量
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Folder,
  FolderOpened,
  VideoCamera,
  Tickets,
  Check
} from '@element-plus/icons-vue'
import {
  parseFolderHierarchy,
  buildDynamicVariables,
  resolveTemplateString,
  type ParsedFolderNode,
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

const selectedKey = ref<string>('{第1层目录}')

// 解析示例媒体的各级目录树
const folderHierarchy = computed(() => {
  return parseFolderHierarchy(props.sampleMedia)
})

// 通用基础变量清单
const basicVars = computed(() => {
  const all = buildDynamicVariables(props.sampleMedia, props.unitLevel, props.ruleConfig)
  return all.filter(v => !v.isLevel)
})

// 当前选中的文件夹节点（如果有）
const currentFolderNode = computed<ParsedFolderNode | undefined>(() => {
  return folderHierarchy.value.nodes.find(
    n => n.varKey === selectedKey.value || n.aliasKeys.includes(selectedKey.value)
  )
})

function isNodeSelected(node: ParsedFolderNode): boolean {
  return selectedKey.value === node.varKey || node.aliasKeys.includes(selectedKey.value)
}

// 实时示例计算
const currentPreviewValue = computed(() => {
  if (!selectedKey.value) return ''
  return resolveTemplateString(
    selectedKey.value,
    props.sampleMedia || { fileName: folderHierarchy.value.sampleFileName },
    0,
    props.ruleConfig,
    props.unitLevel
  )
})

// 选择文件夹节点
function selectFolderNode(node: ParsedFolderNode) {
  selectedKey.value = node.varKey
}

// 确认插入
function confirmInsert() {
  if (!selectedKey.value) return
  emit('select', selectedKey.value)
  dialogVisible.value = false
}

// 监听弹窗打开，初始化默认高亮
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    if (props.initialKey) {
      selectedKey.value = props.initialKey
    } else {
      // 默认选中直属目录或第一层
      const direct = folderHierarchy.value.nodes.find(n => n.isDirectParent)
      selectedKey.value = direct ? direct.varKey : '{第1层目录}'
    }
  }
})
</script>

<style scoped>
.modal-two-columns {
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 16px;
  min-height: 380px;
}

/* 列通用标题 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.panel-subtitle {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

/* ── 左栏：真正的树状结构 ── */
.tree-panel {
  display: flex;
  flex-direction: column;
}

.tree-canvas {
  flex: 1;
  max-height: 340px;
  overflow-y: auto;
  padding: 8px 10px 8px 4px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.tree-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tree-branch {
  position: relative;
  transition: all 0.2s;
}

/* 树分支连接导线 */
.branch-connector {
  position: absolute;
  top: -12px;
  left: 0;
  width: 18px;
  height: 24px;
  pointer-events: none;
}

.corner-line {
  position: absolute;
  bottom: 0;
  left: -8px;
  width: 14px;
  height: 18px;
  border-left: 1.5px dashed var(--el-border-color);
  border-bottom: 1.5px dashed var(--el-border-color);
  border-bottom-left-radius: 6px;
}

/* 树节点交互卡片 */
.tree-node-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1.5px solid var(--el-border-color-lighter);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 0;
}

.tree-node-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.tree-node-card.is-selected {
  border-color: var(--el-color-primary);
  background: #ecf5ff;
}

.node-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.folder-icon {
  background: #fff7e6;
  color: #fa8c16;
}

.video-icon {
  background: #e6f7ff;
  color: #1890ff;
}

.node-content {
  flex: 1;
  min-width: 0;
}

.node-main-row {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
}

.folder-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-pill {
  font-size: 10px;
  line-height: 16px;
  padding: 0 5px;
  border-radius: 4px;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.node-pill.is-parent {
  background: #e6f7ff;
  color: #1890ff;
  font-weight: 500;
}

.node-pill.is-root {
  background: #f6ffed;
  color: #52c41a;
}

.node-pill.is-file {
  background: #f9f0ff;
  color: #722ed1;
}

.node-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.var-tag {
  font-family: monospace;
  font-size: 11px;
  font-weight: 600;
  background: rgba(64, 158, 255, 0.1);
  color: var(--el-color-primary);
  padding: 2px 6px;
  border-radius: 4px;
}

.check-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #ffffff;
  transition: all 0.15s;
}

.tree-node-card.is-selected .check-dot,
.basic-item-card.is-selected .check-dot {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
}

/* 别名条 */
.alias-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 11.5px;
}

.alias-title {
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.alias-group {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.alias-btn {
  padding: 1px 8px;
  background: #ffffff;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  transition: all 0.15s;
}

.alias-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.alias-btn.active {
  background: var(--el-color-primary);
  color: #ffffff;
  border-color: var(--el-color-primary);
}

/* ── 右栏：基础变量与实时预览 ── */
.basic-panel {
  display: flex;
  flex-direction: column;
}

.basic-vars-list {
  flex: 1;
  max-height: 250px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.basic-item-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  background: #ffffff;
  border: 1.5px solid var(--el-border-color-lighter);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.basic-item-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.basic-item-card.is-selected {
  border-color: var(--el-color-primary);
  background: #ecf5ff;
}

.item-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.item-key {
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: rgba(64, 158, 255, 0.08);
  padding: 1px 5px;
  border-radius: 4px;
}

.item-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.item-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-sample {
  font-size: 11.5px;
  color: var(--el-color-success);
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 底部已选效果卡片 */
.selection-card {
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px dashed var(--el-border-color);
}

.selection-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.sel-label {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.sel-token {
  font-family: monospace;
  font-weight: 600;
  color: var(--el-color-primary);
}

.preview-row .sel-preview {
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}
</style>
