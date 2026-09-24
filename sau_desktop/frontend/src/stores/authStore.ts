import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetAuthOverview, ApplyActiveCode, GetDeviceID, ConsumeTrial } from '../../wailsjs/go/main/App'
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
    m122_trial_times: 0,
    last_check_time: ''
  }))

  const loading = ref(false)
  const authModalVisible = ref(false)

  // ============ 试用次数：本地累计（对齐批量助手 ExportSubtitle.vue）============
  // 服务端 m122_trial_times 返回的是【额度上限】，剩余次数必须前端自己算
  let consumingTrial = false

  /** 本地已用试用次数 */
  const trialUsed = ref(0)

  /** 试用额度：取服务端返回的额度上限，拿不到时回退 3 */
  const trialLimit = computed(() => {
    const n = (overview.value as any)?.m122_trial_times
    return typeof n === 'number' && n > 0 ? n : 3
  })

  /** 剩余试用次数 */
  const trialRemaining = computed(() => Math.max(0, trialLimit.value - trialUsed.value))

  // ============ 授权状态 ============
  const isAuthorized = computed(() => {
    return (
      overview.value.is_activated ||
      overview.value.m100_activated ||
      overview.value.m122_activated ||
      (overview.value.days_remaining !== undefined && overview.value.days_remaining > 0)
    )
  })

  // ============ 激活引导弹窗 ============
  const promptActivate = async (actionDesc: string, reason: string): Promise<boolean> => {
    try {
      await ElMessageBox.confirm(
        `${reason ? reason + '\n\n' : ''}${actionDesc}需要开通软件授权，当前设备尚未激活或授权已到期。\n\n是否立即前往激活？`,
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

  // ============ 发布授权检查 ============
  /**
   * 检查发布授权。
   * · consumeTrial = true（默认）：未授权时尝试消费一次试用配额
   * · consumeTrial = false：只做校验与引导，不扣次（调度类二次检查用）
   */
  const ensurePublishAuth = async (
    actionDesc = '发布功能',
    consumeTrial = true
  ): Promise<boolean> => {
    // 1. 已授权 → 直接放行
    if (isAuthorized.value) return true

    // 2. 只校验不扣次（调度类的二次检查）→ 走原来的引导激活
    if (!consumeTrial) return promptActivate(actionDesc, '')

    // 3. 未授权 → 先看本地剩余（避免明知用尽还去打扰服务端）
    if (trialRemaining.value <= 0) {
      return promptActivate(actionDesc, '试用机会已用尽')
    }

    // 并发守卫：防止一次用户操作触发多处校验而重复扣次
    if (consumingTrial) return false
    consumingTrial = true
    try {
      const res = await ConsumeTrial()
      if (res?.overview) overview.value = res.overview as any

      if (res?.ok) {
        trialUsed.value += 1
        const left = trialRemaining.value
        if (left > 0) {
          ElMessage.info(`试用中，本次已消耗 1 次，剩余 ${left} 次`)
        } else {
          ElMessage.warning('本次为最后一次免费试用')
        }
        return true
      }

      // 服务端拒绝（次数用尽 / 后台关闭试用 / 未注册）
      trialUsed.value = trialLimit.value // 标记为已用尽
      return promptActivate(actionDesc, res?.message || '试用机会已用尽')
    } catch (e: any) {
      // 保守拦截：网络异常不放行
      ElMessage.error('无法连接授权服务器，请检查网络后重试')
      return false
    } finally {
      consumingTrial = false
    }
  }

  // ============ 刷新授权状态 ============
  const refreshAuth = async () => {
    loading.value = true
    try {
      const res = await GetAuthOverview()
      if (res) {
        overview.value = res
      }
    } catch (e: any) {
      console.warn('获取授权信息异常:', e)
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

  // ============ 提交激活码 ============
  const activate = async (code: string) => {
    loading.value = true
    try {
      const res = await ApplyActiveCode(code)
      if (res && res.is_activated) {
        overview.value = res
        // 激活成功 → 本地试用计数归零（后续 isAuthorized 为 true，不再走试用分支）
        trialUsed.value = 0
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
    trialRemaining,
    ensurePublishAuth,
    refreshAuth,
    activate,
    openAuthModal,
    closeAuthModal
  }
})
