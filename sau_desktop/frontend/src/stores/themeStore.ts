import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeMode = 'dark' | 'light'

const THEME_KEY = 'sau_theme'
const MIGRATION_FLAG = 'sau_theme_light_migrated'

// 一次性把默认主题迁移到「浅色」(A 版形式)：仅在升级后首次启动时执行一次，
// 之后用户在应用内的选择（切到暗色）会被尊重，不再被覆盖
if (!localStorage.getItem(MIGRATION_FLAG)) {
  localStorage.setItem(THEME_KEY, 'light')
  localStorage.setItem(MIGRATION_FLAG, '1')
}

export const useThemeStore = defineStore('theme', () => {
  // 从本地缓存读取，默认采用浅色模式 (A 版形式)
  const savedTheme = (localStorage.getItem(THEME_KEY) as ThemeMode) || 'light'
  const isDark = ref(savedTheme === 'dark')

  const applyTheme = (dark: boolean) => {
    isDark.value = dark
    const htmlEl = document.documentElement
    if (dark) {
      htmlEl.classList.add('dark')
      htmlEl.classList.remove('light')
      localStorage.setItem(THEME_KEY, 'dark')
    } else {
      htmlEl.classList.add('light')
      htmlEl.classList.remove('dark')
      localStorage.setItem(THEME_KEY, 'light')
    }
  }

  const toggleTheme = () => {
    applyTheme(!isDark.value)
  }

  // 初始化生效
  applyTheme(isDark.value)

  return {
    isDark,
    toggleTheme,
    applyTheme
  }
})
