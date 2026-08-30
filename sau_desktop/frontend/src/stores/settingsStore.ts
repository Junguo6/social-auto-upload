import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface AppSettings {
  concurrency: number       // 同时发布窗口数 (并发限制，默认 3)
  headless: boolean          // 默认是否无头后台静默
  declaration: string       // 默认 AI 声明
  chromePath: string        // 自定义本地 Chrome 路径
  autoRetryCount: number    // 失败自动重试次数 (0~3)
}

export const useSettingsStore = defineStore('settings', () => {
  const defaultSettings: AppSettings = {
    concurrency: 3,
    headless: false,
    declaration: '内容由AI生成',
    chromePath: '',
    autoRetryCount: 1
  }

  const saved = localStorage.getItem('sau_settings')
  const settings = ref<AppSettings>(saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings)

  const saveSettings = () => {
    localStorage.setItem('sau_settings', JSON.stringify(settings.value))
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
