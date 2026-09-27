import { LoadAppData, SaveAppData } from '../../wailsjs/go/main/App'

export interface DualStorageOptions<T> {
  /** 后端物理磁盘文件名（如 'tasks' -> data/tasks.json） */
  diskKey: string
  /** 兼容既有 localStorage 的键名 */
  localKey: string
  /** 默认初始值工厂函数或对象 */
  getDefault: () => T
  /** 防抖刷盘延迟（毫秒），默认 500ms。传 0 则立即落盘 */
  debounceMs?: number
  /** 数据转换处理函数（如从存储恢复时补充必要字段） */
  transformLoad?: (raw: any) => T
  /** 保存前的数据裁剪处理函数（如切片日志、裁剪超限列表） */
  transformSave?: (data: T) => any
}

export interface DualStorageInstance<T> {
  /** 获取当前最新快照数据 */
  get: () => T
  /** 同步/异步加载数据（热缓存优先，随后磁盘对齐与冷迁移） */
  load: (onSynced?: (data: T) => void) => Promise<T>
  /** 保存数据（内存即刻更新，磁盘防抖落盘） */
  save: (data: T) => void
  /** 立即强制将当前缓冲区数据落盘（跳过防抖） */
  flush: () => Promise<void>
}

/**
 * 创建具有双驱动持久化能力的存储适配器
 * 实现：首屏0ms渲染 + 自动平滑冷迁移 + 防抖原子落盘 + 异常安全降级
 */
export function createDualStorage<T>(options: DualStorageOptions<T>): DualStorageInstance<T> {
  const {
    diskKey,
    localKey,
    getDefault,
    debounceMs = 500,
    transformLoad = (val) => val as T,
    transformSave = (val) => val
  } = options

  // 1. 初始化热缓存：尝试从 localStorage 同步读取，保证第 0 毫秒即可渲染
  let currentData: T = getDefault()
  try {
    const localRaw = localStorage.getItem(localKey)
    if (localRaw) {
      currentData = transformLoad(JSON.parse(localRaw))
    }
  } catch (err) {
    console.warn(`[DualStorage:${diskKey}] Failed to read initial localStorage:`, err)
  }

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let pendingSavePayload: string | null = null

  // 执行物理磁盘写入
  const writeToDisk = async (payload: string) => {
    if (typeof (window as any).go !== 'undefined' && SaveAppData) {
      try {
        await SaveAppData(diskKey, payload)
      } catch (err) {
        console.error(`[DualStorage:${diskKey}] SaveAppData failed:`, err)
      }
    }
  }

  // 异步从物理磁盘对齐与迁移
  const load = async (onSynced?: (data: T) => void): Promise<T> => {
    if (typeof (window as any).go === 'undefined' || !LoadAppData) {
      return currentData
    }

    try {
      const diskRaw = await LoadAppData(diskKey)
      if (diskRaw && diskRaw.trim() !== '') {
        const parsed = JSON.parse(diskRaw)
        currentData = transformLoad(parsed)
        // 回写更新 localStorage 热缓存
        localStorage.setItem(localKey, diskRaw)
        if (onSynced) onSynced(currentData)
      } else {
        // 磁盘尚无数据但 localStorage 有数据：自动做首次冷迁移
        const localRaw = localStorage.getItem(localKey)
        if (localRaw) {
          await writeToDisk(localRaw)
        }
      }
    } catch (err) {
      console.warn(`[DualStorage:${diskKey}] LoadAppData sync failed:`, err)
    }

    return currentData
  }

  // 保存数据
  const save = (data: T) => {
    currentData = data
    try {
      const prepared = transformSave(data)
      const raw = JSON.stringify(prepared)

      // 1. 立即更新 localStorage，保证热缓存最新
      localStorage.setItem(localKey, raw)
      pendingSavePayload = raw

      // 2. 防抖落盘物理磁盘
      if (debounceMs <= 0) {
        writeToDisk(raw)
      } else {
        if (debounceTimer) {
          clearTimeout(debounceTimer)
        }
        debounceTimer = setTimeout(() => {
          if (pendingSavePayload) {
            writeToDisk(pendingSavePayload)
            pendingSavePayload = null
          }
          debounceTimer = null
        }, debounceMs)
      }
    } catch (err) {
      console.error(`[DualStorage:${diskKey}] Failed to serialize data:`, err)
    }
  }

  // 立即落盘
  const flush = async () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    if (pendingSavePayload) {
      const payload = pendingSavePayload
      pendingSavePayload = null
      await writeToDisk(payload)
    }
  }

  return {
    get: () => currentData,
    load,
    save,
    flush
  }
}
