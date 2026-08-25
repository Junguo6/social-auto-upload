import { defineStore } from 'pinia'
import { ref } from 'vue'
import { BatchPublishMedia, StopActivePublish } from '../../wailsjs/go/main/App'
import { engine } from '../../wailsjs/go/models'

export interface PublishTask {
  id: string
  platform: string
  account: string
  title: string
  filePath: string
  status: 'pending' | 'running' | 'success' | 'failed'
  createdAt: string
  errorMsg?: string
}

export const usePublishStore = defineStore('publish', () => {
  const isPublishing = ref(false)
  const taskHistory = ref<PublishTask[]>([])

  // 记录当前矩阵批次中各个账号的状态映射 (key: `${platform}:${account}`)
  const batchAccountStates = ref<Record<string, 'pending' | 'running' | 'success' | 'failed'>>({})

  // 执行矩阵并发批量发布 (支持全量高级参数)
  const executeBatchPublish = async (params: {
    targets: Array<{ platform: string; account: string }>
    concurrency: number
    action: string
    filePath: string
    images: string[]
    title: string
    desc: string
    tags: string
    thumbnail?: string
    thumbnailLandscape?: string
    thumbnailPortrait?: string
    tid?: number
    shortTitle?: string
    category?: string
    draft?: boolean
    schedule?: string
    declaration?: string
    collection?: string
    productLink?: string
    productTitle?: string
    visibility?: string
    playlist?: string
    bgm?: string
    note?: string
    notef?: string
    headless: boolean
  }) => {
    isPublishing.value = true

    // 初始化每个账号的状态为 running
    const newStates: Record<string, 'pending' | 'running' | 'success' | 'failed'> = {}
    params.targets.forEach(t => {
      newStates[`${t.platform}:${t.account}`] = 'running'
    })
    batchAccountStates.value = newStates

    try {
      const payload = engine.BatchPublishParam.createFrom(params)
      const results = await BatchPublishMedia(payload)

      // 更新最终各账号结果
      if (results && Array.isArray(results)) {
        results.forEach((res: engine.AccountPublishResult) => {
          const key = `${res.platform}:${res.account}`
          batchAccountStates.value[key] = res.success ? 'success' : 'failed'

          taskHistory.value.unshift({
            id: String(Date.now() + Math.random()),
            platform: res.platform,
            account: res.account,
            title: params.title,
            filePath: params.filePath,
            status: res.success ? 'success' : 'failed',
            createdAt: new Date().toLocaleTimeString(),
            errorMsg: res.errorMsg
          })
        })
      }

      return results || []
    } finally {
      isPublishing.value = false
    }
  }

  const cancelPublish = async () => {
    return await StopActivePublish()
  }

  return {
    isPublishing,
    taskHistory,
    batchAccountStates,
    executeBatchPublish,
    cancelPublish
  }
})
