import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { GetAuthOverview, ApplyActiveCode, GetDeviceID } from '../../wailsjs/go/main/App'
import { auth } from '../../wailsjs/go/models'

export const useAuthStore = defineStore('auth', () => {
  const overview = ref<auth.AuthOverview>(new auth.AuthOverview({
    new_sn: '',
    machine_id: '',
    is_activated: false,
    is_expired: false,
    days_remaining: 0,
    deadline: '',
    user_id: '',
    version: '1.2.0',
    announcement: '',
    help_url: '',
    agent_notice: '',
    agent_website: '',
    m100_activated: false,
    m122_activated: false,
    last_check_time: ''
  }))

  const loading = ref(false)
  const authModalVisible = ref(false)

  // 授权状态判定 (激活且未到期)
  const isAuthorized = computed(() => {
    return (
      overview.value.is_activated ||
      overview.value.m100_activated ||
      overview.value.m122_activated ||
      (overview.value.days_remaining !== undefined && overview.value.days_remaining > 0)
    )
  })

  // 检查发布授权，若未激活则友好弹窗引导
  const ensurePublishAuth = async (actionDesc = '发布功能'): Promise<boolean> => {
    if (isAuthorized.value) {
      return true
    }
    try {
      await ElMessageBox.confirm(
        `${actionDesc}需要开通软件授权，当前设备尚未激活或授权已到期。\n\n是否立即前往激活？`,
        '软件未激活',
        {
          confirmButtonText: '立即激活',
          cancelButtonText: '暂不激活',
          type: 'warning',
          center: true,
          roundButton: true
        }
      )
      openAuthModal()
    } catch {
      // 用户取消
    }
    return false
  }

  // 刷新云端鉴权状态
  const refreshAuth = async () => {
    loading.value = true
    try {
      const res = await GetAuthOverview()
      if (res) {
        overview.value = res
      }
    } catch (e: any) {
      console.warn('获取授权信息异常:', e)
      // 若获取失败，至少兜底拿到本地机器识别码
      if (!overview.value.new_sn) {
        try {
          const sn = await GetDeviceID()
          if (sn) overview.value.new_sn = sn
        } catch (_) {}
      }
    } finally {
      loading.value = false
    }
  }

  // 提交激活码
  const activate = async (code: string) => {
    loading.value = true
    try {
      const res = await ApplyActiveCode(code)
      if (res && res.is_activated) {
        overview.value = res
        return { success: true, msg: '🎉 激活成功！授权已生效' }
      } else {
        return { success: false, msg: '激活失败：未能获取到有效授权，请检查卡密是否正确' }
      }
    } catch (err: any) {
      return { success: false, msg: err?.message || err || '激活失败，卡密无效或已被使用' }
    } finally {
      loading.value = false
    }
  }

  const openAuthModal = () => {
    authModalVisible.value = true
  }

  const closeAuthModal = () => {
    authModalVisible.value = false
  }

  return {
    overview,
    isAuthorized,
    loading,
    authModalVisible,
    ensurePublishAuth,
    refreshAuth,
    activate,
    openAuthModal,
    closeAuthModal
  }
})
