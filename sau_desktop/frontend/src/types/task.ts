import { engine } from '../../wailsjs/go/models'

export type TaskStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled'
export type TaskPriority = 'high' | 'normal' | 'low'

export interface TaskLogItem {
  time: string
  type: string
  message: string
}

export interface PublishTask {
  id: string                    // 唯一任务 ID (e.g. task-1725100000000-xxx)
  batchId: string               // 批次 ID
  batchName: string             // 批次名称
  platform: string              // 平台 ID
  account: string               // 账号 ID/标识
  nickname: string              // 账号昵称
  title: string                 // 发布标题
  action: 'upload-video' | 'upload-note'
  status: TaskStatus
  priority: TaskPriority
  progress: number              // 0-100
  createdAt: string
  startedAt?: string
  completedAt?: string
  duration?: number             // 执行耗时(秒)
  errorMsg?: string
  logs: TaskLogItem[]
  params: engine.AccountPublishTask // 完整下发参数快照，用于重试
}

export interface TaskBatch {
  id: string
  name: string
  createdAt: string
  totalTasks: number
  completedTasks: number
  failedTasks: number
  status: 'queued' | 'running' | 'completed' | 'partial'
  concurrency: number
}
