import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { PipelinePublishMedia, StopActivePublish, StopSingleTask, StopTaskById, ResumeAccount, GetAccountRiskStatus, GetRiskOverview } from '../../wailsjs/go/main/App'
import { EventsOn } from '../../wailsjs/runtime/runtime'
import { engine } from '../../wailsjs/go/models'
import { useSettingsStore } from './settingsStore'
import { useAuthStore } from './authStore'
import type { PublishTask, TaskBatch, TaskStatus, TaskLogItem, TaskLane, RiskState } from '../types/task'
import { createDualStorage } from '../utils/storageAdapter'

const STORAGE_KEY = 'sau_task_workflow_v8'

interface WorkflowData {
  tasks: PublishTask[]
  batches: TaskBatch[]
  lanes: TaskLane[]
}

const taskStorage = createDualStorage<WorkflowData>({
  diskKey: 'tasks',
  localKey: STORAGE_KEY,
  getDefault: () => ({ tasks: [], batches: [], lanes: [] }),
  debounceMs: 500,
  transformSave: (data) => ({
    // 放宽到 500 条任务记录，日志保留最新 100 条
    tasks: data.tasks.slice(0, 500).map(t => ({
      ...t,
      logs: t.logs ? t.logs.slice(-100) : []
    })),
    batches: data.batches.slice(0, 100),
    lanes: data.lanes.map(l => ({
      ...l,
      tasks: l.tasks.slice(0, 100)
    }))
  })
})

export const useTaskStore = defineStore('task', () => {
  const settingsStore = useSettingsStore()

  const tasks = ref<PublishTask[]>([])
  const batches = ref<TaskBatch[]>([])
  const lanes = ref<TaskLane[]>([])
  const isExecuting = ref(false)
  /** 本次执行的开始时刻（毫秒时间戳）；0 表示当前未执行 */
  const executionStartedAt = ref<number>(0)
  const currentRunningBatchId = ref<string | null>(null)
  const globalLiveLogs = ref<TaskLogItem[]>([])

  // ============ 计划执行队列（多计划逐个串行执行）============
  /** 待执行的计划队列（batchId 列表，按数组顺序依次执行） */
  const pendingPlanQueue = ref<string[]>([])
  /** 当前正在执行的计划（空 = 未指定，走"执行全部待发任务"的老行为） */
  const activePlanId = ref<string>('')

  /** 某个计划是否还有待执行/执行中的任务 */
  const planHasPending = (planId: string) =>
    tasks.value.some(t => t.batchId === planId && (t.status === 'queued' || t.status === 'running'))

  /** 设置执行队列（左侧多选计划后由 UI 调用） */
  const setPlanQueue = (batchIds: string[]) => {
    pendingPlanQueue.value = [...batchIds]
  }

  /** Tab 关闭：从队列移除一个计划（不影响正在执行的那个） */
  const removeFromPlanQueue = (batchId: string) => {
    pendingPlanQueue.value = pendingPlanQueue.value.filter(id => id !== batchId)
    if (activePlanId.value === batchId && !isExecuting.value) {
      activePlanId.value = pendingPlanQueue.value[0] || ''
    }
  }

  /** 启动队列：从第一个开始执行 */
  const startPlanQueue = () => {
    if (isExecuting.value) return
    if (pendingPlanQueue.value.length === 0) {
      ElMessage.info('没有待执行的计划')
      return
    }
    activePlanId.value = pendingPlanQueue.value[0]
    triggerMultiLaneExecution()
  }

  /** 当前计划跑完后，推进到下一个 */
  const advancePlanQueue = () => {
    pendingPlanQueue.value = pendingPlanQueue.value.filter(id => id !== activePlanId.value)
    if (pendingPlanQueue.value.length > 0) {
      activePlanId.value = pendingPlanQueue.value[0]
      setTimeout(() => { triggerMultiLaneExecution() }, 1000)
    } else {
      activePlanId.value = ''
      ElMessage.success('所有计划已执行完毕')
    }
  }

  // 当前最新提交的批次 ID (用于视觉高亮发光与快速过滤)
  const latestBatchId = ref<string | null>(null)
  // 当前选中的批次过滤器 ('all' | batchId)
  const selectedBatchFilter = ref<string>('all')

  // 全局硬件/系统设置最大并发通道数限制 (来自系统设置，默认 1，最大 5)
  const maxConcurrency = computed(() => {
    return Math.min(5, Math.max(1, settingsStore.settings.concurrency || 1))
  })

  // 是否允许继续新增发布通道
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

  // 辅助函数：解析恢复任务流数据并建立引用映射
  const applyParsedWorkflowData = (parsed: any) => {
    if (!parsed || typeof parsed !== 'object') return
    const taskMap = new Map<string, PublishTask>()

    if (Array.isArray(parsed.tasks)) {
      tasks.value = parsed.tasks.map((t: any, idx: number) => {
        const item: PublishTask = {
          ...t,
          orderIndex: t.orderIndex ?? idx + 1,
          status: t.status === 'running' ? 'failed' : t.status,
          errorMsg: t.status === 'running' ? '应用重启导致任务中断' : t.errorMsg
        }
        taskMap.set(item.id, item)
        return item
      })
    }
    if (Array.isArray(parsed.batches)) {
      batches.value = parsed.batches
    }
    if (Array.isArray(parsed.lanes) && parsed.lanes.length > 0) {
      lanes.value = parsed.lanes.slice(0, maxConcurrency.value).map((l: any) => ({
        ...l,
        tasks: Array.isArray(l.tasks) ? l.tasks.map((t: any) => {
          if (taskMap.has(t.id)) {
            return taskMap.get(t.id)!
          }
          const restored: PublishTask = {
            ...t,
            status: t.status === 'running' ? 'failed' : t.status,
            errorMsg: t.status === 'running' ? '应用重启导致任务中断' : t.errorMsg
          }
          taskMap.set(restored.id, restored)
          tasks.value.push(restored)
          return restored
        }) : []
      }))
    }
  }

  // 加载历史记录 (本地热缓存 + 后端磁盘双驱动同步)
  const loadTasksFromStorage = async () => {
    // 1. 同步加载首屏热缓存
    applyParsedWorkflowData(taskStorage.get())

    // 2. 异步与物理磁盘对齐并平滑冷迁移
    await taskStorage.load((synced) => {
      applyParsedWorkflowData(synced)
      refreshAllLanesStatus()
    })

    // 默认初始化 lanes 数量 (不超过系统设置并发上限)
    if (lanes.value.length === 0) {
      const initCount = Math.min(2, maxConcurrency.value)
      const initialLanes: TaskLane[] = []
      for (let i = 0; i < initCount; i++) {
        initialLanes.push({
          id: `lane-${i + 1}`,
          name: `发布通道 ${i + 1}`,
          status: 'idle',
          delayBetweenTasks: 15,
          tasks: []
        })
      }
      lanes.value = initialLanes
    }

    refreshAllLanesStatus()
  }

  // 保存任务记录 (内存即时生效，物理磁盘 500ms 防抖落盘)
  const saveTasksToStorage = () => {
    taskStorage.save({
      tasks: tasks.value,
      batches: batches.value,
      lanes: lanes.value
    })
  }

  // 计算属性
  const queuedTasksCount = computed(() => tasks.value.filter(t => t.status === 'queued').length)
  const runningTasksCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
  const successTasksCount = computed(() => tasks.value.filter(t => t.status === 'success').length)
  const failedTasksCount = computed(() => tasks.value.filter(t => t.status === 'failed').length)

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

  // 统一穿透更新任务状态 (同时更新 tasks.value 与各泳道中的所有实例引用)
  const syncUpdateTask = (
    predicate: (t: PublishTask) => boolean,
    updater: (t: PublishTask) => void
  ): boolean => {
    let matched = false
    const seen = new Set<PublishTask>()
    tasks.value.forEach(t => {
      if (predicate(t) && !seen.has(t)) {
        seen.add(t)
        updater(t)
        matched = true
      }
    })
    lanes.value.forEach(l => {
      l.tasks.forEach(t => {
        if (predicate(t) && !seen.has(t)) {
          seen.add(t)
          updater(t)
          matched = true
        }
      })
    })
    return matched
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

    // 1. 结构化事件精准推进任务状态 (严格遵循单一主键 TaskId 绑定)
    if (evt.taskId || (plat && acc)) {
      let matchedTask: PublishTask | null = null

      if (evt.taskId) {
        // 严格主键匹配：通过 TaskId 精准锁定任务，杜绝同通道同账号卡片串门连带误报成功
        matchedTask = tasks.value.find(t => t.id === evt.taskId) || null
        if (!matchedTask) {
          for (const l of lanes.value) {
            matchedTask = l.tasks.find(t => t.id === evt.taskId) || null
            if (matchedTask) break
          }
        }
      } else if (plat && acc) {
        // 兜底无 TaskId 时：绝对只匹配当前正在执行中 (status === 'running') 的任务，严禁碰排队中 (queued) 任务！
        matchedTask = tasks.value.find(t => t.platform === plat && t.account === acc && t.status === 'running') || null
        if (!matchedTask) {
          for (const l of lanes.value) {
            matchedTask = l.tasks.find(t => t.platform === plat && t.account === acc && t.status === 'running') || null
            if (matchedTask) break
          }
        }
      }

      if (matchedTask) {
        const targetId = matchedTask.id
        const isAuthOrLoginIssue = cleanMsg.includes('未登录') || cleanMsg.includes('登录失效') || 
                                   cleanMsg.includes('Cookie已失效') || cleanMsg.includes('cookie 已失效') ||
                                   cleanMsg.includes('扫码登录') || cleanMsg.includes('登录已过期')

        const updated = syncUpdateTask(t => t.id === targetId, (targetTask) => {
          targetTask.logs.push(logItem)

          if (type === 'task_start') {
            targetTask.status = 'running'
            targetTask.startedAt = timeStr
            targetTask.progress = 30
          } else if (type === 'task_success') {
            targetTask.status = 'success'
            targetTask.completedAt = timeStr
            targetTask.completedAtTimestamp = Date.now()
            targetTask.progress = 100
            targetTask.errorMsg = ''
          } else if (type === 'task_error') {
            targetTask.status = 'failed'
            targetTask.completedAt = timeStr
            targetTask.completedAtTimestamp = Date.now()
            targetTask.errorMsg = cleanMsg
            if (isAuthOrLoginIssue) {
              targetTask.isPaused = true
              targetTask.pauseReason = '账号未登录或凭证失效，请在账号管理中重新登录后点击恢复'
            }
          } else if (type === 'risk_alert') {
            targetTask.status = 'failed'
            targetTask.isPaused = true
            targetTask.pauseReason = cleanMsg
            targetTask.errorMsg = cleanMsg
          }
        })

        // 若当前任务因未登录而失败，自动保护暂停同账号后续在排队的任务，防止无意义的连续尝试
        if (isAuthOrLoginIssue && matchedTask.platform && matchedTask.account) {
          const authPlat = matchedTask.platform
          const authAcc = matchedTask.account
          syncUpdateTask(
            t => t.id !== targetId && t.platform === authPlat && t.account === authAcc && t.status === 'queued',
            t => {
              t.isPaused = true
              t.pauseReason = '账号未登录或凭证失效，已自动暂停排队，请在账号管理登录后重试'
            }
          )
        }

        if (updated) {
          if (type === 'risk_alert') {
            ElNotification({
              title: '⚠️ 账号已自动保护暂停',
              message: cleanMsg,
              type: 'warning',
              duration: 9000
            })
          }
          refreshAllLanesStatus()
          return
        }
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
    /** filePath → 目录层级的映射（用于任务中心按层级分组） */
    crumbsMap?: Record<string, string[]>
  }) => {
    const batchId = 'batch-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7)
    const nowStr = new Date().toLocaleString()

    // 当前产品策略：固定为「逐个发布」（一条发完再发下一条）。
    // 想恢复多通道并发时，把下面这行改回 Math.min(params.concurrency || 3, maxConcurrency.value) 即可。
    const effectiveConcurrency = 1

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
        // 目录层级：优先用调用方给的映射，取不到则空数组
        folderCrumbs: params.crumbsMap?.[raw.filePath] || [],
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
    newBatch.tasksSnapshot = JSON.parse(JSON.stringify(newTasks))

    // 智能将新任务追加装载到现有泳道中 (同平台追加到同通道尾部，新平台分配到空闲通道)
    distributeNewBatchIntoLanes(newTasks, effectiveConcurrency)
    refreshAllLanesStatus()
    saveTasksToStorage()

    // 不在创建后自动开始 —— 用户可能分多次创建任务，
    // 统一在任务管理中心点「开始发布」才真正执行
    if (isExecuting.value) {
      // 已有流程在跑：新任务自动并入，沿用当前执行状态
    }

    return batchId
  }

  // 内部辅助：将新创建的批次智能追加到泳道末尾 (平滑追加，绝不把正在执行的任务重置或打乱)
  const distributeNewBatchIntoLanes = (newTasks: PublishTask[], concurrency: number) => {
    // 当前策略：只保留 1 个发布通道（逐个发布）。
    // 先把多余通道里的任务并回主通道，再删除多余通道。
    if (lanes.value.length > 1) {
      const primary = lanes.value[0]
      lanes.value.slice(1).forEach((l) => {
        if (l.tasks && l.tasks.length > 0) primary.tasks.push(...l.tasks)
      })
      lanes.value = [primary]
    }

    // 1. 确保至少有 1 个泳道
    const targetLaneCount = 1
    while (lanes.value.length < targetLaneCount) {
      const idx = lanes.value.length + 1
      lanes.value.push({
        id: `lane-${Date.now()}-${idx}`,
        name: `发布通道 ${idx}`,
        status: 'idle',
        delayBetweenTasks: 15,
        tasks: []
      })
    }

    // 2. 所有新任务全部进入唯一的主通道
    const primary = lanes.value[0]
    newTasks.forEach(t => {
      t.laneId = primary.id
      t.delaySeconds = primary.delayBetweenTasks || 15
      t.orderIndex = primary.tasks.length + 1
      primary.tasks.push(t)
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

    // 3. 构建全新发布通道
    const newLanes: TaskLane[] = []
    for (let i = 0; i < laneCount; i++) {
      newLanes.push({
        id: `lane-${i + 1}`,
        name: `发布通道 ${i + 1}`,
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

  // 3. 泳道管理：新增发布通道 (上限保护)
  const addLane = () => {
    if (!canAddLane.value) {
      ElMessage.warning(`已达系统设置的最大通道数 (${maxConcurrency.value} 个)，如需增加请前往「系统设置」调整`)
      return
    }
    const nextIdx = lanes.value.length + 1
    lanes.value.push({
      id: `lane-${Date.now()}`,
      name: `发布通道 ${nextIdx}`,
      status: 'idle',
      delayBetweenTasks: 15,
      tasks: []
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
    ElMessage.success(`已添加「发布通道 ${nextIdx}」`)
  }

  // 4. 泳道管理：移除发布通道 (通道内任务退回未分配池)
  const removeLane = (laneId: string) => {
    if (lanes.value.length <= 1) {
      ElMessage.info('至少需要保留 1 个执行发布通道')
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

    // 若指定了当前计划（队列模式），只装载该计划的任务；否则维持"全部待发"的老行为
    const planTaskIds = activePlanId.value
      ? new Set(tasks.value.filter(t => t.batchId === activePlanId.value).map(t => t.id))
      : null

    // 逐个发布策略：只使用第 1 个通道（历史数据可能残留多个通道，先收敛）
    const onlyFirstLane = lanes.value.slice(0, 1)

    // 检查是否有排队中或运行中的任务
    const activeLanesWithTasks = onlyFirstLane
      .map(l => ({
        ...l,
        tasks: planTaskIds ? l.tasks.filter(t => planTaskIds.has(t.id)) : l.tasks
      }))
      .filter(l => l.tasks.some(t => t.status === 'queued' || t.status === 'running'))

    if (activeLanesWithTasks.length === 0) {
      if (unassignedTasks.value.length > 0) {
        ElMessage.warning(`还有 ${unassignedTasks.value.length} 个任务在「待分配任务池」，请先把它们拖入发布通道再启动调度`)
      } else {
        ElMessage.info('当前没有可调度的任务')
      }
      return
    }

    // 前置鉴权检查：未激活直接拦截并引导（只做校验与引导，不在此处扣次——试用次数已在用户发起发布的入口消费）
    const authStore = useAuthStore()
    if (!authStore.isAuthorized) {
      authStore.ensurePublishAuth('任务并发调度', false)
      return
    }

    isExecuting.value = true
    executionStartedAt.value = Date.now()
    let hasExecutionError = false

    // 设置泳道运行状态（逐个发布：只处理第 1 个通道）
    onlyFirstLane.forEach(l => {
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

      // 解析每个账号的发布结果 (优先根据 TaskId 精准匹配，同时同步 lanes 与 tasks)
      if (results && Array.isArray(results)) {
        results.forEach((res: engine.AccountPublishResult) => {
          if (!res) return
          const targetId = res.taskId
          if (targetId) {
            syncUpdateTask(
              t => t.id === targetId,
              matched => {
                if (matched.status !== 'success') {
                  matched.status = res.success ? 'success' : 'failed'
                  matched.completedAt = new Date().toLocaleTimeString()
                  matched.completedAtTimestamp = Date.now()
                  matched.progress = 100
                  matched.errorMsg = res.errorMsg || matched.errorMsg || ''
                }
              }
            )
          } else if (res.platform && res.account) {
            // 兜底无 TaskId 时，仅匹配非成功中的第 1 个执行中任务
            const runningTask = tasks.value.find(t => t.platform === res.platform && t.account === res.account && t.status === 'running')
            if (runningTask) {
              syncUpdateTask(
                t => t.id === runningTask.id,
                matched => {
                  matched.status = res.success ? 'success' : 'failed'
                  matched.completedAt = new Date().toLocaleTimeString()
                  matched.completedAtTimestamp = Date.now()
                  matched.progress = 100
                  matched.errorMsg = res.errorMsg || matched.errorMsg || ''
                }
              )
            }
          }
        })
      }

      refreshAllLanesStatus()
    } catch (err: any) {
      hasExecutionError = true
      const errMsg = err?.message || String(err)
      console.error('泳道任务流水线执行异常:', errMsg)

      const isAuthErr = errMsg.includes('激活') || errMsg.includes('授权') || errMsg.includes('到期') || errMsg.includes('卡密')

      if (isAuthErr) {
        ElMessageBox.alert(
          `发布调度已被拦截：${errMsg}\n\n请在软件激活窗口输入卡密完成授权。`,
          '需要激活软件授权',
          {
            confirmButtonText: '前往激活',
            type: 'warning',
            callback: () => {
              authStore.openAuthModal()
            }
          }
        )
      } else {
        ElMessage.error(`任务执行异常: ${errMsg}`)
      }

      // 将涉及到的未完成任务标记为失败并填充清晰错误原因，彻底避免任务一直卡在“排队中”
      syncUpdateTask(
        t => t.status === 'running' || t.status === 'queued',
        t => {
          t.status = 'failed'
          t.errorMsg = errMsg
          t.completedAt = new Date().toLocaleTimeString()
          t.completedAtTimestamp = Date.now()
        }
      )
      lanes.value.forEach(l => {
        l.status = 'failed'
      })
    } finally {
      isExecuting.value = false
      executionStartedAt.value = 0
      refreshAllLanesStatus()
      saveTasksToStorage()

      // 自驱动队列保护（仅在本轮无致命异常时）
      if (!hasExecutionError) {
        if (activePlanId.value) {
          // 队列模式：当前计划还有待发任务 → 续跑同一计划；已跑完 → 推进到下一个计划
          if (planHasPending(activePlanId.value)) {
            setTimeout(() => { triggerMultiLaneExecution() }, 1000)
          } else {
            advancePlanQueue()
          }
        } else {
          // 未指定计划：维持老行为（有排队任务就自动拉起下一轮）
          const hasRemainingQueued = lanes.value.some(l => l.tasks.some(t => t.status === 'queued'))
          if (hasRemainingQueued) {
            setTimeout(() => { triggerMultiLaneExecution() }, 1000)
          }
        }
      }
    }
  }

  // 7. 中止工作流全部任务
  const cancelWorkflow = async () => {
    await StopActivePublish()
    isExecuting.value = false
    executionStartedAt.value = 0
    // 用户主动停止 → 清空执行队列，避免停下来又自动开下一个计划
    pendingPlanQueue.value = []
    activePlanId.value = ''
    syncUpdateTask(
      t => t.status === 'running' || t.status === 'queued',
      t => {
        t.status = 'cancelled'
        t.errorMsg = '用户手动终止'
      }
    )
    lanes.value.forEach(l => {
      l.status = 'idle'
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
  }

  // 7.1 中止单个执行中任务 (优先通过 TaskId 精准杀死进程，通道后续任务自动继续执行)
  const cancelTask = async (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId) || lanes.value.flatMap(l => l.tasks).find(t => t.id === taskId)
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

    syncUpdateTask(t => t.id === taskId, target => {
      target.status = 'cancelled'
      target.errorMsg = '已手动中止该任务，通道后续任务将自动继续执行'
    })

    refreshAllLanesStatus()
    saveTasksToStorage()
    ElMessage.info(`已中止任务「${task.nickname || task.account}」，通道后续任务将自动继续`)
  }

  // 8. 重试 / 恢复单个任务 (自动排布至泳道并立即重置风控限流冷却)
  const retryTask = async (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId) || lanes.value.flatMap(l => l.tasks).find(t => t.id === taskId)
    if (!task) return

    // 关键机制：重试前调用 Go 接口，立即清空该账号在后端的 Cooldown 和失败计数！杜绝后端拦截“提示要等待”！
    try {
      await ResumeAccount(task.platform, task.account)
    } catch (e) {
      console.warn('ResumeAccount on retry failed:', e)
    }

    syncUpdateTask(t => t.id === taskId, target => {
      target.status = 'queued'
      target.errorMsg = ''
      target.isPaused = false
      target.pauseReason = ''
      target.progress = 0
      target.logs = []
    })

    // 确保该任务在某个泳道内
    const inAnyLane = lanes.value.some(l => l.tasks.some(t => t.id === taskId))
    if (!inAnyLane) {
      distributeNewBatchIntoLanes([task], maxConcurrency.value)
    }

    refreshAllLanesStatus()
    saveTasksToStorage()
    triggerMultiLaneExecution()
  }

  // 9. 清理已完成 (仅清理当前活跃泳道画板，批次历史完整归档保存)
  const clearFinishedTasks = () => {
    // 1. 同步归档各批次的最终快照与统计指标，确保历史记录永不丢失
    batches.value.forEach(b => {
      const batchTasks = tasks.value.filter(t => t.batchId === b.id)
      if (batchTasks.length > 0) {
        b.tasksSnapshot = JSON.parse(JSON.stringify(batchTasks.map(t => ({
          ...t,
          logs: t.logs.slice(-20) // 保存最后20条关键日志
        }))))
        b.completedTasks = batchTasks.filter(t => t.status === 'success').length
        b.failedTasks = batchTasks.filter(t => t.status === 'failed' || t.status === 'cancelled').length
        if (b.completedTasks === b.totalTasks && b.totalTasks > 0) {
          b.status = 'completed'
        } else if (b.failedTasks > 0) {
          b.status = 'partial'
        }
      }
    })

    // 2. 从当前活跃画板与泳道中清除已结束的任务，让主画板重归整洁
    tasks.value = tasks.value.filter(t => t.status === 'running' || t.status === 'queued')
    lanes.value.forEach(l => {
      l.tasks = l.tasks.filter(t => t.status === 'running' || t.status === 'queued')
    })
    refreshAllLanesStatus()
    saveTasksToStorage()
    ElMessage.success('已清理已完成的任务记录')
  }

  // 9.2 仅重新发布批次中失败/异常的任务
  const republishFailedInBatch = (batchId: string): string | null => {
    const batch = batches.value.find(b => b.id === batchId)
    const taskList = batch?.tasksSnapshot && batch.tasksSnapshot.length > 0 
      ? batch.tasksSnapshot 
      : tasks.value.filter(t => t.batchId === batchId)

    if (!batch || taskList.length === 0) {
      ElMessage.warning('未找到该批次数据')
      return null
    }

    const failedTasks = taskList.filter(t => t.status === 'failed' || t.status === 'cancelled')
    if (failedTasks.length === 0) {
      ElMessage.info('该批次中没有失败或中止的任务')
      return null
    }

    const rawTasks: engine.AccountPublishTask[] = failedTasks.map(t => ({
      ...t.params,
      status: 'queued'
    }))

    const newBatchId = enqueueBatch({
      batchName: `${batch.name} (重发${failedTasks.length}个失败任务)`,
      videoFileName: batch.videoFileName,
      thumbnail: failedTasks[0]?.thumbnail,
      rawTasks,
      concurrency: batch.concurrency || 1
    })

    ElMessage.success(`已重新装载 ${failedTasks.length} 个失败任务至发布通道`)
    return newBatchId
  }

  // 9.3 删除历史批次
  const deleteBatch = (batchId: string) => {
    const idx = batches.value.findIndex(b => b.id === batchId)
    if (idx >= 0) {
      batches.value.splice(idx, 1)
      if (selectedBatchFilter.value === batchId) {
        selectedBatchFilter.value = 'all'
      }
      saveTasksToStorage()
      ElMessage.info('已删除该批次归档记录')
    }
  }

  /**
   * 删除指定任务（批量）。
   * · 执行中的任务会被跳过（必须先中止）
   * · 同时从所属通道移除、保存本地存储
   * · 批次内任务清空后，批次本身保留（便于历史追溯），仅计数归零
   * @returns 实际删除的数量
   */
  const removeTasks = (taskIds: string[]): number => {
    if (taskIds.length === 0) return 0

    const removable: string[] = []
    let skipped = 0

    taskIds.forEach((id) => {
      const t = tasks.value.find((x) => x.id === id)
      if (!t) return
      if (t.status === 'running') { skipped++; return }   // 执行中不可删
      removable.push(id)
    })

    if (removable.length === 0) {
      if (skipped > 0) ElMessage.warning('执行中的发布计划无法删除，请先中止')
      return 0
    }

    const set = new Set(removable)

    // 1. 从计划列表移除
    tasks.value = tasks.value.filter((t) => !set.has(t.id))

    // 2. 从各通道移除
    lanes.value.forEach((lane) => {
      lane.tasks = lane.tasks.filter((t) => !set.has(t.id))
    })

    // 3. 刷新通道状态与批次计数
    refreshAllLanesStatus()
    saveTasksToStorage()

    if (skipped > 0) {
      ElMessage.success(`已删除 ${removable.length} 个发布计划，${skipped} 个执行中的已跳过`)
    } else {
      ElMessage.success(`已删除 ${removable.length} 个发布计划`)
    }

    return removable.length
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

  // 13. 人工已处理，解除账号安全保护状态并自动恢复队列
  const resumeAccountRisk = async (platform: string, account: string) => {
    try {
      await ResumeAccount(platform, account)
      tasks.value.forEach(t => {
        if (t.platform === platform && t.account === account) {
          t.isPaused = false
          t.pauseReason = ''
          if (t.status === 'failed' && (t.errorMsg?.includes('已自动保护暂停') || t.errorMsg?.includes('准入'))) {
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
            if (t.status === 'failed' && (t.errorMsg?.includes('已自动保护暂停') || t.errorMsg?.includes('准入'))) {
              t.status = 'queued'
              t.errorMsg = ''
            }
          }
        })
      })
      refreshAllLanesStatus()
      saveTasksToStorage()
      ElMessage.success(`已成功解除 [${platform}:${account}] 的安全保护，相关任务已重新排队`)
    } catch (err: any) {
      ElMessage.error(`解除安全保护失败: ${err.message || err}`)
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
    executionStartedAt,
    currentRunningBatchId,
    globalLiveLogs,
    queuedTasksCount,
    runningTasksCount,
    successTasksCount,
    failedTasksCount,
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
    republishFailedInBatch,
    deleteBatch,
    clearAllTasks,
    removeTasks,
    saveTasksToStorage,
    // 计划执行队列
    pendingPlanQueue,
    activePlanId,
    planHasPending,
    setPlanQueue,
    removeFromPlanQueue,
    startPlanQueue,
    advancePlanQueue
  }
})
