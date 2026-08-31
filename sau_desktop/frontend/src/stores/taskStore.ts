import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { MatrixPublishMedia, StopActivePublish } from '../../wailsjs/go/main/App'
import { EventsOn, EventsOff } from '../../wailsjs/runtime/runtime'
import { engine } from '../../wailsjs/go/models'
import type { PublishTask, TaskBatch, TaskStatus, TaskPriority, TaskLogItem } from '../types/task'

const STORAGE_KEY = 'sau_task_history_v1'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<PublishTask[]>([])
  const batches = ref<TaskBatch[]>([])
  const isExecuting = ref(false)
  const currentRunningBatchId = ref<string | null>(null)
  const globalLiveLogs = ref<TaskLogItem[]>([])

  // 从 localStorage 加载历史任务记录
  const loadTasksFromStorage = () => {
    try {
      const data = localStorage.getItem(STORAGE_KEY)
      if (data) {
        const parsed = JSON.parse(data)
        if (Array.isArray(parsed.tasks)) {
          tasks.value = parsed.tasks.map((t: any) => ({
            ...t,
            status: t.status === 'running' || t.status === 'queued' ? 'failed' : t.status,
            errorMsg: t.status === 'running' ? '应用重启导致任务中断' : t.errorMsg
          }))
        }
        if (Array.isArray(parsed.batches)) {
          batches.value = parsed.batches
        }
      }
    } catch (e) {
      console.error('Failed to load tasks from localStorage', e)
    }
  }

  // 保存任务记录到 localStorage (只保留最近 100 条)
  const saveTasksToStorage = () => {
    try {
      const payload = {
        tasks: tasks.value.slice(0, 100).map(t => ({
          ...t,
          logs: t.logs.slice(-50) // 每个任务保留最近50条日志
        })),
        batches: batches.value.slice(0, 30)
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch (e) {
      console.error('Failed to save tasks to localStorage', e)
    }
  }

  // 计算属性
  const queuedTasksCount = computed(() => tasks.value.filter(t => t.status === 'queued').length)
  const runningTasksCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
  const successTasksCount = computed(() => tasks.value.filter(t => t.status === 'success').length)
  const failedTasksCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)
  const activeTasksCount = computed(() => queuedTasksCount.value + runningTasksCount.value)

  // 清洗 ANSI Escape 颜色转义字符
  const cleanAnsiString = (str: string): string => {
    if (!str) return ''
    return str
      .replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
      .replace(/\r/g, '')
      .trim()
  }

  // 添加日志流并智能路由到相关任务
  const appendLog = (evt: any) => {
    const timeStr = new Date().toLocaleTimeString()
    let type = 'log'
    let rawMsg = ''

    if (typeof evt === 'string') {
      rawMsg = evt
    } else if (evt && evt.message) {
      rawMsg = evt.message
      type = evt.type || 'log'
    }

    const cleanMsg = cleanAnsiString(rawMsg)
    if (!cleanMsg) return

    const logItem: TaskLogItem = {
      time: timeStr,
      type,
      message: cleanMsg
    }

    // 全局控制台日志
    globalLiveLogs.value.push(logItem)
    if (globalLiveLogs.value.length > 500) {
      globalLiveLogs.value.shift()
    }

    // 智能尝试关联到当前正在运行的任务
    const runningTasks = tasks.value.filter(t => t.status === 'running')
    for (const t of runningTasks) {
      if (cleanMsg.toLowerCase().includes(t.platform.toLowerCase()) || 
          cleanMsg.toLowerCase().includes(t.account.toLowerCase())) {
        t.logs.push(logItem)
        break
      }
    }
  }

  // 初始化监听 Wails 后端事件
  const initEventListener = () => {
    loadTasksFromStorage()
    EventsOn('sau-log', appendLog)
  }

  // 1. 创建批次并入队 (Enqueue Batch)
  const enqueueBatch = (params: {
    batchName: string
    rawTasks: engine.AccountPublishTask[]
    concurrency: number
  }) => {
    const batchId = 'batch-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7)
    const nowStr = new Date().toLocaleString()

    const newBatch: TaskBatch = {
      id: batchId,
      name: params.batchName || `矩阵发布批次 ${nowStr}`,
      createdAt: nowStr,
      totalTasks: params.rawTasks.length,
      completedTasks: 0,
      failedTasks: 0,
      status: 'queued',
      concurrency: params.concurrency
    }

    batches.value.unshift(newBatch)

    const newTasks: PublishTask[] = params.rawTasks.map((raw, idx) => ({
      id: `task-${Date.now()}-${idx}-${Math.random().toString(36).substring(2, 6)}`,
      batchId,
      batchName: newBatch.name,
      platform: raw.platform,
      account: raw.account,
      nickname: raw.nickname || raw.account,
      title: raw.title,
      action: (raw.action as 'upload-video' | 'upload-note') || 'upload-video',
      status: 'queued',
      priority: 'normal',
      progress: 0,
      createdAt: nowStr,
      logs: [],
      params: raw
    }))

    // 放入任务队列头部或尾部
    tasks.value = [...newTasks, ...tasks.value]
    saveTasksToStorage()

    // 触发调度执行
    triggerQueueExecution()

    return batchId
  }

  // 2. 调度执行队列中的任务
  const triggerQueueExecution = async () => {
    if (isExecuting.value) return

    // 寻找处于 queued 状态的任务
    const nextQueuedTasks = tasks.value.filter(t => t.status === 'queued')
    if (nextQueuedTasks.length === 0) return

    // 按批次或按优先级聚合出当前批次任务
    const currentBatchId = nextQueuedTasks[0].batchId
    const currentBatch = batches.value.find(b => b.id === currentBatchId)
    const batchTasks = nextQueuedTasks.filter(t => t.batchId === currentBatchId)

    if (batchTasks.length === 0) return

    isExecuting.value = true
    currentRunningBatchId.value = currentBatchId
    if (currentBatch) {
      currentBatch.status = 'running'
    }

    // 更新任务状态为 running
    const startTimestamp = Date.now()
    batchTasks.forEach(t => {
      t.status = 'running'
      t.startedAt = new Date().toLocaleTimeString()
      t.progress = 20
    })

    try {
      const concurrency = currentBatch?.concurrency || 3
      const rawPayload = engine.MatrixPublishParam.createFrom({
        concurrency: concurrency,
        tasks: batchTasks.map(t => t.params)
      })

      const results = await MatrixPublishMedia(rawPayload)

      // 解析结果
      if (results && Array.isArray(results)) {
        results.forEach((res: engine.AccountPublishResult) => {
          const matchedTask = batchTasks.find(t => t.platform === res.platform && t.account === res.account)
          if (matchedTask) {
            matchedTask.status = res.success ? 'success' : 'failed'
            matchedTask.completedAt = new Date().toLocaleTimeString()
            matchedTask.duration = Math.round((Date.now() - startTimestamp) / 1000)
            matchedTask.progress = 100
            matchedTask.errorMsg = res.errorMsg || ''

            if (currentBatch) {
              if (res.success) {
                currentBatch.completedTasks++
              } else {
                currentBatch.failedTasks++
              }
            }
          }
        })
      }

      if (currentBatch) {
        if (currentBatch.failedTasks === 0) {
          currentBatch.status = 'completed'
        } else if (currentBatch.completedTasks === 0) {
          currentBatch.status = 'partial'
        } else {
          currentBatch.status = 'partial'
        }
      }
    } catch (err: any) {
      batchTasks.forEach(t => {
        if (t.status === 'running') {
          t.status = 'failed'
          t.errorMsg = err.message || String(err)
          t.completedAt = new Date().toLocaleTimeString()
          t.duration = Math.round((Date.now() - startTimestamp) / 1000)
        }
      })
      if (currentBatch) {
        currentBatch.status = 'partial'
      }
    } finally {
      isExecuting.value = false
      currentRunningBatchId.value = null
      saveTasksToStorage()

      // 继续检查是否有下一批排队任务
      setTimeout(() => {
        triggerQueueExecution()
      }, 500)
    }
  }

  // 3. 中止任务 / 批次
  const cancelActiveTask = async (taskId?: string) => {
    await StopActivePublish()
    if (taskId) {
      const found = tasks.value.find(t => t.id === taskId)
      if (found && (found.status === 'running' || found.status === 'queued')) {
        found.status = 'cancelled'
        found.errorMsg = '用户手动取消'
      }
    } else {
      tasks.value.forEach(t => {
        if (t.status === 'running' || t.status === 'queued') {
          t.status = 'cancelled'
          t.errorMsg = '用户手动终止'
        }
      })
    }
    isExecuting.value = false
    currentRunningBatchId.value = null
    saveTasksToStorage()
  }

  // 4. 重试单个任务
  const retryTask = (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (!task) return
    task.status = 'queued'
    task.errorMsg = ''
    task.progress = 0
    task.logs = []
    saveTasksToStorage()
    triggerQueueExecution()
  }

  // 5. 调整优先级
  const changePriority = (taskId: string, priority: TaskPriority) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.priority = priority
      saveTasksToStorage()
    }
  }

  // 6. 清理已完成/失败任务
  const clearFinishedTasks = () => {
    tasks.value = tasks.value.filter(t => t.status === 'running' || t.status === 'queued')
    saveTasksToStorage()
  }

  // 7. 清理全部任务与日志
  const clearAllTasks = () => {
    tasks.value = []
    batches.value = []
    globalLiveLogs.value = []
    saveTasksToStorage()
  }

  return {
    tasks,
    batches,
    isExecuting,
    currentRunningBatchId,
    globalLiveLogs,
    queuedTasksCount,
    runningTasksCount,
    successTasksCount,
    failedTasksCount,
    activeTasksCount,
    initEventListener,
    enqueueBatch,
    cancelActiveTask,
    retryTask,
    changePriority,
    clearFinishedTasks,
    clearAllTasks
  }
})
