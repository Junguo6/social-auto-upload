import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { PipelinePublishMedia, StopActivePublish, StopSingleTask, StopTaskById, ResumeAccount, GetAccountRiskStatus, GetRiskOverview } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'
import { engine } from '../../wailsjs/go/models'
import { useSettingsStore } from './settingsStore'
import type { PublishTask, TaskBatch, TaskStatus, TaskLogItem, TaskLane, RiskState } from '../types/task'

const STORAGE_KEY = 'sau_task_workflow_v8'

export const useTaskStore = defineStore('task', () => {
  const settingsStore = useSettingsStore()

  const tasks = ref<PublishTask[]>([])
  const batches = ref<TaskBatch[]>([])
  const lanes = ref<TaskLane[]>([])
  const isExecuting = ref(false)
  const currentRunningBatchId = ref<string | null>(null)
  const globalLiveLogs = ref<TaskLogItem[]>([])

  // 当前最新提交的批次 ID (用于视觉高亮发光与快速过滤)
  const latestBatchId = ref<string | null>(null)
  // 当前选中的批次过滤器 ('all' | batchId)
  const selectedBatchFilter = ref<string>('all')

  // 全局硬件/系统设置最大并发通道数限制 (来自系统设置，默认 3，最大 5)
  const maxConcurrency = computed(() => {
    return Math.min(5, Math.max(1, settingsStore.settings.concurrency || 3))
  })

  // 是否允许继续新增线程通道
  const canAddLane = computed(() => {
    return lanes.value.length < maxConcurrency.value
  })

  // 辅助函数：精准刷新单个泳道的状态
  const syncLaneStatus = (lane: TaskLane) => {
    if (!lane.tasks || lane.tasks.length === 0) {
      lane.status = 'idle'
      return
    }
    const anyRunning = lane.tasks.some(t => t.status === 'running')
    if (anyRunning) {
      lane.status = 'running'
      return
    }
    const anyQueued = lane.tasks.some(t => t.status === 'queued')
    if (anyQueued) {
      lane.status = isExecuting.value ? 'running' : 'idle'
      return
    }
    const allSuccess = lane.tasks.every(t => t.status === 'success')
    if (allSuccess) {
      lane.status = 'completed'
      return
    }
    const anyFailed = lane.tasks.some(t => t.status === 'failed')
    if (anyFailed) {
      lane.status = 'failed'
      return
    }
    lane.status = 'idle'
  }

  // 辅助函数：刷新所有泳道状态
  const refreshAllLanesStatus = () => {
    lanes.value.forEach(l => syncLaneStatus(l))
  }

  // 从 localStorage 加载历史记录
  const loadTasksFromStorage = () => {
    try {
      const data = localStorage.getItem(STORAGE_KEY)
      if (data) {
        const parsed = JSON.parse(data)
        if (Array.isArray(parsed.tasks)) {
          tasks.value = parsed.tasks.map((t: any, idx: number) => ({
            ...t,
            orderIndex: t.orderIndex ?? idx + 1,
            status: t.status === 'running' ? 'failed' : t.status,
            errorMsg: t.status === 'running' ? '应用重启导致任务中断' : t.errorMsg
          }))
        }
        if (Array.isArray(parsed.batches)) {
          batches.value = parsed.batches
        }
        if (Array.isArray(parsed.lanes) && parsed.lanes.length > 0) {
          lanes.value = parsed.lanes.slice(0, maxConcurrency.value)
        }
      }
    } catch (e) {
      console.error('Failed to load workflow tasks from storage', e)
    }

    // 默认初始化 lanes 数量 (不超过系统设置并发上限)
    if (lanes.value.length === 0) {
      const initCount = Math.min(2, maxConcurrency.value)
      const initialLanes: TaskLane[] = []
      for (let i = 0; i < initCount; i++) {
        initialLanes.push({
          id: `lane-${i + 1}`,
          name: `线程通道 ${i + 1}`,
          status: 'idle',
          delayBetweenTasks: 15,
          tasks: []
        })
      }
      lanes.value = initialLanes
    }

    refreshAllLanesStatus()
  }

  // 保存任务记录到 localStorage
  const saveTasksToStorage = () => {
    try {
      const payload = {
        tasks: tasks.value.slice(0, 100).map(t => ({
          ...t,
          logs: t.logs.slice(-50)
        })),
        batches: batches.value.slice(0, 30),
        lanes: lanes.value.map(l => ({
          ...l,
          tasks: l.tasks.slice(0, 30)
        }))
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch (e) {
      console.error('Failed to save tasks to storage', e)
    }
  }

  // 计算属性
  const queuedTasksCount = computed(() => tasks.value.filter(t => t.status === 'queued').length)
  const runningTasksCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
  const successTasksCount = computed(() => tasks.value.filter(t => t.status === 'success').length)
  const failedTasksCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)
  const activeTasksCount = computed(() => queuedTasksCount.value + runningTasksCount.value)

  // 待分配任务池 (凡是不在任何泳道中的任务都完整保留在此，杜绝任何任务卡片丢失)
  const unassignedTasks = computed(() => {
    const laneTaskIds = new Set<string>()
    lanes.value.forEach(l => l.tasks.forEach(t => laneTaskIds.add(t.id)))
    return tasks.value.filter(t => !laneTaskIds.has(t.id))
  })

  // 检测是否存在跨通道同平台并发风控隐患 (例如 2 个抖音账号在不同线程同时跑)
  const platformConflicts = computed(() => {
    const platformToLaneMap: Record<string, Set<string>> = {}
    lanes.value.forEach(lane => {
      lane.tasks.forEach(t => {
        if (t.status === 'queued' || t.status === 'running') {
          if (!platformToLaneMap[t.platform]) {
            platformToLaneMap[t.platform] = new Set()
          }
          platformToLaneMap[t.platform].add(lane.id)
        }
      })
    })

    const conflicts: string[] = []
    Object.keys(platformToLaneMap).forEach(plat => {
      if (platformToLaneMap[plat].size > 1) {
        conflicts.push(plat)
      }
    })
    return conflicts
  })

  // 清洗 ANSI Escape 颜色转义字符
  const cleanAnsiString = (str: string): string => {
    if (!str) return ''
    return str
      .replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
      .replace(/\r/g, '')
      .trim()
  }

  // 接收并智能路由引擎事件与日志 (结构化推进任务状态机)
  const appendLog = (evt: any) => {
    const timeStr = new Date().toLocaleTimeString()
    let type = 'log'
    let rawMsg = ''
    let plat = ''
    let acc = ''

    if (typeof evt === 'string') {
      rawMsg = evt
    } else if (evt) {
      rawMsg = evt.message || ''
      type = evt.type || 'log'
      plat = evt.platform || ''
      acc = evt.account || ''
    }

    const cleanMsg = cleanAnsiString(rawMsg)
    if (!cleanMsg && !plat) return

    const logItem: TaskLogItem = { time: timeStr, type, message: cleanMsg }
    globalLiveLogs.value.push(logItem)
    if (globalLiveLogs.value.length > 500) {
      globalLiveLogs.value.shift()
    }

    // 1. 结构化事件精准推进任务状态 (优先匹配 TaskId)
    if (evt.taskId || (plat && acc)) {
      let targetTask = evt.taskId ? tasks.value.find(t => t.id === evt.taskId) : null
      if (!targetTask && plat && acc) {
        targetTask = tasks.value.find(t => t.platform === plat && t.account === acc && t.status !== 'success')
      }
      if (targetTask) {
        targetTask.logs.push(logItem)

        if (type === 'task_start') {
          targetTask.status = 'running'
          targetTask.startedAt = timeStr
          targetTask.progress = 30
          refreshAllLanesStatus()
        } else if (type === 'task_success') {
          targetTask.status = 'success'
          targetTask.completedAt = timeStr
          targetTask.completedAtTimestamp = Date.now()
          targetTask.progress = 100
          targetTask.errorMsg = ''
          refreshAllLanesStatus()
        } else if (type === 'task_error') {
          targetTask.status = 'failed'
          targetTask.completedAt = timeStr
          targetTask.completedAtTimestamp = Date.now()
          targetTask.errorMsg = cleanMsg
          refreshAllLanesStatus()
        } else if (type === 'risk_alert') {
          targetTask.status = 'failed'
          targetTask.isPaused = true
          targetTask.pauseReason = cleanMsg
          targetTask.errorMsg = cleanMsg
          ElNotification({
            title: '⚠️ 触发账号安全熔断',
            message: cleanMsg,
            type: 'warning',
            duration: 9000
          })
          refreshAllLanesStatus()
        }
        return
      }
    }

    // 2. 普通文本日志智能关联到运行中的任务
    const allRunning = tasks.value.filter(t => t.status === 'running')
    for (const t of allRunning) {
      if (cleanMsg.toLowerCase().includes(t.platform.toLowerCase()) || 
          cleanMsg.toLowerCase().includes(t.account.toLowerCase())) {
        t.logs.push(logItem)
        break
      }
    }
  }

  const initEventListener = () => {
    loadTasksFromStorage()
    EventsOn('sau-log', appendLog)
  }

  // 1. 创建批次并自动装载进线程泳道 (智能防风控追加，绝不丢弃或错排现有任务)
  const enqueueBatch = (params: {
    batchName: string
    videoFileName?: string
    thumbnail?: string
    rawTasks: engine.AccountPublishTask[]
    concurrency: number
  }) => {
    const batchId = 'batch-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7)
    const nowStr = new Date().toLocaleString()

    const effectiveConcurrency = Math.min(params.concurrency || 3, maxConcurrency.value)

    const newBatch: TaskBatch = {
      id: batchId,
      name: params.batchName || `矩阵发布批次 ${nowStr}`,
      videoFileName: params.videoFileName || '',
      createdAt: nowStr,
      totalTasks: params.rawTasks.length,
      completedTasks: 0,
      failedTasks: 0,
      status: 'queued',
      concurrency: effectiveConcurrency,
      executionMode: 'parallel'
    }
    batches.value.unshift(newBatch)

    // 设置为最新激活批次
    latestBatchId.value = batchId

    const newTasks: PublishTask[] = params.rawTasks.map((raw, idx) => {
      const taskId = `task-${Date.now()}-${idx}-${Math.random().toString(36).substring(2, 6)}`
      raw.taskId = taskId
      return {
        id: taskId,
        batchId,
        batchName: newBatch.name,
        videoFileName: params.videoFileName || '',
        thumbnail: params.thumbnail || raw.thumbnail || '',
        platform: raw.platform,
        account: raw.account,
        nickname: raw.nickname || raw.account,
        title: raw.title,
        action: (raw.action as 'upload-video' | 'upload-note') || 'upload-video',
        status: 'queued',
        priority: 'normal',
        progress: 0,
        orderIndex: idx + 1,
        delaySeconds: 15,
        createdAt: nowStr,
        logs: [],
        params: raw
      }
    })

    tasks.value = [...tasks.value, ...newTasks]

    // 智能将新任务追加装载到现有泳道中 (同平台追加到同通道尾部，新平台分配到空闲通道)
    distributeNewBatchIntoLanes(newTasks, effectiveConcurrency)
    refreshAllLanesStatus()
    saveTasksToStorage()

    // 启动多协程泳道调度 (如果当前正空闲或刚完成，立即触发执行)
    triggerMultiLaneExecution()

    return batchId
  }

  // 内部辅助：将新创建的批次智能追加到泳道末尾 (平滑追加，绝不把正在执行的任务重置或打乱)
  const distributeNewBatchIntoLanes = (newTasks: PublishTask[], concurrency: number) => {
    // 1. 确保已有足够的泳道
    const targetLaneCount = Math.max(lanes.value.length, Math.min(concurrency, maxConcurrency.value))
    while (lanes.value.length < targetLaneCount) {
      const idx = lanes.value.length + 1
      lanes.value.push({
        id: `lane-${Date.now()}-${idx}`,
        name: `线程通道 ${idx}`,
        status: 'idle',
        delayBetweenTasks: 15,
        tasks: []
      })
    }

    // 2. 按平台对新任务分组
    const platMap: Record<string, PublishTask[]> = {}
    newTasks.forEach(t => {
      if (!platMap[t.platform]) platMap[t.platform] = []
      platMap[t.platform].push(t)
    })

    // 3. 为每个平台寻找最佳泳道 (优先寻找已有该平台任务的泳道；其次选任务数最少的泳道)
    Object.keys(platMap).forEach(plat => {
      const platTasks = platMap[plat]
      
      // 寻找已有同平台的泳道
      let matchedLane = lanes.value.find(l => l.tasks.some(t => t.platform === plat))
      if (!matchedLane) {
        // 寻找当前任务数最少的泳道
        let minCount = Infinity
        lanes.value.forEach(l => {
          if (l.tasks.length < minCount) {
            minCount = l.tasks.length
            matchedLane = l
          }
        })
      }

      if (!matchedLane && lanes.value.length > 0) {
        matchedLane = lanes.value[0]
      }

      if (matchedLane) {
        platTasks.forEach(t => {
          t.laneId = matchedLane!.id
          t.delaySeconds = matchedLane!.delayBetweenTasks || 15
          t.orderIndex = matchedLane!.tasks.length + 1
          matchedLane!.tasks.push(t)
        })
      }
    })
  }

  // 2. 智能防风控全量任务均分器 (按平台智能隔离 + 执行中任务严格置顶排在第1位)
  const autoDistributeTasksToLanes = (taskItems?: PublishTask[], targetLaneCount?: number) => {
    // 待排布任务池：当前所有非成功任务
    const pool = taskItems || tasks.value.filter(t => t.status !== 'success')
    if (pool.length === 0) return

    // 1. 按平台对任务进行聚类分组
    const platformMap: Record<string, PublishTask[]> = {}
    pool.forEach(t => {
      if (!platformMap[t.platform]) platformMap[t.platform] = []
      platformMap[t.platform].push(t)
    })
    const distinctPlatforms = Object.keys(platformMap)

    // 2. 计算最佳并发泳道数 (受 maxConcurrency 约束)
    let laneCount = targetLaneCount || Math.min(distinctPlatforms.length, maxConcurrency.value)
    laneCount = Math.min(laneCount, maxConcurrency.value)
    laneCount = Math.max(1, laneCount)

    // 3. 构建全新线程通道
    const newLanes: TaskLane[] = []
    for (let i = 0; i < laneCount; i++) {
      newLanes.push({
        id: `lane-${i + 1}`,
        name: `线程通道 ${i + 1}`,
        status: 'idle',
        delayBetweenTasks: 15,
        tasks: []
      })
    }

    // 4. 将同平台的任务群分配到同一个泳道内部串行排队
    // 状态排序权重：running (0) 严格置顶第一位 -> queued (1) -> cancelled (2) -> failed (3)
    const getStatusPriority = (s: TaskStatus) => {
      switch (s) {
        case 'running': return 0
        case 'queued': return 1
        case 'cancelled': return 2
        case 'failed': return 3
        default: return 4
      }
    }

    distinctPlatforms.forEach((plat, platIdx) => {
      const targetLane = newLanes[platIdx % laneCount]
      const platTasks = platformMap[plat]

      // 严格排序：正在执行中的任务永远排在排队任务之前！
      platTasks.sort((a, b) => getStatusPriority(a.status) - getStatusPriority(b.status))

      platTasks.forEach((t) => {
        t.laneId = targetLane.id
        t.delaySeconds = 15
        t.orderIndex = targetLane.tasks.length + 1
        targetLane.tasks.push(t)
      })
    })

    lanes.value = newLanes
    refreshAllLanesStatus()
    saveTasksToStorage()
  }

  // 3. 泳道管理：新增线程通道 (上限保护)
  const addLane = () => {
    if (!canAddLane.value) {
      ElMessage.warning(`已达到系统设置的最大并发限制 (${maxConcurrency.value} 个线程)，如需增加请前往「系统设置」调整`)
      return
    }
    const nextIdx = lanes.value.length + 1
    lanes.value.push({
      id: `lane-${Date.now()}`,
      name: `线程通道 ${nextIdx}`,
      status: 'idle',
      delayBetweenTasks: 15,
      tasks: []
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
    ElMessage.success(`已添加「线程通道 ${nextIdx}」`)
  }

  // 4. 泳道管理：移除线程通道 (通道内任务退回未分配池)
  const removeLane = (laneId: string) => {
    if (lanes.value.length <= 1) {
      ElMessage.info('至少需要保留 1 个执行线程通道')
      return
    }
    const idx = lanes.value.findIndex(l => l.id === laneId)
    if (idx >= 0) {
      const removed = lanes.value.splice(idx, 1)[0]
      removed.tasks.forEach(t => {
        t.laneId = undefined
      })
      refreshAllLanesStatus()
      saveTasksToStorage()
      ElMessage.info(`已移除「${removed.name}」，其任务已归还至待分配池`)
    }
  }

  // 5. 跨泳道移动与卡片重排 (Move Task Between / Inside Lanes)
  const moveTask = (params: {
    taskId: string
    fromLaneId: string | null
    toLaneId: string | null
    newIndex: number
  }) => {
    const { taskId, fromLaneId, toLaneId, newIndex } = params
    const task = tasks.value.find(t => t.id === taskId)
    if (!task) return

    // 1. 从源泳道移除
    if (fromLaneId) {
      const sourceLane = lanes.value.find(l => l.id === fromLaneId)
      if (sourceLane) {
        sourceLane.tasks = sourceLane.tasks.filter(t => t.id !== taskId)
        syncLaneStatus(sourceLane)
      }
    }

    // 2. 插入目标泳道
    if (toLaneId) {
      const targetLane = lanes.value.find(l => l.id === toLaneId)
      if (targetLane) {
        task.laneId = toLaneId
        targetLane.tasks.splice(newIndex, 0, task)
        // 刷新 orderIndex
        targetLane.tasks.forEach((t, i) => {
          t.orderIndex = i + 1
        })
        syncLaneStatus(targetLane)
      }
    } else {
      task.laneId = undefined
    }

    refreshAllLanesStatus()
    saveTasksToStorage()
  }

  // 6. 执行多协程泳道任务流调度 (Go Goroutine per lane)
  const triggerMultiLaneExecution = async () => {
    if (isExecuting.value) return

    // 检查是否有排队中或运行中的任务
    const activeLanesWithTasks = lanes.value.filter(l => l.tasks.some(t => t.status === 'queued' || t.status === 'running'))
    if (activeLanesWithTasks.length === 0) return

    isExecuting.value = true

    // 设置泳道运行状态 (每个通道只让第 1 个待发任务就绪)
    lanes.value.forEach(l => {
      const hasPending = l.tasks.some(t => t.status === 'queued' || t.status === 'running')
      if (hasPending) {
        l.status = 'running'
      }
    })

    try {
      // 组装 Go 契约结构体 PipelinePublishParam (只下发未完成的任务，并根据前序任务完成时间计算前置防风控延时)
      const goParam = engine.PipelinePublishParam.createFrom({
        lanes: activeLanesWithTasks.map(l => {
          const pendingTasks = l.tasks.filter(t => t.status === 'queued' || t.status === 'running')

          return {
            laneId: l.id,
            laneName: l.name,
            tasks: pendingTasks.map((t, pIdx) => {
              let initialDelaySeconds = 0
              // 如果是通道内第 1 个待发任务，检查其前序任务是否刚刚完成 (计算剩余防风控安全延时)
              if (pIdx === 0) {
                const taskIdxInLane = l.tasks.findIndex(item => item.id === t.id)
                if (taskIdxInLane > 0) {
                  const prevTask = l.tasks[taskIdxInLane - 1]
                  if (prevTask && prevTask.status === 'success') {
                    const requiredDelay = (prevTask.delaySeconds !== undefined && prevTask.delaySeconds >= 0)
                      ? prevTask.delaySeconds 
                      : (l.delayBetweenTasks ?? 15)
                    if (prevTask.completedAtTimestamp) {
                      const elapsed = Math.floor((Date.now() - prevTask.completedAtTimestamp) / 1000)
                      initialDelaySeconds = Math.max(0, requiredDelay - elapsed)
                    } else {
                      initialDelaySeconds = requiredDelay
                    }
                  }
                }
              }

              return {
                ...t.params,
                taskId: t.id,
                initialDelaySeconds,
                delaySeconds: (t.delaySeconds !== undefined && t.delaySeconds >= 0) ? t.delaySeconds : (l.delayBetweenTasks ?? 15)
              }
            }),
            delayBetweenTasks: l.delayBetweenTasks ?? 15,
            scheduledAt: l.scheduledAt || ''
          }
        })
      })

      const results = await PipelinePublishMedia(goParam)

      // 解析每个账号的发布结果 (优先根据 TaskId 精准匹配)
      if (results && Array.isArray(results)) {
        results.forEach((res: engine.AccountPublishResult) => {
          let matched = res.taskId ? tasks.value.find(t => t.id === res.taskId) : null
          if (!matched) {
            matched = tasks.value.find(t => t.platform === res.platform && t.account === res.account && t.status !== 'success')
          }
          if (matched && matched.status !== 'success') {
            matched.status = res.success ? 'success' : 'failed'
            matched.completedAt = new Date().toLocaleTimeString()
            matched.completedAtTimestamp = Date.now()
            matched.progress = 100
            matched.errorMsg = res.errorMsg || ''
          }
        })
      }

      refreshAllLanesStatus()
    } catch (err: any) {
      lanes.value.forEach(l => {
        l.status = 'failed'
        l.tasks.forEach(t => {
          if (t.status === 'running') {
            t.status = 'failed'
            t.errorMsg = err.message || String(err)
            t.completedAt = new Date().toLocaleTimeString()
            t.completedAtTimestamp = Date.now()
          }
        })
      })
    } finally {
      isExecuting.value = false
      refreshAllLanesStatus()
      saveTasksToStorage()

      // 自驱动队列保护：如果在执行过程中有新任务追加排队，300ms 后自动拉起下一轮调度执行！
      const hasRemainingQueued = lanes.value.some(l => l.tasks.some(t => t.status === 'queued'))
      if (hasRemainingQueued) {
        setTimeout(() => {
          triggerMultiLaneExecution()
        }, 300)
      }
    }
  }

  // 7. 中止工作流全部任务
  const cancelWorkflow = async () => {
    await StopActivePublish()
    isExecuting.value = false
    lanes.value.forEach(l => {
      l.status = 'idle'
      l.tasks.forEach(t => {
        if (t.status === 'running' || t.status === 'queued') {
          t.status = 'cancelled'
          t.errorMsg = '用户手动终止'
        }
      })
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
  }

  // 7.1 中止单个执行中任务 (优先通过 TaskId 精准杀死进程，通道后续任务自动继续执行)
  const cancelTask = async (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (!task) return

    if (task.status === 'running') {
      try {
        await StopTaskById(taskId)
      } catch (err) {
        try {
          await StopSingleTask(task.platform, task.account)
        } catch (e) {
          console.warn('StopSingleTask failed', e)
        }
      }
    }

    task.status = 'cancelled'
    task.errorMsg = '已手动中止该任务，通道后续任务将自动继续执行'

    refreshAllLanesStatus()
    saveTasksToStorage()
    ElMessage.info(`已中止任务「${task.nickname || task.account}」，通道后续任务将自动继续`)
  }

  // 8. 重试 / 恢复单个任务 (自动排布至泳道)
  const retryTask = (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (!task) return
    task.status = 'queued'
    task.errorMsg = ''
    task.progress = 0
    task.logs = []

    // 确保该任务在某个泳道内
    const inAnyLane = lanes.value.some(l => l.tasks.some(t => t.id === taskId))
    if (!inAnyLane) {
      distributeNewBatchIntoLanes([task], maxConcurrency.value)
    }

    refreshAllLanesStatus()
    saveTasksToStorage()
    triggerMultiLaneExecution()
  }

  // 9. 清理已完成
  const clearFinishedTasks = () => {
    tasks.value = tasks.value.filter(t => t.status === 'running' || t.status === 'queued')
    lanes.value.forEach(l => {
      l.tasks = l.tasks.filter(t => t.status === 'running' || t.status === 'queued')
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
  }

  // 10. 清空全部
  const clearAllTasks = () => {
    tasks.value = []
    batches.value = []
    globalLiveLogs.value = []
    latestBatchId.value = null
    selectedBatchFilter.value = 'all'
    lanes.value.forEach(l => {
      l.tasks = []
      l.status = 'idle'
    })
    saveTasksToStorage()
  }

  // 11. 更新单个任务节点的专属步骤延时 (仅影响该节点连接，绝不影响通道全局延时)
  const setTaskDelay = (taskId: string, delay: number) => {
    const safeDelay = Math.max(0, delay)
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.delaySeconds = safeDelay
      if (task.params) {
        task.params.delaySeconds = safeDelay
      }
    }
    lanes.value.forEach(l => {
      const laneTask = l.tasks.find(t => t.id === taskId)
      if (laneTask) {
        laneTask.delaySeconds = safeDelay
        if (laneTask.params) {
          laneTask.params.delaySeconds = safeDelay
        }
      }
    })
    saveTasksToStorage()
  }

  // 12. 更新通道全局默认延时 (作为该通道中未单独设置延时任务的基准默认值)
  const setLaneDelay = (laneId: string, delay: number) => {
    const lane = lanes.value.find(l => l.id === laneId)
    if (lane) {
      lane.delayBetweenTasks = Math.max(0, delay)
      saveTasksToStorage()
    }
  }

  // 13. 人工已处理，解除账号安全熔断状态并自动恢复队列
  const resumeAccountRisk = async (platform: string, account: string) => {
    try {
      await ResumeAccount(platform, account)
      tasks.value.forEach(t => {
        if (t.platform === platform && t.account === account) {
          t.isPaused = false
          t.pauseReason = ''
          if (t.status === 'failed' && (t.errorMsg?.includes('熔断') || t.errorMsg?.includes('准入'))) {
            t.status = 'queued'
            t.errorMsg = ''
          }
        }
      })
      lanes.value.forEach(l => {
        l.tasks.forEach(t => {
          if (t.platform === platform && t.account === account) {
            t.isPaused = false
            t.pauseReason = ''
            if (t.status === 'failed' && (t.errorMsg?.includes('熔断') || t.errorMsg?.includes('准入'))) {
              t.status = 'queued'
              t.errorMsg = ''
            }
          }
        })
      })
      refreshAllLanesStatus()
      saveTasksToStorage()
      ElMessage.success(`已成功解除 [${platform}:${account}] 的安全熔断，相关任务已重新排队`)
    } catch (err: any) {
      ElMessage.error(`解除熔断失败: ${err.message || err}`)
    }
  }

  return {
    tasks,
    batches,
    lanes,
    unassignedTasks,
    platformConflicts,
    maxConcurrency,
    canAddLane,
    latestBatchId,
    selectedBatchFilter,
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
    addLane,
    removeLane,
    moveTask,
    setTaskDelay,
    setLaneDelay,
    autoDistributeTasksToLanes,
    triggerMultiLaneExecution,
    cancelWorkflow,
    cancelTask,
    retryTask,
    resumeAccountRisk,
    clearFinishedTasks,
    clearAllTasks,
    saveTasksToStorage
  }
})
