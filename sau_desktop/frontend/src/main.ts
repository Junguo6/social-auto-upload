import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './assets/main.css'

// ============ 全局阻止 WebView 的默认拖放行为 ============
// 背景：Wails 原生拖拽（main.go 的 EnableFileDrop）是 OS 级实现，只负责把文件路径回调给 Go，
// 并不会阻止 WebView 自己处理这次拖放。
// 若不在全局拦截：拖到未被 @drop.prevent 覆盖的区域时，WebView 会导航到该文件
//   · 拖入视频 → 整个界面变成全屏视频播放器
//   · 拖入文件夹 → 变成 file:// 文件列表
// 拖拽导入统一由 Go 侧 OnFileDrop（media:file-drop 事件）处理，这里只需阻止默认行为。
window.addEventListener('dragover', (e) => e.preventDefault(), false)
window.addEventListener('drop', (e) => e.preventDefault(), false)

const app = createApp(App)

// 注册 ElementPlus 所有 Icon 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { size: 'default' })

app.mount('#app')
