<template>
  <div class="live-canvas-container" ref="containerRef">
    <!-- 顶部状态栏 -->
    <div class="canvas-header-bar">
      <div class="header-left">
        <span class="live-indicator" :class="{ 'is-active': isReceiving }"></span>
        <span class="live-title">{{ title || '实时无头浏览器视窗 (CDP)' }}</span>
        <span class="fps-badge" v-if="fps > 0">{{ fps }} FPS</span>
      </div>
      <div class="header-right">
        <span class="res-info" v-if="frameWidth > 0">{{ frameWidth }}×{{ frameHeight }}</span>
        <el-button 
          size="small" 
          type="info" 
          link 
          :title="isInteractive ? '已开启双向鼠标反向交互' : '已禁用交互'"
          @click="isInteractive = !isInteractive"
        >
          <el-icon><Pointer /></el-icon>
          <span>{{ isInteractive ? '交互开' : '只读' }}</span>
        </el-button>

        <el-tooltip :content="viewMode === 'contain' ? '当前：全貌适应(无截断)，点击切换为 1:1 原始尺寸' : '当前：1:1 原生高清(平滑滚动)，点击切换为全貌适应'" placement="bottom">
          <el-button size="small" type="primary" link @click="toggleViewMode">
            <el-icon><FullScreen /></el-icon>
            <span>{{ viewMode === 'contain' ? '全貌适应' : '1:1 原生' }}</span>
          </el-button>
        </el-tooltip>

        <el-button size="small" type="primary" link @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 画面主视窗 -->
    <div class="canvas-viewport" :class="{ 'mode-scroll': viewMode === 'original' }" ref="viewportRef">
      <canvas 
        ref="canvasRef" 
        tabindex="0"
        class="screencast-canvas"
        :class="{ 'can-interact': isInteractive }"
        @click="handleClick"
        @mousedown="handleMouseDown"
        @mouseup="handleMouseUp"
        @mousemove="handleMouseMove"
        @wheel.prevent="handleWheel"
        @keydown="handleKeyDown"
      ></canvas>

      <!-- 等待/加载遮罩 -->
      <div class="canvas-placeholder" v-if="!hasReceivedFirstFrame">
        <el-icon class="is-loading loading-icon"><Loading /></el-icon>
        <p class="placeholder-text">正在初始化后台无头浏览器并建立 CDP 画面通道...</p>
        <span class="placeholder-sub">无需外部弹出浏览器窗口，所有扫码与交互将在当前界面实时呈现</span>
      </div>
    </div>

    <!-- 底部操作提示 -->
    <div class="canvas-footer-bar" v-if="isInteractive">
      <el-icon><InfoFilled /></el-icon>
      <span>已启用鼠标反向投屏：可直接在上方画面中滑动拼图、点击验证码或用手机扫描页面中的二维码。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { EventsOn } from '../../../wailsjs/runtime/runtime'
import { SendBrowserInput } from '../../../wailsjs/go/main/App'

const props = defineProps<{
  taskId?: string
  title?: string
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const viewportRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

const isReceiving = ref(false)
const hasReceivedFirstFrame = ref(false)
const isInteractive = ref(true)
const fps = ref(0)
const frameWidth = ref(0)
const frameHeight = ref(0)
const viewMode = ref<'contain' | 'original'>('contain')

const toggleViewMode = () => {
  viewMode.value = viewMode.value === 'contain' ? 'original' : 'contain'
}

let frameCount = 0
let fpsTimer: any = null
let unlistenFn: any = null
let lastFrameTime = 0

// 计算鼠标在画布内部原始尺寸的绝对坐标
const getCanvasCoordinates = (e: MouseEvent) => {
  if (!canvasRef.value) return { x: 0, y: 0 }
  const rect = canvasRef.value.getBoundingClientRect()
  const scaleX = canvasRef.value.width / rect.width
  const scaleY = canvasRef.value.height / rect.height
  const x = Math.round((e.clientX - rect.left) * scaleX)
  const y = Math.round((e.clientY - rect.top) * scaleY)
  return { x, y }
}

const sendMouse = async (type: string, e: MouseEvent, button: string = 'left') => {
  if (!isInteractive.value) return
  const { x, y } = getCanvasCoordinates(e)
  const targetTask = props.taskId || 'live'
  try {
    await SendBrowserInput(targetTask, 'mouse', type, x, y, button, 0, 0, '', '')
  } catch (err) {
    // 忽略未就绪静默错误
  }
}

let isMouseDown = false
let isDragging = false
let downStartX = 0
let downStartY = 0

// 点击事件：直接派发原子化的 click 指令，解决 DOM 点击不触发问题
const handleClick = async (e: MouseEvent) => {
  if (!isInteractive.value) return
  if (isDragging) {
    isDragging = false
    return
  }
  const { x, y } = getCanvasCoordinates(e)
  const targetTask = props.taskId || 'live'
  const btn = e.button === 2 ? 'right' : 'left'
  try {
    await SendBrowserInput(targetTask, 'click', 'click', x, y, btn, 0, 0, '', '')
  } catch (err) {
    // 忽略未就绪静默错误
  }
}

const handleMouseDown = (e: MouseEvent) => {
  if (!isInteractive.value) return
  isMouseDown = true
  isDragging = false
  downStartX = e.clientX
  downStartY = e.clientY
  const btn = e.button === 2 ? 'right' : 'left'
  sendMouse('mousePressed', e, btn)
}

const handleMouseUp = (e: MouseEvent) => {
  if (!isInteractive.value) return
  isMouseDown = false
  const btn = e.button === 2 ? 'right' : 'left'
  sendMouse('mouseReleased', e, btn)
}

let moveThrottle = 0
const handleMouseMove = (e: MouseEvent) => {
  if (!isInteractive.value) return
  // 仅在鼠标按住进行拖拽 (如滑动拼图验证码、选区) 时才上报移动，避免纯悬停产生海量 IPC 拥塞
  if (!isMouseDown) return
  if (Math.hypot(e.clientX - downStartX, e.clientY - downStartY) > 4) {
    isDragging = true
  }
  const now = Date.now()
  if (now - moveThrottle < 33) return // 节流约 30 次/秒
  moveThrottle = now
  sendMouse('mouseMoved', e, 'left')
}

const handleKeyDown = async (e: KeyboardEvent) => {
  if (!isInteractive.value) return
  const targetTask = props.taskId || 'live'
  try {
    await SendBrowserInput(targetTask, 'key', 'keyDown', 0, 0, 'none', 0, 0, e.key, e.key.length === 1 ? e.key : '')
    if (e.key.length === 1) {
      await SendBrowserInput(targetTask, 'key', 'char', 0, 0, 'none', 0, 0, e.key, e.key)
    }
    await SendBrowserInput(targetTask, 'key', 'keyUp', 0, 0, 'none', 0, 0, e.key, '')
  } catch (err) {}
}

const handleWheel = async (e: WheelEvent) => {
  if (!isInteractive.value) return
  const { x, y } = getCanvasCoordinates(e)
  const targetTask = props.taskId || 'live'
  try {
    await SendBrowserInput(targetTask, 'mouse', 'mouseWheel', x, y, 'none', Math.round(e.deltaX), Math.round(e.deltaY), '', '')
  } catch (err) {}
}

const handleRefresh = () => {
  hasReceivedFirstFrame.value = false
  isReceiving.value = false
}

let sharedImg: HTMLImageElement | null = null
let isDecoding = false
let queuedFrame: { data: string; width?: number; height?: number } | null = null
let decodeWatchdog: any = null

// 将 Base64 快速解包为二进制 Uint8Array Blob，交付底层显卡异步解码
const b64ToBlob = (b64: string): Blob => {
  const binary = atob(b64)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Blob([bytes], { type: 'image/jpeg' })
}

const fallbackDecode = (frame: any, onComplete: () => void) => {
  if (!sharedImg) {
    sharedImg = new Image()
  }
  sharedImg.onload = () => {
    if (canvasRef.value && sharedImg) {
      const ctx = canvasRef.value.getContext('2d', { alpha: false })
      if (ctx) {
        if (canvasRef.value.width !== sharedImg.width || canvasRef.value.height !== sharedImg.height) {
          canvasRef.value.width = sharedImg.width
          canvasRef.value.height = sharedImg.height
          frameWidth.value = sharedImg.width
          frameHeight.value = sharedImg.height
        }
        ctx.drawImage(sharedImg, 0, 0)
        hasReceivedFirstFrame.value = true
        isReceiving.value = true
        lastFrameTime = Date.now()
        frameCount++
      }
    }
    onComplete()
  }
  sharedImg.onerror = () => onComplete()
  sharedImg.src = 'data:image/jpeg;base64,' + frame.data
}

const processQueuedFrame = () => {
  if (!queuedFrame || isDecoding) return
  isDecoding = true
  const frame = queuedFrame
  queuedFrame = null

  const onComplete = () => {
    if (decodeWatchdog) {
      clearTimeout(decodeWatchdog)
      decodeWatchdog = null
    }
    isDecoding = false
    if (queuedFrame) {
      requestAnimationFrame(processQueuedFrame)
    }
  }

  // 150ms 自动看门狗：杜绝 WebKit 内核偶发丢弃 onload/onerror 导致 isDecoding 永远为 true 的致命死锁
  if (decodeWatchdog) clearTimeout(decodeWatchdog)
  decodeWatchdog = setTimeout(() => {
    if (isDecoding) {
      onComplete()
    }
  }, 150)

  try {
    if (typeof window !== 'undefined' && 'createImageBitmap' in window) {
      const blob = b64ToBlob(frame.data)
      createImageBitmap(blob).then(bitmap => {
        if (canvasRef.value) {
          const ctx = canvasRef.value.getContext('2d', { alpha: false })
          if (ctx) {
            if (canvasRef.value.width !== bitmap.width || canvasRef.value.height !== bitmap.height) {
              canvasRef.value.width = bitmap.width
              canvasRef.value.height = bitmap.height
              frameWidth.value = bitmap.width
              frameHeight.value = bitmap.height
            }
            ctx.drawImage(bitmap, 0, 0)
            hasReceivedFirstFrame.value = true
            isReceiving.value = true
            lastFrameTime = Date.now()
            frameCount++
          }
        }
        bitmap.close()
        onComplete()
      }).catch(() => {
        fallbackDecode(frame, onComplete)
      })
    } else {
      fallbackDecode(frame, onComplete)
    }
  } catch {
    onComplete()
  }
}

// 接收 CDP 帧并以跳帧/合并机制绘制，彻底消除背压卡顿
const renderFrame = (payloadData: any) => {
  try {
    const frameObj = typeof payloadData === 'string' ? JSON.parse(payloadData) : payloadData
    if (!frameObj || !frameObj.data) return

    // 若指定了 taskId，则过滤非当前任务的帧 (带前缀模糊容错)
    if (props.taskId && frameObj.taskId && frameObj.taskId !== props.taskId) {
      if (!props.taskId.includes(frameObj.taskId) && !frameObj.taskId.includes(props.taskId)) {
        return
      }
    }

    queuedFrame = frameObj
    if (!isDecoding) {
      processQueuedFrame()
    }
  } catch (err) {
    console.error('解析 CDP 画面帧异常:', err)
  }
}

onMounted(() => {
  unlistenFn = EventsOn('sau-screencast', (evt: any) => {
    const payload = evt?.message || evt?.Message || evt
    if (payload) {
      renderFrame(payload)
    }
  })

  // FPS 计数器
  fpsTimer = setInterval(() => {
    fps.value = frameCount
    frameCount = 0
    if (Date.now() - lastFrameTime > 2500) {
      isReceiving.value = false
    }
  }, 1000)
})

onUnmounted(() => {
  if (fpsTimer) clearInterval(fpsTimer)
  if (typeof unlistenFn === 'function') unlistenFn()
  sharedImg = null
  isDecoding = false
  queuedFrame = null
})
</script>

<style scoped>
.live-canvas-container {
  display: flex;
  flex-direction: column;
  background: #090d16;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  overflow: hidden;
  width: 100%;
  height: 100%;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
}

.canvas-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  transition: all 0.3s;
}

.live-indicator.is-active {
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
}

.live-title {
  font-weight: 700;
  color: #e2e8f0;
}

.fps-badge {
  font-size: 9px;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.15);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.res-info {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
}

.canvas-viewport {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #020617;
  overflow: hidden;
}

/* 1:1 原生高清滚动模式：启用平滑横纵滚动条，杜绝右侧截断 */
.canvas-viewport.mode-scroll {
  overflow: auto !important;
  align-items: flex-start !important;
  justify-content: flex-start !important;
  padding: 8px;
}

.screencast-canvas {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
  image-rendering: -webkit-optimize-contrast;
  image-rendering: crisp-edges;
}

.canvas-viewport.mode-scroll .screencast-canvas {
  max-width: none !important;
  max-height: none !important;
  width: auto !important;
  height: auto !important;
}

.screencast-canvas.can-interact {
  cursor: crosshair;
}

.canvas-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(2, 6, 23, 0.85);
  backdrop-filter: blur(4px);
  color: #94a3b8;
  padding: 20px;
  text-align: center;
}

.loading-icon {
  font-size: 28px;
  color: #38bdf8;
}

.placeholder-text {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.placeholder-sub {
  font-size: 11px;
  color: #64748b;
}

.canvas-footer-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(15, 23, 42, 0.9);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 10px;
  color: #94a3b8;
}
</style>
