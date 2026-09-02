<template>
  <div class="task-center-workspace">
    <!-- 1. 顶部数据看板与全局工作流调度控制台 -->
    <div class="task-stats-bar glass-card">
      <div class="stats-group">
        <div class="stat-card">
          <div class="stat-num">{{ taskStore.tasks.length }}</div>
          <div class="stat-label">全部任务</div>
        </div>
        <div class="stat-card running-card">
          <div class="stat-num">{{ taskStore.runningTasksCount }}</div>
          <div class="stat-label">并发执行中</div>
        </div>
        <div class="stat-card queued-card">
          <div class="stat-num">{{ taskStore.queuedTasksCount }}</div>
          <div class="stat-label">排队待发</div>
        </div>
        <div class="stat-card success-card">
          <div class="stat-num">{{ taskStore.successTasksCount }}</div>
          <div class="stat-label">发布成功</div>
        </div>
        <div class="stat-card failed-card">
          <div class="stat-num">{{ taskStore.failedTasksCount }}</div>
          <div class="stat-label">失败/异常</div>
        </div>
      </div>

      <div class="stats-actions">
        <!-- 启动/中止多线程工作流 -->
        <el-button 
          v-if="taskStore.isExecuting" 
          type="danger" 
          size="default" 
          class="exec-btn"
          @click="taskStore.cancelWorkflow"
        >
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>中止工作流</span>
        </el-button>

        <el-button 
          v-else 
          type="primary" 
          size="default" 
          class="exec-btn gradient-btn-matrix"
          :disabled="taskStore.queuedTasksCount === 0"
          @click="taskStore.triggerMultiLaneExecution"
        >
          <el-icon><Promotion /></el-icon>
          <span>启动多线程并发调度 ({{ taskStore.lanes.length }} 线程)</span>
        </el-button>

        <el-tooltip 
          :content="taskStore.canAddLane ? '新建一个独立的并发线程通道' : `已达系统设置的最大并发限制 (${taskStore.maxConcurrency} 个线程)，可前往「系统设置」调整`" 
          placement="top"
        >
          <el-button 
            size="small" 
            plain 
            :disabled="!taskStore.canAddLane"
            @click="taskStore.addLane"
          >
            <el-icon><Plus /></el-icon> 新增线程通道
          </el-button>
        </el-tooltip>

        <el-dropdown trigger="click" @command="handleAutoDistribute">
          <el-button size="small" plain>
            <el-icon><MagicStick /></el-icon> 智能分流
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="anti-risk">🛡️ 智能防风控均分 (同平台串行，跨平台并发)</el-dropdown-item>
              <el-dropdown-item divided command="1">单线程串行执行 (1个线程处理全部)</el-dropdown-item>
              <el-dropdown-item command="2" v-if="taskStore.maxConcurrency >= 2">双线程并发分流 (2个线程并发)</el-dropdown-item>
              <el-dropdown-item command="3" v-if="taskStore.maxConcurrency >= 3">3线程高并发 (推荐)</el-dropdown-item>
              <el-dropdown-item command="4" v-if="taskStore.maxConcurrency >= 4">4线程极速分发</el-dropdown-item>
              <el-dropdown-item command="5" v-if="taskStore.maxConcurrency >= 5">5线程全负荷并发</el-dropdown-item>
              <el-dropdown-item divided command="max">极致全并发 (按最大并发限制 {{ taskStore.maxConcurrency }} 均分)</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button size="small" type="primary" plain class="log-trigger-btn" @click="openGlobalLogs">
          <el-icon><Monitor /></el-icon> 控制台日志
          <span class="log-indicator-dot" v-if="taskStore.runningTasksCount > 0"></span>
        </el-button>

        <el-button size="small" plain @click="taskStore.clearFinishedTasks">
          <el-icon><Delete /></el-icon> 清理已完成
        </el-button>
      </div>
    </div>

    <!-- 2. 批次过滤器与防风控冲突提示栏 -->
    <div class="batch-filter-bar glass-card" v-if="taskStore.batches.length > 0">
      <div class="batch-filter-left">
        <el-icon><CollectionTag /></el-icon>
        <span class="filter-label">批次聚焦:</span>
        <div class="batch-pills-scroll custom-scrollbar">
          <span 
            class="batch-pill" 
            :class="{ active: selectedBatch === 'all' }"
            @click="selectedBatch = 'all'"
          >
            全部任务 ({{ taskStore.tasks.length }})
          </span>

          <span 
            v-for="(batch, bIdx) in taskStore.batches.slice(0, 8)" 
            :key="batch.id"
            class="batch-pill"
            :class="{ 
              active: selectedBatch === batch.id,
              'is-latest': batch.id === taskStore.latestBatchId 
            }"
            @click="selectedBatch = batch.id"
          >
            <span v-if="batch.id === taskStore.latestBatchId" class="latest-sparkle">✨ 刚刚提交:</span>
            <span v-else class="batch-idx-label">批次 #{{ bIdx + 1 }}:</span>
            <span class="batch-name-text" :title="batch.name">{{ batch.name }}</span>
            <span class="batch-count-tag">{{ getBatchTaskCount(batch.id) }}</span>
          </span>
        </div>
      </div>

      <!-- 防风控并发冲突警告 -->
      <div class="risk-alert-box" v-if="taskStore.platformConflicts.length > 0">
        <el-icon class="risk-icon"><WarningFilled /></el-icon>
        <span class="risk-text">
          检测到 <strong>{{ taskStore.platformConflicts.map(p => getPlatformStyle(p).name).join('、') }}</strong> 任务分布在多个并发通道中，可能增加 IP 频次风控风险
        </span>
        <el-button size="small" type="warning" plain @click="taskStore.autoDistributeTasksToLanes()">
          一键优化防风控
        </el-button>
      </div>
    </div>

    <!-- 3. 可视化多协程任务流泳道画板 (Multi-Lane Workflow Canvas) -->
    <div class="workflow-canvas-panel glass-card">
      <div class="canvas-header">
        <div class="header-left">
          <span class="canvas-tag">WORKFLOW STUDIO</span>
          <span class="canvas-title">多协程任务工作流编排画板</span>
          <span class="canvas-hint">通道间并行并发 (Go Goroutines)，通道内按卡片箭头串行顺序执行，支持跨通道自由拖拽</span>
        </div>

        <div class="header-right">
          <span class="lane-counter">
            当前激活 <strong>{{ taskStore.lanes.length }}</strong> / {{ taskStore.maxConcurrency }} 个并发线程通道
            <router-link to="/settings" class="settings-link" title="前往系统设置修改最大并发数">
              <el-icon><Setting /></el-icon> 配置上限
            </router-link>
          </span>
        </div>
      </div>

      <!-- 泳道容器列表 -->
      <div class="lanes-scroll-container custom-scrollbar">
        <div 
          v-for="(lane, laneIdx) in taskStore.lanes" 
          :key="lane.id"
          class="workflow-lane-card"
          :class="lane.status"
          @dragover.prevent
          @drop="handleDropOnLane(lane.id, $event)"
        >
          <!-- 泳道头部控制栏 -->
          <div class="lane-header">
            <div class="lane-title-meta">
              <span class="lane-index-pill">Goroutine #{{ laneIdx + 1 }}</span>
              <span class="lane-name">{{ lane.name }}</span>
              <span class="lane-status-badge" :class="lane.status">
                <el-icon v-if="lane.status === 'running'" class="is-loading"><Loading /></el-icon>
                <el-icon v-else-if="lane.status === 'completed'"><Check /></el-icon>
                <el-icon v-else-if="lane.status === 'failed'"><WarningFilled /></el-icon>
                <span>{{ getLaneStatusText(lane.status) }}</span>
              </span>
            </div>

            <div class="lane-actions">
              <div class="delay-setting-box" title="该通道内各任务节点的默认基准防风控延时秒数">
                <span class="delay-label">通道默认延时:</span>
                <el-input-number 
                  v-model="lane.delayBetweenTasks" 
                  :min="0" 
                  :max="3600" 
                  :step="5" 
                  size="small" 
                  style="width: 95px" 
                  controls-position="right"
                  @change="handleLaneDelayChange(lane)"
                />
                <span class="delay-unit">秒</span>
              </div>

              <el-button 
                v-if="taskStore.lanes.length > 1" 
                size="small" 
                type="danger" 
                link 
                title="删除该线程通道 (任务将退回待分配池)"
                @click="taskStore.removeLane(lane.id)"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>

          <!-- 泳道卡片箭头流 (Card & Arrow Stream) -->
          <div class="lane-track-body custom-scrollbar">
            <!-- 泳道卡片群 -->
            <div 
              v-for="(task, taskIdx) in lane.tasks" 
              :key="task.id"
              class="lane-node-item"
              :class="{ 'is-faded': selectedBatch !== 'all' && task.batchId !== selectedBatch }"
            >
              <!-- 任务卡片 (状态机保护: 执行中的任务锁定禁止拖拽，可中止后拖拽) -->
              <div 
                class="flow-card"
                :class="[task.status, { 
                  'is-drag-source': draggingTaskId === task.id,
                  'is-running-locked': task.status === 'running',
                  'is-latest-highlight': task.batchId === taskStore.latestBatchId
                }]"
                :draggable="task.status !== 'running'"
                @dragstart="task.status !== 'running' ? handleDragStart(task.id, lane.id, taskIdx, $event) : $event.preventDefault()"
                @dragend="handleDragEnd"
              >
                <!-- 卡片顶部标识栏 -->
                <div class="card-drag-bar" :title="task.status === 'running' ? '当前任务正在并发执行中，锁定禁止拖拽。可先点击「中止」后再拖拽调整。' : '按住拖拽以移动卡片或调序'">
                  <div class="drag-bar-left">
                    <el-icon v-if="task.status === 'running'" class="is-loading"><Loading /></el-icon>
                    <el-icon v-else><Rank /></el-icon>
                    <span class="card-step-num">#{{ taskIdx + 1 }}</span>
                    <span v-if="task.batchId === taskStore.latestBatchId" class="latest-badge-pill">✨ 最新</span>
                  </div>
                  <span class="locked-hint" v-if="task.status === 'running'">执行中锁定</span>
                  <span class="cancelled-hint" v-else-if="task.status === 'cancelled'">已中止(可拖拽)</span>
                </div>

                <!-- 批次/来源视频信息 -->
                <div class="card-source-row" v-if="task.videoFileName || task.batchName" :title="task.videoFileName || task.batchName">
                  <el-icon class="source-icon"><Film /></el-icon>
                  <span class="source-text">{{ task.videoFileName || task.batchName }}</span>
                </div>

                <div class="card-plat-row">
                  <span class="card-plat-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
                    {{ getPlatformStyle(task.platform).name }}
                  </span>
                  <span class="card-acc-name" :title="task.nickname || task.account">
                    {{ task.nickname || task.account }}
                  </span>
                </div>

                <div class="card-title-row" :title="task.title">
                  <span class="card-action-tag">{{ task.action === 'upload-video' ? '视频' : '图文' }}</span>
                  <span class="card-title-text">{{ task.title }}</span>
                </div>

                <!-- 风险熔断与准入拦截横幅 -->
                <div class="card-risk-banner" v-if="task.isPaused || task.errorMsg?.includes('熔断') || task.errorMsg?.includes('准入')">
                  <el-icon class="risk-icon"><WarningFilled /></el-icon>
                  <span class="risk-banner-text" :title="task.pauseReason || task.errorMsg">
                    {{ task.pauseReason || task.errorMsg }}
                  </span>
                  <el-button size="small" type="danger" link @click.stop="taskStore.resumeAccountRisk(task.platform, task.account)">
                    解除熔断
                  </el-button>
                </div>

                <div class="card-footer-row">
                  <span class="card-status-pill" :class="task.status">
                    <el-icon v-if="task.status === 'running'" class="is-loading"><Loading /></el-icon>
                    <el-icon v-else-if="task.status === 'success'"><Check /></el-icon>
                    <el-icon v-else-if="task.status === 'failed'"><WarningFilled /></el-icon>
                    <el-icon v-else-if="task.status === 'queued'"><Clock /></el-icon>
                    <el-icon v-else-if="task.status === 'cancelled'"><CircleClose /></el-icon>
                    <span>{{ getStatusText(task.status) }}</span>
                  </span>

                  <div class="card-btns" @click.stop>
                    <!-- 执行中提供中止按钮 -->
                    <el-button 
                      v-if="task.status === 'running'"
                      size="small" 
                      type="danger" 
                      link 
                      title="中止该任务，中止后可自由拖拽调序"
                      @click="taskStore.cancelTask(task.id)"
                    >
                      <el-icon><CircleClose /></el-icon> 中止
                    </el-button>

                    <!-- 已中止或失败提供恢复重试按钮 -->
                    <el-button 
                      v-if="task.status === 'failed' || task.status === 'cancelled'"
                      size="small" 
                      type="warning" 
                      link 
                      title="重新排队恢复此任务"
                      @click="taskStore.retryTask(task.id)"
                    >
                      <el-icon><RefreshRight /></el-icon> 恢复
                    </el-button>

                    <el-button size="small" type="primary" link @click="openTaskLogs(task)">
                      <el-icon><Monitor /></el-icon> 日志
                    </el-button>
                  </div>
                </div>
              </div>

              <!-- 步骤间箭头连接器 (Arrow Connector，独立调节单步骤专属延时，不影响通道全局延时) -->
              <div class="step-connector" v-if="taskIdx < lane.tasks.length - 1">
                <div class="connector-line"></div>
                <el-popover placement="top" :width="190" trigger="click">
                  <template #reference>
                    <span 
                      class="connector-delay-pill clickable" 
                      title="点击仅修改此连接处的专属延时 (不影响通道全局默认延时)"
                    >
                      延时 {{ getStepDelay(task, lane) }}s
                    </span>
                  </template>
                  <div class="pop-delay-editor">
                    <div class="pop-delay-title">步骤专属延时设置</div>
                    <div class="pop-delay-hint">当前卡片发布后，等待多少秒再启动下一个任务 (仅影响此连接)</div>
                    <div class="pop-delay-control">
                      <el-input-number 
                        v-model="task.delaySeconds" 
                        :min="0" 
                        :max="3600" 
                        :step="5" 
                        size="small" 
                        controls-position="right"
                        style="width: 110px"
                        @change="handleStepDelayChange(task)"
                      />
                      <span class="pop-delay-unit">秒</span>
                    </div>
                    <div class="pop-delay-footer">
                      <el-button size="small" link type="primary" @click="resetStepDelay(task, lane)">
                        重置为通道默认 ({{ lane.delayBetweenTasks ?? 15 }}s)
                      </el-button>
                    </div>
                  </div>
                </el-popover>
                <el-icon class="connector-arrow-icon"><Right /></el-icon>
              </div>
            </div>

            <!-- 空泳道放置提示卡片 -->
            <div 
              class="lane-drop-placeholder"
              :class="{ 'is-drag-target': isDragging && draggingFromLaneId !== lane.id }"
            >
              <el-icon><Plus /></el-icon>
              <span>{{ lane.tasks.length === 0 ? '将任务拖拽至此处放入该线程' : '拖入任务追加至末尾' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. 待分配任务停靠池 (Unassigned Task Dock，支持随时拖回与查看) -->
    <div 
      class="unassigned-dock glass-card"
      :class="{ 'is-drag-over-dock': isDragging && draggingFromLaneId !== null }"
      @dragover.prevent
      @drop="handleDropOnUnassigned($event)"
    >
      <div class="dock-title-row">
        <div class="title-left">
          <el-icon><Box /></el-icon>
          <span class="title-text">待分配任务池 ({{ taskStore.unassignedTasks.length }})</span>
          <span class="title-sub">可将上方线程通道中的卡片拖拽回此处暂存，或点击「智能分流」一键自动排布</span>
        </div>
        <div class="title-right" v-if="taskStore.unassignedTasks.length > 0">
          <el-button size="small" type="primary" link @click="taskStore.autoDistributeTasksToLanes()">
            一键智能按平台防风控分流
          </el-button>
        </div>
      </div>

      <div class="dock-cards-tray custom-scrollbar" v-if="taskStore.unassignedTasks.length > 0">
        <div 
          v-for="task in taskStore.unassignedTasks" 
          :key="task.id"
          class="unassigned-card"
          :class="[task.status, { 'is-drag-source': draggingTaskId === task.id }]"
          :draggable="task.status !== 'running'"
          @dragstart="task.status !== 'running' ? handleDragStart(task.id, null, -1, $event) : $event.preventDefault()"
          @dragend="handleDragEnd"
        >
          <div class="card-left">
            <span class="dock-plat-badge" :style="{ background: getPlatformStyle(task.platform).brandColor }">
              {{ getPlatformStyle(task.platform).name }}
            </span>
            <span class="dock-acc-name">{{ task.nickname || task.account }}</span>
            <span class="dock-title-snippet" :title="task.title">{{ task.title }}</span>
            <span class="card-status-pill" :class="task.status">
              <el-icon v-if="task.status === 'success'"><Check /></el-icon>
              <el-icon v-else-if="task.status === 'failed'"><WarningFilled /></el-icon>
              <el-icon v-else-if="task.status === 'queued'"><Clock /></el-icon>
              <el-icon v-else-if="task.status === 'cancelled'"><CircleClose /></el-icon>
              <span>{{ getStatusText(task.status) }}</span>
            </span>
          </div>
          <div class="card-right-tools">
            <el-button size="small" type="primary" link @click.stop="openTaskLogs(task)">
              <el-icon><Monitor /></el-icon>
            </el-button>
            <el-icon class="drag-icon"><Rank /></el-icon>
          </div>
        </div>
      </div>

      <div class="dock-empty-hint" v-else>
        <span>全部任务已装载至上方线程通道中。若需暂存某个任务，可直接按住卡片拖拽放置到此处。</span>
      </div>
    </div>

    <!-- 5. 抽屉式任务详情与实时终端日志控制台 -->
    <TaskLogDrawer 
      v-model="showLogDrawer"
      :task="selectedTaskForDrawer"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatformConfig } from '../config/platforms'
import { useTaskStore } from '../stores/taskStore'
import TaskLogDrawer from '../components/matrix/TaskLogDrawer.vue'
import type { PublishTask, TaskStatus } from '../types/task'

const taskStore = useTaskStore()

// 批次聚焦状态
const selectedBatch = ref<string>('all')

// 抽屉状态
const showLogDrawer = ref(false)
const selectedTaskForDrawer = ref<PublishTask | null>(null)

// 拖拽状态
const isDragging = ref(false)
const draggingTaskId = ref<string | null>(null)
const draggingFromLaneId = ref<string | null>(null)

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getStatusText = (status: TaskStatus) => {
  switch (status) {
    case 'running': return '执行中'
    case 'queued': return '排队中'
    case 'success': return '发布成功'
    case 'failed': return '发布失败'
    case 'cancelled': return '已取消'
    default: return '待调度'
  }
}

const getLaneStatusText = (status: string) => {
  switch (status) {
    case 'running': return '多协程并发中'
    case 'completed': return '全部执行完成'
    case 'failed': return '存在异常'
    default: return '空闲待命'
  }
}

const getBatchTaskCount = (batchId: string) => {
  return taskStore.tasks.filter(t => t.batchId === batchId).length
}

const openGlobalLogs = () => {
  selectedTaskForDrawer.value = null
  showLogDrawer.value = true
}

const getStepDelay = (task: PublishTask, lane: any) => {
  if (task.delaySeconds !== undefined && task.delaySeconds !== null) {
    return task.delaySeconds
  }
  return lane.delayBetweenTasks ?? 15
}

const handleLaneDelayChange = (lane: any) => {
  if (lane && lane.id) {
    const val = Number(lane.delayBetweenTasks) || 0
    taskStore.setLaneDelay(lane.id, val)
    ElMessage.success(`已更新「${lane.name}」通道默认延时为 ${val} 秒`)
  }
}

const handleStepDelayChange = (task: PublishTask) => {
  if (task && task.id) {
    const val = Number(task.delaySeconds) || 0
    taskStore.setTaskDelay(task.id, val)
    ElMessage.success(`已设置该步骤专属延时为 ${val} 秒`)
  }
}

const resetStepDelay = (task: PublishTask, lane: any) => {
  const defaultVal = lane.delayBetweenTasks ?? 15
  task.delaySeconds = defaultVal
  taskStore.setTaskDelay(task.id, defaultVal)
  ElMessage.info(`已重置该步骤延时为通道默认 (${defaultVal}秒)`)
}

const handleAutoDistribute = (cmd: string) => {
  if (cmd === 'anti-risk') {
    taskStore.autoDistributeTasksToLanes()
    ElMessage.success('已应用智能防风控分流（同平台串行，跨平台并发）')
  } else if (cmd === 'max') {
    taskStore.autoDistributeTasksToLanes(undefined, taskStore.maxConcurrency)
    ElMessage.success(`已按系统最大并发限制 (${taskStore.maxConcurrency} 线程) 智能均分`)
  } else {
    const num = parseInt(cmd, 10)
    if (!isNaN(num)) {
      taskStore.autoDistributeTasksToLanes(undefined, num)
      ElMessage.success(`已均分到 ${num} 个并发线程`)
    }
  }
}

// -----------------------------------------------------------------------------
// HTML5 拖拽流状态管理
// -----------------------------------------------------------------------------
const handleDragStart = (taskId: string, fromLaneId: string | null, _idx: number, e: DragEvent) => {
  isDragging.value = true
  draggingTaskId.value = taskId
  draggingFromLaneId.value = fromLaneId
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', taskId)
  }
}

const handleDragEnd = () => {
  isDragging.value = false
  draggingTaskId.value = null
  draggingFromLaneId.value = null
}

const handleDropOnLane = (targetLaneId: string, _e: DragEvent) => {
  if (!draggingTaskId.value) return

  const targetLane = taskStore.lanes.find(l => l.id === targetLaneId)
  if (!targetLane) return

  taskStore.moveTask({
    taskId: draggingTaskId.value,
    fromLaneId: draggingFromLaneId.value,
    toLaneId: targetLaneId,
    newIndex: targetLane.tasks.length
  })

  ElMessage.success(`已将任务移入「${targetLane.name}」`)
  handleDragEnd()
}

const handleDropOnUnassigned = (_e: DragEvent) => {
  if (!draggingTaskId.value) return

  taskStore.moveTask({
    taskId: draggingTaskId.value,
    fromLaneId: draggingFromLaneId.value,
    toLaneId: null,
    newIndex: 0
  })

  ElMessage.info('已将任务移入待分配池')
  handleDragEnd()
}
</script>

<style scoped>
.task-center-workspace {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 88px);
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

/* 1. 顶部数据看板与操作栏 */
.task-stats-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-radius: 12px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
}

.stats-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5px 12px;
  border-radius: 8px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  min-width: 64px;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.stat-label {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 1px;
}

.running-card .stat-num { color: #3b82f6; }
.queued-card .stat-num { color: #eab308; }
.success-card .stat-num { color: #10b981; }
.failed-card .stat-num { color: #ef4444; }

.stats-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.exec-btn {
  font-weight: 700;
  padding: 7px 18px;
  border-radius: 7px;
}

.gradient-btn-matrix {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
  border: none !important;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
}

.log-trigger-btn {
  position: relative;
}

.log-indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  position: absolute;
  top: 4px;
  right: 4px;
}

/* 2. 批次过滤器与冲突提示 */
.batch-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  gap: 12px;
  flex-shrink: 0;
}

.batch-filter-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  overflow: hidden;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.batch-pills-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding: 2px 0;
}

.batch-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  user-select: none;
}

.batch-pill:hover {
  border-color: var(--primary-light);
  color: var(--text-main);
}

.batch-pill.active {
  background: rgba(99, 102, 241, 0.18);
  border-color: var(--primary-light);
  color: #c7d2fe;
  font-weight: 700;
}

.batch-pill.is-latest {
  border-color: rgba(168, 85, 247, 0.4);
}

.latest-sparkle {
  color: #c084fc;
  font-weight: 700;
}

.batch-idx-label {
  color: var(--text-muted);
}

.batch-name-text {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.batch-count-tag {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
}

.risk-alert-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px;
  border-radius: 6px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  font-size: 11px;
  color: #fbbf24;
  white-space: nowrap;
}

.risk-icon {
  font-size: 13px;
  color: #f59e0b;
}

/* 3. 多泳道画板 */
.workflow-canvas-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  overflow: hidden;
  min-height: 0;
}

.canvas-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.canvas-tag {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #818cf8;
  font-weight: 700;
}

.canvas-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.canvas-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.lane-counter {
  font-size: 11px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.lane-counter strong {
  color: #818cf8;
}

.settings-link {
  font-size: 10px;
  color: var(--primary-light);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.1);
}

.settings-link:hover {
  background: rgba(99, 102, 241, 0.2);
}

.lanes-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.workflow-lane-card {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-detail);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease;
}

.workflow-lane-card:hover {
  border-color: var(--border-highlight);
}

.workflow-lane-card.running {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.04);
}

.lane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.08);
  border-bottom: 1px solid var(--border-subtle);
}

.lane-title-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lane-index-pill {
  font-size: 9px;
  font-weight: 700;
  color: #c084fc;
  background: rgba(168, 85, 247, 0.15);
  padding: 1px 5px;
  border-radius: 3px;
}

.lane-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.lane-status-badge {
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 3px;
}

.lane-status-badge.running { color: #3b82f6; }
.lane-status-badge.completed { color: #10b981; }
.lane-status-badge.failed { color: #ef4444; }

.lane-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.delay-setting-box {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
}

.delay-label {
  color: var(--text-secondary);
}

.delay-unit {
  color: var(--text-muted);
  font-size: 10px;
}

/* 泳道横向卡片流 */
.lane-track-body {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  overflow-x: auto;
  min-height: 115px;
  box-sizing: border-box;
}

.lane-node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  transition: opacity 0.2s ease;
}

.lane-node-item.is-faded {
  opacity: 0.25;
}

.flow-card {
  width: 200px;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  cursor: grab;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 5px;
  user-select: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.flow-card:active {
  cursor: grabbing;
}

.flow-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary-light);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
}

.flow-card.running {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.12);
  cursor: default;
}

.flow-card.is-running-locked {
  cursor: default;
}

.flow-card.is-running-locked:hover {
  transform: none;
}

.flow-card.is-latest-highlight {
  border-color: rgba(168, 85, 247, 0.5);
  box-shadow: 0 0 12px rgba(168, 85, 247, 0.2);
}

.flow-card.cancelled {
  border-color: rgba(148, 163, 184, 0.4);
  background: rgba(148, 163, 184, 0.05);
}

.flow-card.success {
  border-color: rgba(16, 185, 129, 0.4);
}

.flow-card.failed {
  border-color: rgba(239, 68, 68, 0.4);
}

.flow-card.is-drag-source {
  opacity: 0.4;
  border-style: dashed;
}

.card-drag-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
}

.drag-bar-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.latest-badge-pill {
  font-size: 9px;
  color: #c084fc;
  background: rgba(168, 85, 247, 0.18);
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 700;
}

.locked-hint {
  font-size: 9px;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.15);
  padding: 1px 4px;
  border-radius: 3px;
}

.cancelled-hint {
  font-size: 9px;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  padding: 1px 4px;
  border-radius: 3px;
}

.card-step-num {
  font-size: 10px;
  font-weight: 700;
  color: #818cf8;
}

.card-source-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.08);
  padding: 2px 5px;
  border-radius: 4px;
}

.source-icon {
  font-size: 11px;
  flex-shrink: 0;
}

.source-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-plat-row {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-plat-badge {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
}

.card-acc-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-action-tag {
  font-size: 9px;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.12);
  padding: 1px 3px;
  border-radius: 2px;
}

.card-title-text {
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-risk-banner {
  margin-top: 3px;
  padding: 2px 5px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.28);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  color: #f87171;
}

.risk-icon {
  font-size: 11px;
  flex-shrink: 0;
  color: #ef4444;
}

.risk-banner-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 4px;
  font-size: 9px;
}

.card-status-pill {
  display: flex;
  align-items: center;
  gap: 2px;
  font-weight: 600;
}

.card-status-pill.running { color: #3b82f6; }
.card-status-pill.success { color: #10b981; }
.card-status-pill.failed { color: #ef4444; }
.card-status-pill.queued { color: #eab308; }

.step-connector {
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--text-muted);
}

.connector-line {
  width: 10px;
  height: 1px;
  background: var(--border-highlight);
}

.connector-delay-pill {
  font-size: 8px;
  color: #a855f7;
  background: rgba(168, 85, 247, 0.12);
  border: 1px solid rgba(168, 85, 247, 0.25);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.connector-delay-pill.clickable {
  cursor: pointer;
}

.connector-delay-pill.clickable:hover {
  background: rgba(168, 85, 247, 0.25);
  border-color: #a855f7;
  color: #e9d5ff;
}


.pop-delay-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 2px;
}

.pop-delay-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.pop-delay-hint {
  font-size: 10px;
  color: var(--text-muted);
  line-height: 1.3;
}

.pop-delay-control {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.pop-delay-unit {
  font-size: 11px;
  color: var(--text-muted);
}

.pop-delay-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 4px;
}

.connector-arrow-icon {
  font-size: 12px;
  color: #818cf8;
}

.lane-drop-placeholder {
  min-width: 130px;
  height: 85px;
  border: 1.5px dashed var(--border-subtle);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: var(--text-muted);
  font-size: 10px;
  padding: 0 10px;
  text-align: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.lane-drop-placeholder.is-drag-target {
  border-color: var(--primary-light);
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary-light);
}

/* 4. 待分配任务池 */
.unassigned-dock {
  display: flex;
  flex-direction: column;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  flex-shrink: 0;
  gap: 8px;
  transition: all 0.2s ease;
}

.unassigned-dock.is-drag-over-dock {
  border-color: var(--primary-light);
  background: rgba(99, 102, 241, 0.08);
}

.dock-empty-hint {
  font-size: 11px;
  color: var(--text-muted);
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--border-subtle);
  text-align: center;
}

.dock-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-main);
  font-weight: 700;
}

.title-sub {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: normal;
  margin-left: 4px;
}

.dock-cards-tray {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 3px;
}

.unassigned-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 10px;
  border-radius: 6px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  cursor: grab;
  transition: all 0.15s ease;
  flex-shrink: 0;
  user-select: none;
}

.unassigned-card:hover {
  border-color: var(--primary-light);
  background: rgba(99, 102, 241, 0.08);
}

.card-left {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-right-tools {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dock-plat-badge {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
}

.dock-acc-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-main);
}

.dock-title-snippet {
  font-size: 10px;
  color: var(--text-muted);
  max-width: 120px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drag-icon {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
