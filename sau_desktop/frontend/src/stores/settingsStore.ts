import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createDualStorage } from '../utils/storageAdapter'

export interface AppSettings {
  concurrency: number       // 同时发布窗口数 (并发限制，默认 3)
  headless: boolean          // 默认是否无头后台静默
  declaration: string       // 默认 AI 声明
  chromePath: string        // 自定义本地 Chrome 路径
  autoRetryCount: number    // 失败自动重试次数 (0~3)
}

const defaultSettings: AppSettings = {
  concurrency: 3,
  headless: false,
  declaration: '',             // 各平台「标注/声明」选项各异，统一默认空 → 不操作；用户自选时由各平台表单填充
  chromePath: '',
  autoRetryCount: 1
}

const settingsStorage = createDualStorage<AppSettings>({
  diskKey: 'settings',
  localKey: 'sau_settings',
  getDefault: () => defaultSettings,
  debounceMs: 300,
  transformLoad: (raw) => ({ ...defaultSettings, ...(raw || {}) })
})

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<AppSettings>(settingsStorage.get())

  // 异步与物理磁盘对齐并完成首次冷迁移
  settingsStorage.load((synced) => {
    settings.value = synced
  })

  const saveSettings = () => {
    settingsStorage.save(settings.value)
  }

  const updateSettings = (newSettings: Partial<AppSettings>) => {
    settings.value = { ...settings.value, ...newSettings }
    saveSettings()
  }

  const resetSettings = () => {
    settings.value = { ...defaultSettings }
    saveSettings()
  }

  return {
    settings,
    updateSettings,
    resetSettings,
    saveSettings
  }
})
