import { engine } from '../../wailsjs/go/models'

export type TaskStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled'
export type TaskPriority = 'high' | 'normal' | 'low'
export type ExecutionMode = 'parallel' | 'sequential'

export interface TaskLogItem {
  time: string
  type: string
  message: string
}

export interface PublishTask {
  id: string                    // 唯一任务 ID
  laneId?: string               // 所属并发线程通道 ID
  batchId: string               // 批次 ID
  batchName: string             // 批次名称
  videoFileName?: string        // 关联的本地视频源文件名
  thumbnail?: string            // 封面缩略图路径
  platform: string              // 平台 ID
  account: string               // 账号 ID/标识
  nickname: string              // 账号昵称
  title: string                 // 发布标题
  action: 'upload-video' | 'upload-note'
  status: TaskStatus
  priority: TaskPriority
  progress: number              // 0-100
  orderIndex: number            // 步骤/执行次序
  scheduledAt?: string          // 计划执行时刻 (YYYY-MM-DD HH:mm:ss)
  delaySeconds?: number         // 该步骤完成后到下一步骤的延时秒数
  createdAt: string
  startedAt?: string
  completedAt?: string
  completedAtTimestamp?: number // 完成时刻的毫秒级时间戳 (用于计算动态防风控间隔)
  duration?: number             // 执行耗时(秒)
  errorMsg?: string
  logs: TaskLogItem[]
  params: engine.AccountPublishTask // 完整下发参数快照
}

// 单个工作流并发协程通道 (Worker Lane)
export interface TaskLane {
  id: string                    // 通道 ID (e.g. lane-1)
  name: string                  // 通道名称 (e.g. 线程通道 1)
  status: 'idle' | 'running' | 'completed' | 'failed'
  delayBetweenTasks: number     // 通道内任务默认防风控延时步长(秒)
  scheduledAt?: string          // 通道定时启动时间
  tasks: PublishTask[]          // 通道内的串行卡片流
}

export interface TaskBatch {
  id: string
  name: string
  videoFileName?: string
  createdAt: string
  totalTasks: number
  completedTasks: number
  failedTasks: number
  status: 'queued' | 'running' | 'completed' | 'partial'
  concurrency: number
  executionMode: ExecutionMode
  delayBetweenTasks?: number
  scheduledAt?: string
}
