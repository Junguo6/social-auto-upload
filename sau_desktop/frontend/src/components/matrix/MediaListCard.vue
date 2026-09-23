<template>
  <div
    class="media-list-card glass-card"
    :class="{ 'drag-over': isDragOver }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div class="card-header">
      <div class="card-title-box">
        <div class="title-text-group">
          <div class="main-title">
            <span>要发哪些视频 / 素材</span>
            <span class="req-star">*</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 拖入提示（空状态时更醒目） -->
    <div v-if="mediaList.length === 0" class="drop-zone-hint">
      <div class="drop-hint-inner" @click="handleSelectFolder" @dragover.prevent @drop.prevent="onDrop">
        <div class="drop-icon-wrap">
          <el-icon class="drop-icon"><UploadFilled /></el-icon>
          <div class="drop-arrow">
            <span class="drop-arrow-text">点击选择文件夹</span>
            <span class="drop-sep">·</span>
            <span class="drop-arrow-text">自动递归导入所有视频</span>
          </div>
        </div>
        <div class="drop-sub-tip">
          也可直接拖入文件夹或多个视频文件到本卡片
        </div>
      </div>
    </div>

    <!-- 搜索与快捷操作条 -->
    <div class="media-toolbar" v-if="mediaList.length > 0">
      <span class="badge-count">已添加 {{ mediaList.length }} 个</span>
      <span v-if="hasMultiFolder" class="badge-folder">
        <span class="ic"><FolderIcon :size="13" /></span> 多层目录
      </span>
      <!-- 以第几层为分配单位（素材有多层时才显示） -->
      <span v-if="maxFolderDepth >= 1" class="badge-folder">
        以
        <span class="level-inline">
          <select
            :value="unitLevel"
            class="level-select"
            title="账号按这一层的文件夹顺序分配；改这里会影响对应表的分组与分配"
            @change="e => emit('update:unitLevel', Number((e.target as HTMLSelectElement).value))"
          >
            <option v-for="n in maxFolderDepth" :key="n" :value="n">第{{ n }}层</option>
          </select>
        </span>
        为单位
      </span>
      <div class="quick-batch-ops">
        <el-tooltip content="清空已添加的全部视频" placement="top">
          <el-button size="small" link type="danger" @click="handleClearAll">
            <el-icon><Delete /></el-icon> 清空
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 面包屑（仅当存在子文件夹或已进入子层时显示） -->
    <div
      v-if="mediaList.length > 0 && (browsePath.length > 0 || hasSubFolders)"
      class="crumb-bar"
    >
      <!-- 返回上一级（仅在已进入子文件夹时显示） -->
      <button v-if="browsePath.length > 0" class="crumb-back" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回</span>
      </button>
      <span
        class="crumb-item"
        :class="{ cur: browsePath.length === 0 }"
        @click="jumpTo(0)"
      >全部</span>
      <template v-for="(seg, i) in browsePath" :key="i">
        <span class="crumb-sep">/</span>
        <span
          class="crumb-item"
          :class="{ cur: i === browsePath.length - 1 }"
          @click="jumpTo(i + 1)"
        >{{ seg }}</span>
      </template>
      <span class="crumb-count">本层 {{ browseEntries.videos.length }} 个视频</span>
    </div>

    <!-- 视频清单列表（按层级拆分：文件夹行 + 视频行） -->
    <div v-if="mediaList.length > 0" class="video-list custom-scrollbar">
      <!-- 文件夹行：点击进入 -->
      <div
        v-for="f in browseEntries.folders"
        :key="'folder:' + browsePath.join('/') + '/' + f.name"
        class="folder-row-item"
        :title="`点击进入「${f.name}」`"
        @click="enterFolder(f.name)"
      >
        <div class="folder-icon"><FolderIcon :size="24" /></div>
        <div class="folder-info">
          <div class="folder-name">
            {{ f.name }}
            <span class="level-tag" :class="{ 'is-unit': f.level === unitLevel }">第{{ f.level }}层</span>
          </div>
          <div class="folder-count">{{ f.count }} 个视频</div>
        </div>
        <el-icon class="folder-enter"><ArrowRight /></el-icon>
      </div>

      <!-- 视频行 -->
      <div
        v-for="item in browseEntries.videos"
        :key="item.id"
        class="video-card-item"
      >
        <!-- 视频缩略图（点击播放预览） -->
        <div class="video-thumb" @click.stop="openPreview(item)">
          <img v-if="item.thumbnail" :src="item.thumbnail" class="thumb-img" :alt="item.fileName" />
          <el-icon v-else class="thumb-icon"><Film /></el-icon>
          <span class="format-badge">{{ item.format || 'MP4' }}</span>
          <span v-if="item.duration" class="duration-badge">{{ item.duration }}</span>
        </div>

        <!-- 视频基础信息 -->
        <div class="video-info">
          <div class="video-name" :title="item.fileName">
            <span class="video-idx">#{{ globalIndex(item.id) }}</span>
            <span class="name-text">{{ item.fileName }}</span>
          </div>
          <!-- 父文件夹路径（只显示最外层） -->
          <div v-if="item.folderCrumbs && item.folderCrumbs.length > 0" class="folder-crumbs">
            <span class="crumb">
              <span class="crumb-ic"><FolderIcon :size="13" /></span>
              <span class="crumb-name">{{ item.folderCrumbs[0] }}</span>
            </span>
          </div>
          <div class="video-meta">
            <el-popover placement="top" :width="180" trigger="click">
              <template #reference>
                <span class="meta-item clickable-ep-badge" @click.stop title="点击微调该视频集数">
                  <el-icon><EditPen /></el-icon>
                  <span>第 {{ item.parsedEpisode ?? globalIndex(item.id) }} 集</span>
                </span>
              </template>
              <div class="ep-edit-popover" @click.stop>
                <div class="popover-tip">设定该视频指定集数:</div>
                <el-input-number
                  v-model="item.parsedEpisode"
                  :min="1"
                  :max="9999"
                  size="small"
                  controls-position="right"
                  @change="handleEpisodeUpdated"
                />
              </div>
            </el-popover>

            <span class="meta-item" v-if="item.fileSize">{{ item.fileSize }}</span>
            <span class="meta-path" :title="item.filePath">{{ item.filePath }}</span>
          </div>
        </div>

        <!-- 单项操作 -->
        <div class="row-actions" @click.stop>
          <el-tooltip content="从清单中移除该视频" placement="top">
            <el-button
              type="danger"
              link
              size="small"
              class="del-btn"
              @click="removeMedia(item.id)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <!-- 追加导入提示（列表非空时显示，兼作点击选择文件夹的兜底入口） -->
    <div v-if="mediaList.length > 0" class="drop-more-hint" @click="handleSelectFolder">
      <el-icon><UploadFilled /></el-icon>
      <span>🔒 已导入 {{ mediaList.length }} 个视频 · 可继续追加「同结构」的素材（也可点击此处选择文件夹）</span>
    </div>

    <!-- 拖入覆盖层（拖动中时显示） -->
    <div v-if="isDragOver" class="drag-overlay">
      <div class="drag-overlay-inner">
        <el-icon class="drag-overlay-icon"><UploadFilled /></el-icon>
        <span class="drag-overlay-text">释放以导入视频 / 文件夹</span>
      </div>
    </div>

    <!-- 视频预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewItem?.fileName"
      width="72%"
      append-to-body
      destroy-on-close
    >
      <video
        v-if="previewSrc"
        :src="previewSrc"
        controls
        autoplay
        style="width: 100%; border-radius: 6px; background: #000"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import FolderIcon from '../common/FolderIcon.vue'
import { ElMessage } from 'element-plus'
import { SelectLocalFolder } from '../../../wailsjs/go/main/App'
import { EventsOn, EventsOff } from '../../../wailsjs/runtime/runtime'
import type { MediaItem } from '../../types/matrix'

const props = defineProps<{
  mediaList: MediaItem[]
  selectedMediaIds: string[]
  unitLevel: number
}>()

const emit = defineEmits<{
  (e: 'update:mediaList', list: MediaItem[]): void
  (e: 'update:selectedMediaIds', ids: string[]): void
  (e: 'update:unitLevel', v: number): void
  (e: 'add-media', items: MediaItem[]): void
}>()

const isDragOver = ref(false)
const VIDEO_EXTS = new Set(['mp4', 'mov', 'mkv', 'flv', 'avi', 'webm', 'wmv', 'm4v', '3gp', 'mpeg', 'mpg', 'ts'])

// ============ 视频预览弹窗 ============
const previewVisible = ref(false)
const previewItem = ref<MediaItem | null>(null)
const previewSrc = computed(() => (previewItem.value ? toPreviewUrl(previewItem.value.filePath) : ''))

function openPreview(item: MediaItem) {
  previewItem.value = item
  previewVisible.value = true
}

// ============ 原生拖拽监听（Wails v2.10+）============
// 拖入窗口的文件/文件夹由 Go 侧解析两层结构，通过 "media:file-drop" 事件推送过来
onMounted(() => {
  EventsOn('media:file-drop', (payload: any) => {
    if (!payload) return

    // 结构一致性校验（允许追加同结构素材）
    const incomingItems = [
      ...(payload.folders || []).flatMap((f: any) => f.items || []),
      ...(payload.files || [])
    ].map((it: any) => ({ folders: it.folders || [] }))

    const mismatch = checkStructureMatch(incomingItems)
    if (mismatch) {
      ElMessage.warning(mismatch)
      return
    }

    const genId = () => `media_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    const newItems: MediaItem[] = []

    // 拖入的文件夹（后端已解析两层结构）
    ;(payload.folders || []).forEach((folder: any) => {
      ;(folder.items || []).forEach((it: any) => {
        newItems.push({
          id: genId(),
          filePath: it.filePath,
          fileName: it.fileName,
          format: it.fileName.includes('.') ? it.fileName.split('.').pop()?.toUpperCase() : 'MP4',
          fileSize: it.fileSizeText,
          parsedEpisode: it.episode || parseEpisodeFromFileName(it.fileName) || undefined,
          // 优先用后端返回的完整层级（含三层及以上），旧版只有两层时降级到 parentFolder + childFolder
          folderCrumbs: it.folders || [it.parentFolder, it.childFolder].filter(Boolean)
        })
      })
    })

    // 拖入的散装视频文件
    ;(payload.files || []).forEach((it: any) => {
      newItems.push({
        id: genId(),
        filePath: it.filePath,
        fileName: it.fileName,
        format: it.fileName.includes('.') ? it.fileName.split('.').pop()?.toUpperCase() : 'MP4',
        fileSize: it.fileSizeText,
        parsedEpisode: it.episode || parseEpisodeFromFileName(it.fileName) || undefined,
        folderCrumbs: it.folders || []
      })
    })

    // 结构不合规（如层级混合）→ 整批拒收，不导入任何内容
    const invalidFolders = (payload.folders || []).filter((f: any) => !f.valid)
    if (invalidFolders.length > 0) {
      ElMessage.error(invalidFolders[0].message || '素材文件夹结构不符合要求，请调整后重试')
      return
    }

    if (newItems.length === 0) {
      ElMessage.warning(payload.message || '未识别到视频文件')
      return
    }

    const merged = [...props.mediaList, ...newItems]
    // 首次导入时按「以第几层为单位」自动定位预览列表
    if (props.mediaList.length === 0 && newItems.length > 0) {
      const roots = Array.from(
        new Set(newItems.map((i) => (i.folderCrumbs || [])[0]).filter(Boolean) as string[])
      )
      const lv = props.unitLevel
      if (roots.length === 1 && lv >= 2) {
        if (lv === 2) {
          browsePath.value = [roots[0]]
        } else {
          const sample = (newItems.find((i) => (i.folderCrumbs || [])[0] === roots[0])?.folderCrumbs || []) as string[]
          browsePath.value = sample.slice(0, Math.min(lv - 1, sample.length))
        }
      } else {
        browsePath.value = []
      }
    }
    emit('update:mediaList', merged)
    emit('update:selectedMediaIds', Array.from(new Set([...props.selectedMediaIds, ...newItems.map(i => i.id)])))

    // 异步补全缩略图（不阻塞导入，逐个出现）
    void hydrateMediaMeta(newItems)
    ElMessage.success(payload.message || `已导入 ${newItems.length} 个视频`)
  })
})

onUnmounted(() => {
  EventsOff('media:file-drop')
})

// ============ 多层路径解析 ============
// 从 filePath 提取文件夹层级 crumbs
function extractFolderCrumbs(filePath: string): string[] {
  const normalized = (filePath || '').replace(/\\/g, '/')
  const parts = normalized.split('/').filter(Boolean)
  // 去掉最后一个文件本身，前面的全是文件夹层级
  parts.pop()
  return parts
}

const hasMultiFolder = computed(() => {
  if (props.mediaList.length <= 1) return false
  const crumbs = new Set(props.mediaList.map(m => JSON.stringify(m.folderCrumbs || [])))
  return crumbs.size > 1
})

/** 素材里实际存在的最深层级（决定「以第几层为单位」的可选项） */
const maxFolderDepth = computed(() =>
  props.mediaList.reduce((mx, m) => Math.max(mx, (m.folderCrumbs || []).length), 0)
)

// 素材层级不足当前设定时自动回退（不超过实际最大值，默认不高于第 2 层）
watch(maxFolderDepth, (depth) => {
  if (depth > 0 && props.unitLevel > depth) {
    emit('update:unitLevel', Math.min(2, depth))
  }
}, { immediate: true })

/** 素材的目录层数：0 = 平铺视频，1 = 一层文件夹，2 = 两层… */
function maxDepthOf(list: Array<{ folderCrumbs?: string[]; folders?: string[] }>): number {
  return list.reduce((mx, m) => {
    const c = m.folderCrumbs || m.folders || []
    return Math.max(mx, c.length)
  }, 0)
}

/**
 * 校验新素材与现有素材结构是否一致。
 * 一致 → 返回 null（允许追加）；不一致 → 返回提示文案。
 * 目的：避免「10 个文件夹的结构」和「平铺视频」混在一起，导致层级/分组错乱。
 */
function checkStructureMatch(incoming: Array<{ folders?: string[] }>): string | null {
  if (props.mediaList.length === 0) return null // 首次导入，不校验
  if (incoming.length === 0) return null

  const existingDepth = maxDepthOf(props.mediaList)
  const incomingDepth = maxDepthOf(incoming)

  if (existingDepth !== incomingDepth) {
    const describe = (d: number) => (d === 0 ? '平铺视频（无文件夹）' : `${d} 层文件夹`)
    return `素材结构不一致：已有的是「${describe(existingDepth)}」，新拖入的是「${describe(incomingDepth)}」。请先清空，再统一上传同结构的素材。`
  }
  return null
}

// ============ 预览区逐层浏览 ============
// browsePath 表示当前所在层级（相对扫描根目录的目录名序列），[] = 根
const browsePath = ref<string[]>([])

/**
 * 把「以第 N 层为单位」换算成预览列表要显示的路径：
 * 显示第 N 层 = browsePath 停在前 N-1 层
 * · N=1 → []（根层）
 * · N=2 → [第一层名]
 * · N>=3 → 取某个视频的前 N-1 段目录
 * 若素材有多个根（第一层不唯一），无法确定唯一路径，回退到根层。
 */
function pathForUnitLevel(level: number): string[] {
  const all = props.mediaList
  if (level <= 1 || all.length === 0) return []

  const roots = Array.from(
    new Set(all.map((m) => (m.folderCrumbs || [])[0]).filter(Boolean) as string[])
  )
  if (roots.length !== 1) return []

  if (level === 2) return [roots[0]]

  const sample = all.find((m) => (m.folderCrumbs || [])[0] === roots[0])?.folderCrumbs || []
  return sample.slice(0, Math.min(level - 1, sample.length))
}

// 用户切换「以第几层为单位」时，预览列表同步跳到该层，
// 让用户当场确认"这一层具体是哪些文件夹"
watch(
  () => props.unitLevel,
  (lv) => {
    browsePath.value = pathForUnitLevel(lv)
  }
)

/** 当前层级下的文件夹（含视频数）与视频（已应用搜索过滤） */
const browseEntries = computed(() => {
  const folders = new Map<string, { name: string; count: number; level: number }>()
  const videos: MediaItem[] = []
  const cur = browsePath.value

  props.mediaList.forEach((m) => {
    const crumbs = m.folderCrumbs || []

    // 必须落在当前路径下（crumbs 前缀必须匹配 browsePath）
    for (let i = 0; i < cur.length; i++) {
      if (crumbs[i] !== cur[i]) return
    }

    // 视频正好在当前层（散装视频 crumbs 为空数组，只在根层出现）
    if (crumbs.length === cur.length) {
      videos.push(m)
      return
    }

    // 统计子文件夹内的视频数
    const name = crumbs[cur.length]
    const hit = folders.get(name) || { name, count: 0, level: cur.length + 1 }
    hit.count += 1
    folders.set(name, hit)
  })

  return {
    folders: Array.from(folders.values()).sort((a, b) => a.name.localeCompare(b.name, 'zh')),
    videos
  }
})

const hasSubFolders = computed(() => browseEntries.value.folders.length > 0)

function enterFolder(name: string) {
  browsePath.value = [...browsePath.value, name]
}

/** 返回上一级（根层时无操作） */
function goBack() {
  if (browsePath.value.length === 0) return
  browsePath.value = browsePath.value.slice(0, -1)
}

function jumpTo(depth: number) {
  browsePath.value = browsePath.value.slice(0, depth)
}

/** 全局序号：列表按层级拆分后，序号仍按整体顺序 */
function globalIndex(id: string) {
  return props.mediaList.findIndex((m) => m.id === id) + 1
}

// 媒体列表清空时回根目录；当前路径在新列表里不存在对应文件夹时也回根
watch(
  () => props.mediaList,
  () => {
    if (props.mediaList.length === 0) {
      browsePath.value = []
      return
    }
    const valid = browsePath.value.every((seg, i) =>
      props.mediaList.some((m) => (m.folderCrumbs || [])[i] === seg)
    )
    if (!valid) browsePath.value = []
  },
  { deep: true }
)

// ============ 过滤后的列表（搜索 + 逐层浏览在 browseEntries 中合并处理） ============

import { parseEpisodeFromFileName } from '../../utils/matrixHelper'

// ============ 拖入处理 ============
function onDragOver(e: DragEvent) {
  if (e.dataTransfer?.types.includes('Files')) {
    isDragOver.value = true
  }
}

function onDragLeave(e: DragEvent) {
  // 仅当真正离开卡片时才关闭
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  if (
    e.clientX < rect.left || e.clientX > rect.right ||
    e.clientY < rect.top || e.clientY > rect.bottom
  ) {
    isDragOver.value = false
  }
}

async function onDrop(e: DragEvent) {
  isDragOver.value = false

  // 外部文件/文件夹拖拽：统一交给 Wails 原生拖拽处理（media:file-drop 事件，可拿到绝对路径）
  // 这里直接返回，避免弹出"选择文件夹"降级弹窗 + 重复导入
  if (e.dataTransfer?.types.includes('Files')) {
    return
  }

  const items = Array.from(e.dataTransfer?.items || [])
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length === 0) return

  // 检测是否是文件夹拖入：如果 items 里有 webkitGetAsEntry 且是 directory
  let isFolderDrop = false
  for (const item of items) {
    if (item.kind === 'file') {
      const entry = (item as any).webkitGetAsEntry?.()
      if (entry?.isDirectory) {
        isFolderDrop = true
        break
      }
    }
  }

  const newItems: MediaItem[] = []
  const VIDEO_EXT_RE = /\.(mp4|mov|mkv|flv|avi|webm|wmv|m4v|3gp|mpeg|mpg|ts)$/i

  for (const file of files) {
    // Electron/Wails 环境：File 对象带 .path 属性
    const filePath: string = (file as any).path || ''
    const fileName = file.name

    if (!VIDEO_EXT_RE.test(fileName)) continue

    // 解析文件夹层级：优先 webkitRelativePath，其次 file.path
    let folderCrumbs: string[] = []
    const relPath: string = (file as any).webkitRelativePath || ''
    if (relPath && relPath.includes('/')) {
      folderCrumbs = extractFolderCrumbs(relPath)
    } else if (filePath && filePath.includes('/')) {
      folderCrumbs = extractFolderCrumbs(filePath)
    }

    const ext = fileName.includes('.') ? fileName.split('.').pop()?.toUpperCase() : 'MP4'
    const ep = parseEpisodeFromFileName(fileName) || (props.mediaList.length + newItems.length + 1)

    newItems.push({
      id: `media_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      filePath,
      fileName,
      format: ext,
      parsedEpisode: ep,
      folderCrumbs,
      fileSize: formatFileSize((file as any).size)
    })
  }

  if (newItems.length === 0) {
    if (!isFolderDrop) {
      ElMessage.warning('未识别到有效的视频文件（支持 .mp4 .mov .mkv .avi 等）')
    }
    return
  }

  const merged = [...props.mediaList, ...newItems]
  emit('update:mediaList', merged)
  const newIds = newItems.map(i => i.id)
  emit('update:selectedMediaIds', Array.from(new Set([...props.selectedMediaIds, ...newIds])))
  ElMessage.success(`成功导入 ${newItems.length} 个视频`)
}

// ============ 选择文件夹（递归导入） ============
const handleSelectFolder = async () => {
  try {
    const res = await SelectLocalFolder('选择包含视频的文件夹（会自动递归导入）')
    if (!res) {
      ElMessage.info('未选择文件夹')
      return
    }

    // 结构不合规 → 拒收
    if (res.valid === false) {
      ElMessage.error(res.message || '素材文件夹结构不符合要求，请调整后重试')
      return
    }

    if (!res.items || res.items.length === 0) {
      ElMessage.info('未选择文件夹或文件夹内无视频文件')
      return
    }

    // 结构一致性校验（允许追加同结构素材）
    const mismatch = checkStructureMatch(res.items.map((it: any) => ({ folders: it.folders || [] })))
    if (mismatch) {
      ElMessage.warning(mismatch)
      return
    }

    const newItems: MediaItem[] = res.items.map((it: any, idx: number) => {
      const folderCrumbs = it.folders || []
      const fileName = it.fileName || ''
      const ext = fileName.includes('.') ? fileName.split('.').pop()?.toUpperCase() : 'MP4'
      const ep = it.episode || parseEpisodeFromFileName(fileName) || (props.mediaList.length + idx + 1)
      return {
        id: `media_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        filePath: it.filePath,
        fileName,
        format: ext,
        parsedEpisode: ep,
        folderCrumbs
      }
    })

    const merged = [...props.mediaList, ...newItems]
    // 首次导入时按「以第几层为单位」自动定位预览列表
    if (props.mediaList.length === 0 && newItems.length > 0) {
      const roots = Array.from(
        new Set(newItems.map((i) => (i.folderCrumbs || [])[0]).filter(Boolean) as string[])
      )
      const lv = props.unitLevel
      if (roots.length === 1 && lv >= 2) {
        if (lv === 2) {
          browsePath.value = [roots[0]]
        } else {
          const sample = (newItems.find((i) => (i.folderCrumbs || [])[0] === roots[0])?.folderCrumbs || []) as string[]
          browsePath.value = sample.slice(0, Math.min(lv - 1, sample.length))
        }
      } else {
        browsePath.value = []
      }
    }
    emit('update:mediaList', merged)
    const newIds = newItems.map(i => i.id)
    emit('update:selectedMediaIds', Array.from(new Set([...props.selectedMediaIds, ...newIds])))

    // 异步补全缩略图（不阻塞导入，逐个出现）
    void hydrateMediaMeta(newItems)

    // 提示用户导入的层级信息
    const folderSet = new Set(newItems.map(i => i.folderCrumbs?.slice(0, -1).join('/')).filter(Boolean))
    const folderMsg = folderSet.size > 0 ? `，覆盖 ${folderSet.size} 个文件夹层级` : ''
    ElMessage.success(`成功从文件夹导入 ${newItems.length} 个视频${folderMsg}`)
  } catch (err: any) {
    ElMessage.error(`选择文件夹失败: ${err?.message || err}`)
  }
}

// ============ 工具函数 ============
function formatFileSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)}GB`
}

// ============ 选中操作（由代码自动维护：导入即全选，删除时同步剔除） ============
const handleEpisodeUpdated = () => {
  emit('update:mediaList', [...props.mediaList])
}

// ============ 全选 / 全不选（已移除勾选框，相关逻辑由代码自动维护） ============
const removeMedia = (id: string) => {
  emit('update:mediaList', props.mediaList.filter(m => m.id !== id))
  emit('update:selectedMediaIds', props.selectedMediaIds.filter(i => i !== id))
}

const handleClearAll = () => {
  browsePath.value = []
  emit('update:mediaList', [])
  emit('update:selectedMediaIds', [])
}

// ============ 视频缩略图 & 时长抓取（走后端只读通道） ============
// 构造可供 <video> 播放/抓帧的本地地址（走后端 AssetServer 只读通道）
function toPreviewUrl(filePath: string): string {
  return `/local-media?path=${encodeURIComponent(filePath)}`
}

/**
 * 读取视频时长 + 首帧缩略图
 * 移植自「去字幕」BatchView.loadVideoMeta：<video> 加载 → seek 到中间帧 → canvas 抓帧 → dataURL
 * 差异：Web 端用 URL.createObjectURL(File)，桌面端只有绝对路径，改走后端 /local-media 通道
 */
function loadVideoMeta(mediaUrl: string): Promise<{ duration: string; thumbnail: string }> {
  return new Promise((resolve) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.muted = true
    ;(video as any).playsInline = true

    let settled = false
    const finish = (duration: string, thumbnail: string) => {
      if (settled) return
      settled = true
      video.removeAttribute('src')
      video.load()
      resolve({ duration, thumbnail })
    }

    const fmtDuration = (sec: number) => {
      const total = Math.round(sec)
      const h = Math.floor(total / 3600)
      const m = Math.floor((total % 3600) / 60)
      const s = total % 60
      const pad = (n: number) => String(n).padStart(2, '0')
      return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
    }

    video.onloadedmetadata = () => {
      const dur = Number.isFinite(video.duration) ? video.duration : 0
      const durationText = dur > 0 ? fmtDuration(dur) : ''

      // 跳到中间帧抓图
      video.currentTime = Math.min(1, (dur || 1) / 2)

      video.onseeked = () => {
        try {
          const w = video.videoWidth || 0
          const h = video.videoHeight || 0
          if (!w || !h) {
            finish(durationText, '')
            return
          }
          const tw = 320
          const th = Math.max(1, Math.round((tw * h) / w))
          const canvas = document.createElement('canvas')
          canvas.width = tw
          canvas.height = th
          canvas.getContext('2d')?.drawImage(video, 0, 0, tw, th)
          finish(durationText, canvas.toDataURL('image/jpeg', 0.8))
        } catch {
          finish(durationText, '')
        }
      }

      // 兜底：3 秒内没抓到帧就只返回时长
      setTimeout(() => finish(durationText, ''), 3000)
    }

    video.onerror = () => finish('', '')
    video.src = mediaUrl
  })
}

/**
 * 串行补全缩略图/时长（对齐去字幕的串行 await，避免同时解码多个视频把界面拖卡）
 * 每抓完一个就 emit 一次，用户能看着缩略图逐个出现
 */
async function hydrateMediaMeta(targets: MediaItem[]) {
  for (const item of targets) {
    if (!item?.filePath || item.thumbnail) continue
    const meta = await loadVideoMeta(toPreviewUrl(item.filePath))
    if (!meta.duration && !meta.thumbnail) continue

    emit(
      'update:mediaList',
      props.mediaList.map((m) =>
        m.id === item.id
          ? { ...m, thumbnail: meta.thumbnail || m.thumbnail, duration: meta.duration || m.duration }
          : m
      )
    )
  }
}
</script>

<style scoped>
.media-list-card {
  padding: 20px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  position: relative;
}

.media-list-card.drag-over {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-title-box {
  display: flex;
  align-items: center;
  gap: 12px;
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

.req-star { color: var(--status-danger); }

.badge-count {
  font-size: 12px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 20px;
  padding: 1px 9px;
  font-weight: 600;
}

.badge-folder {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 1px 8px;
}

.level-select {
  font-size: 11px;
  font-weight: 600;
  padding: 0;
  margin: 0;
  border-radius: 6px;
  line-height: 17px;
  color: var(--primary-color);
  background: transparent;
  border: none;
  cursor: pointer;
  outline: none;
}

/* 与对应表说明行的 level-badge 同一套蓝底蓝框视觉 */
.level-inline {
  display: inline-block;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 17px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  vertical-align: 1px;
}

.badge-count { display: inline-flex; align-items: center; gap: 4px; }
.quick-batch-ops { display: flex; align-items: center; gap: 4px; }

/* 追加导入提示条 */
.drop-more-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 10px;
  padding: 9px;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all .15s;
}
.drop-more-hint:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 拖入提示区 */
.drop-zone-hint {
  flex: 1;                  /* 空列表时占满卡片高度 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.drop-hint-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 34px 20px;   /* 原 20px 16px，加大 ~40% 让空状态更有分量 */
  border: 1.5px dashed var(--border-highlight);
  border-radius: 12px;
  cursor: pointer;
  background: var(--bg-detail);
  transition: all 0.25s ease;
  gap: 8px;
}

.drop-hint-inner:hover {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.drop-icon-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.drop-icon {
  font-size: 32px;
  color: var(--primary-color);
  opacity: 0.8;
}

.drop-arrow {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.drop-sub-tip {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.75;
  margin-top: 2px;
}

.drop-sep { opacity: 0.5; }

.drop-overlay {
  position: absolute;
  inset: 0;
  border-radius: 14px;
  background: rgba(99, 102, 241, 0.12);
  border: 2px dashed var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}

.drag-overlay-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.drag-overlay-icon {
  font-size: 42px;
  color: var(--primary-color);
}

.drag-overlay-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--primary-color);
}

/* 工具栏 */
.media-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  row-gap: 8px;
}

.media-toolbar .badge-count { white-space: nowrap; flex-shrink: 0; }
.quick-batch-ops { display: flex; align-items: center; gap: 8px; }

/* 视频列表 */
.video-list {
  flex: 1;                  /* 撑满卡片剩余高度 */
  min-height: 220px;        /* 兜底：窗口极矮时不被压扁 */
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 4px;
}

.video-card-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0;
}

.video-card-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-detail);
}

.video-thumb {
  position: relative;
  flex: 0 0 auto;        /* 固定尺寸，不参与 flex 伸缩 */
  width: 112px;          /* 固定宽 */
  height: 63px;          /* 16:9 固定高（不再用 padding-top 撑） */
  background: #000;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
}

.video-thumb .thumb-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-thumb .thumb-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.3);
}

.duration-badge {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 0 4px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  font-size: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  line-height: 14px;
}

.format-badge {
  position: absolute;
  left: 4px;
  top: 4px;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  padding: 0 4px;
  border-radius: 3px;
  line-height: 14px;
}

.video-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.video-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.video-idx {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.12);
  padding: 0 5px;
  border-radius: 4px;
  white-space: nowrap;
}

.name-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 多层文件夹面包屑 */
.folder-crumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  font-size: 11px;
  color: var(--text-muted);
}

.crumb {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.crumb-ic { font-size: 11px; }

.crumb-name {
  color: var(--text-secondary);
  font-weight: 500;
}

.crumb-sep {
  color: var(--border-highlight);
  margin: 0 1px;
}

.video-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  flex-wrap: wrap;
}

.meta-item { color: var(--text-secondary); }

.meta-path {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
  opacity: 0.6;
  font-size: 10px;
}

.row-actions { flex-shrink: 0; }

.del-btn { font-size: 15px; color: var(--text-muted); }
.del-btn:hover { color: var(--status-danger); }

/* 集数调整 */
.clickable-ep-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(99, 102, 241, 0.12);
  color: var(--primary-color);
  padding: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.clickable-ep-badge:hover { background: var(--primary-color); color: #fff; }

.ep-edit-popover { display: flex; flex-direction: column; gap: 8px; padding: 4px 0; }
.popover-tip { font-size: 12px; color: var(--text-muted); }

/* ===== 面包屑 ===== */
.crumb-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 2px 2px 10px;
  font-size: 12px;
  color: var(--text-muted);
}
.crumb-item {
  padding: 2px 9px;
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  transition: all .15s;
}
.crumb-item:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.crumb-item.cur {
  background: transparent;
  border-color: transparent;
  color: var(--text-main);
  font-weight: 600;
  cursor: default;
}
.crumb-sep { color: var(--text-muted); user-select: none; }
.crumb-count { margin-left: auto; opacity: 0.8; }
.crumb-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  font-size: 12px;
  transition: all .15s;
}
.crumb-back:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* ===== 文件夹行 ===== */
.folder-row-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  transition: all .15s;
}
.folder-row-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-detail);
}
.folder-row-item:active { transform: scale(0.998); }

.folder-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(99, 102, 241, 0.12);
  color: var(--primary-color);
  font-size: 20px;
}
.folder-info { flex: 1; min-width: 0; }
.folder-name {
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.folder-count {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.folder-enter { color: var(--text-muted); flex-shrink: 0; transition: transform .15s, color .15s; }
.folder-row-item:hover .folder-enter { color: var(--primary-color); transform: translateX(3px); }
.level-tag {
  font-size: 10px;
  font-weight: 400;
  padding: 1px 6px;
  margin-left: 6px;
  border-radius: 8px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  vertical-align: 1px;
}
.level-tag.is-unit {
  color: var(--primary-color);
  border-color: var(--primary-color);
  font-weight: 600;
}
</style>
