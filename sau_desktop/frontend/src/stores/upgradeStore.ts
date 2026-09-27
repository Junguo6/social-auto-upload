import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  CheckUpdate,
  StartDownloadUpdate,
  CancelDownloadUpdate,
  ApplyUpdate,
  QuitApp,
  GetAppVersion
} from '../../wailsjs/go/main/App'
import { upgrade } from '../../wailsjs/go/models'
import { EventsOn } from '../../wailsjs/runtime/runtime'

export const useUpgradeStore = defineStore('upgrade', () => {
  const checking = ref(false)
  const hasUpdate = ref(false)
  const isDownloading = ref(false)
  const isInstalling = ref(false)
  const isCompleted = ref(false)
  const modalVisible = ref(false)

  const currentVersion = ref('')
  const latestVersion = ref('')
  const versionInfo = ref<upgrade.VersionInfo | null>(null)

  const downloadProgress = ref<upgrade.DownloadProgress>({
    percentage: 0,
    downloaded: 0,
    total: 0,
    downloaded_mb: 0,
    total_mb: 0,
    status: 'idle',
    message: ''
  })

  let listenerInitialized = false

  const isForced = computed(() => !!versionInfo.value?.is_forced)

  // 监听 Wails 后台下载进度事件
  const initEventListener = () => {
    if (listenerInitialized) return
    listenerInitialized = true

    EventsOn('sau-upgrade-progress', (progress: upgrade.DownloadProgress) => {
      downloadProgress.value = progress
      if (progress.status === 'downloading') {
        isDownloading.value = true
      } else if (progress.status === 'completed') {
        isDownloading.value = false
        isCompleted.value = true
        // 若为强制更新，下载完成后自动进入安装重启流程
        if (isForced.value) {
          setTimeout(() => {
            applyUpdate()
          }, 800)
        }
      } else if (progress.status === 'error') {
        isDownloading.value = false
        ElMessage.error(progress.message || progress.error || '下载升级包异常')
      }
    })
  }

  // 检查更新
  // silent = true 用于应用启动时的静默检查（仅在需要弹窗或强制更新时才打扰用户）
  // silent = false 用于设置页手动点击（始终给出清晰反馈）
  const checkUpdate = async (silent = true) => {
    checking.value = true
    try {
      if (!currentVersion.value) {
        currentVersion.value = await GetAppVersion()
      }

      initEventListener()

      const res = await CheckUpdate()
      if (!res) {
        if (!silent) ElMessage.info('未获取到版本信息，当前已是最新版本')
        return
      }

      hasUpdate.value = !!res.has_update
      currentVersion.value = res.current_version || currentVersion.value
      latestVersion.value = res.latest_version || currentVersion.value
      versionInfo.value = res.version_info || null

      if (res.has_update && res.version_info) {
        // 强制更新或配置了弹窗提示时，弹出升级框
        if (!silent || res.version_info.is_forced || res.version_info.is_pop_up) {
          modalVisible.value = true
        } else {
          // 静默模式下若有新版但未勾选强弹，展示非阻塞式轻通知
          ElNotification({
            title: '发现新版本',
            message: `小映分发助手 v${res.latest_version} 已发布，可前往【设置】或点击更新`,
            type: 'info',
            duration: 6000,
            position: 'bottom-right',
            onClick: () => {
              modalVisible.value = true
            }
          })
        }
      } else {
        if (!silent) {
          ElMessage.success(`当前已是最新版本 (v${currentVersion.value})`)
        }
      }
    } catch (err: any) {
      console.error('检查更新失败:', err)
      if (!silent) {
        ElMessage.error(`检测更新失败: ${err?.message || err}`)
      }
    } finally {
      checking.value = false
    }
  }

  // 开始下载升级包
  const startDownload = async () => {
    if (isDownloading.value) return
    isDownloading.value = true
    isCompleted.value = false
    downloadProgress.value = {
      percentage: 0,
      downloaded: 0,
      total: 0,
      downloaded_mb: 0,
      total_mb: 0,
      status: 'downloading',
      message: '正在连接服务器...'
    }

    try {
      await StartDownloadUpdate()
    } catch (err: any) {
      isDownloading.value = false
      ElMessage.error(`启动下载失败: ${err?.message || err}`)
    }
  }

  // 取消下载
  const cancelDownload = async () => {
    try {
      await CancelDownloadUpdate()
      isDownloading.value = false
    } catch (err) {
      console.error('取消下载失败:', err)
    }
  }

  // 执行更新安装与重启
  const applyUpdate = async () => {
    if (isInstalling.value) return
    isInstalling.value = true
    try {
      await ApplyUpdate()
      ElMessage({
        message: '升级准备就绪，软件即将自动重启生效...',
        type: 'success',
        duration: 3000
      })
      setTimeout(async () => {
        try {
          await QuitApp()
        } catch {
          // 容错处理
        }
      }, 1500)
    } catch (err: any) {
      ElMessage.error(`执行升级失败: ${err?.message || err}`)
      isInstalling.value = false
    }
  }

  const openModal = () => {
    modalVisible.value = true
  }

  const closeModal = () => {
    if (isForced.value) {
      ElMessage.warning('当前版本包含重大安全或架构更新，必须完成升级后方可继续使用')
      return
    }
    modalVisible.value = false
  }

  return {
    checking,
    hasUpdate,
    isDownloading,
    isInstalling,
    isCompleted,
    modalVisible,
    currentVersion,
    latestVersion,
    versionInfo,
    downloadProgress,
    isForced,
    initEventListener,
    checkUpdate,
    startDownload,
    cancelDownload,
    applyUpdate,
    openModal,
    closeModal
  }
})
