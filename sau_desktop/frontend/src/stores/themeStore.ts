import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeMode = 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  // 从本地缓存读取，默认采用暗黑深色模式
  const savedTheme = (localStorage.getItem('sau_theme') as ThemeMode) || 'dark'
  const isDark = ref(savedTheme === 'dark')

  const applyTheme = (dark: boolean) => {
    isDark.value = dark
    const htmlEl = document.documentElement
    if (dark) {
      htmlEl.classList.add('dark')
      htmlEl.classList.remove('light')
      localStorage.setItem('sau_theme', 'dark')
    } else {
      htmlEl.classList.add('light')
      htmlEl.classList.remove('dark')
      localStorage.setItem('sau_theme', 'light')
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
