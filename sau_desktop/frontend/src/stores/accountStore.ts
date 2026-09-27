import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  CheckAccountStatus,
  DeleteAccountCredential,
  LoginAccount,
  SyncAccountsWithCookies
} from '../../wailsjs/go/main/App'
import { createDualStorage } from '../utils/storageAdapter'

/** 分组只存在于用户创建的分组里；账号可以不属于任何分组（groups 为空数组） */

export interface AccountItem {
  platform: string
  account: string       // 底层安全文件标识 (如 account_01 或 user_001)
  nickname?: string     // 真实展示昵称（完整保留 Emoji 和特殊符号）
  finderUid?: string    // 平台唯一 UID
  avatar?: string       // 平台真实高清头像 URL
  avatarLoadFailed?: boolean // 头像加载失败兜底标记
  /** 所属分组（可 0~N 个；空数组 = 未分组） */
  groups?: string[]
  isValid?: boolean
  checked?: boolean
  msg?: string
  loading?: boolean
  isSyncing?: boolean   // 会话结束或状态校验中动画标识
  /** 上次检测登录状态的时间戳（毫秒） */
  checkedAt?: number
}

/** 老数据迁移：group: string → groups: string[]（幂等，可重复执行） */
function migrateAccountGroups(acc: any): AccountItem {
  if (Array.isArray(acc.groups)) {
    acc.groups = acc.groups.filter((g: string) => !!g && g !== '默认分组')
    return acc
  }
  const legacy = typeof acc.group === 'string' ? acc.group.trim() : ''
  acc.groups = (legacy && legacy !== '默认分组') ? [legacy] : []
  delete acc.group
  return acc
}

const accountStorage = createDualStorage<AccountItem[]>({
  diskKey: 'accounts',
  localKey: 'sau_accounts',
  getDefault: () => [],
  debounceMs: 300,
  transformLoad: (raw) => {
    if (!Array.isArray(raw)) return []
    return raw.map((a: any) => {
      let item = migrateAccountGroups(a)
      if (item.platform === 'tencent' && item.account === 'auto' && item.finderUid) {
        item.account = item.finderUid
      }
      item.loading = false
      item.isSyncing = false
      return item
    })
  },
  transformSave: (list) => {
    return list.map(a => {
      const { loading, isSyncing, ...rest } = a
      return rest
    })
  }
})

export const useAccountStore = defineStore('account', () => {
  // 分组列表：全部从已有账号的 groups 字段重建
  const groups = ref<string[]>([])

  // 从本地加载热缓存或使用默认值
  const accounts = ref<AccountItem[]>(accountStorage.get())

  // 从账号数据里补齐分组列表
  const rebuildGroups = () => {
    const seen = new Set<string>(groups.value)
    accounts.value.forEach(a => (a.groups || []).forEach(g => seen.add(g)))
    groups.value = Array.from(seen)
  }
  rebuildGroups()

  const saveToStorage = () => {
    accountStorage.save(accounts.value)
  }

  const checkingAll = ref(false)

  // 添加新分组
  const addGroup = (groupName: string) => {
    const trimmed = groupName.trim()
    if (trimmed && !groups.value.includes(trimmed)) {
      groups.value.push(trimmed)
      return true
    }
    return false
  }

  /** 把账号加入某分组（已在组内则忽略） */
  const addToGroup = (platform: string, account: string, groupName: string) => {
    const g = (groupName || '').trim()
    if (!g) return
    if (!groups.value.includes(g)) groups.value.push(g)
    const target = accounts.value.find(a => a.platform === platform && a.account === account)
    if (!target) return
    if (!Array.isArray(target.groups)) target.groups = []
    if (!target.groups.includes(g)) target.groups.push(g)
    saveToStorage()
  }

  /** 把账号从某分组移除（不影响它在其他分组里的归属） */
  const removeFromGroup = (platform: string, account: string, groupName: string) => {
    const target = accounts.value.find(a => a.platform === platform && a.account === account)
    if (!target || !Array.isArray(target.groups)) return
    target.groups = target.groups.filter(g => g !== groupName)
    saveToStorage()
  }

  /** 批量：把多个账号加入某分组 */
  const addAccountsToGroup = (keys: { platform: string; account: string }[], groupName: string) => {
    keys.forEach(k => addToGroup(k.platform, k.account, groupName))
  }

  /** 切换账号在某分组里的归属 */
  const toggleAccountGroup = (platform: string, account: string, groupName: string) => {
    const target = accounts.value.find(a => a.platform === platform && a.account === account)
    if (!target) return
    if ((target.groups || []).includes(groupName)) removeFromGroup(platform, account, groupName)
    else addToGroup(platform, account, groupName)
  }

  // 每个分组的账号数（用于分组管理弹窗与选择弹层）
  const groupCounts = computed(() => {
    const map: Record<string, number> = {}
    groups.value.forEach((g) => { map[g] = 0 })
    accounts.value.forEach((a) => {
      ;(a.groups || []).forEach(g => { map[g] = (map[g] || 0) + 1 })
    })
    return map
  })

  /**
   * 重命名分组：同步更新组内所有账号。
   * 新名字不能与已有分组重名。
   * @returns 错误信息（成功时返回空字符串）
   */
  const renameGroup = (oldName: string, newName: string): string => {
    const trimmed = (newName || '').trim()
    if (!trimmed) return '分组名不能为空'
    if (trimmed === oldName) return ''
    if (groups.value.includes(trimmed)) return '已存在同名分组'

    groups.value = groups.value.map((g) => (g === oldName ? trimmed : g))
    accounts.value.forEach((a) => {
      if (Array.isArray(a.groups) && a.groups.includes(oldName)) {
        a.groups = a.groups.map(g => (g === oldName ? trimmed : g))
      }
    })
    saveToStorage()
    return ''
  }

  /**
   * 删除分组：把它从所有账号的分组列表里移除（账号本身不删除）。
   * @returns 受影响的账号数
   */
  const removeGroup = (name: string): number => {
    let moved = 0
    accounts.value.forEach((a) => {
      if (Array.isArray(a.groups) && a.groups.includes(name)) {
        a.groups = a.groups.filter(g => g !== name)
        moved += 1
      }
    })
    groups.value = groups.value.filter((g) => g !== name)
    saveToStorage()
    return moved
  }

  // 删除/解绑账号 (前端与磁盘凭证双向同步，先删磁盘，成功后再移除本地列表)
  const removeAccount = async (platform: string, account: string): Promise<boolean> => {
    try {
      await DeleteAccountCredential(platform, account)
    } catch (e) {
      console.warn('删除磁盘凭证异常:', e)
      return false
    }
    const idx = accounts.value.findIndex(a => a.platform === platform && a.account === account)
    if (idx >= 0) {
      accounts.value.splice(idx, 1)
      saveToStorage()
    }
    return true
  }

  // 检测单个账号状态
  const checkAccount = async (row: AccountItem) => {
    // 确保无论传入的是标签页缓存副本还是 store 内部列表项，全部双向同步更新
    const target = accounts.value.find(a => a.platform === row.platform && a.account === row.account) || row
    row.loading = true
    row.isSyncing = true
    if (target !== row) {
      target.loading = true
      target.isSyncing = true
    }

    try {
      const res = await CheckAccountStatus(row.platform, row.account)
      row.isValid = res.isValid
      row.msg = res.msg
      row.checked = true
      row.checkedAt = Date.now()
      if (res.avatar) {
        row.avatar = res.avatar
        row.avatarLoadFailed = false
      }
      if (res.nickname && res.nickname !== 'auto') {
        row.nickname = res.nickname
      }
      if (res.finderUid) {
        row.finderUid = res.finderUid
      }
      if (target !== row) {
        target.isValid = res.isValid
        target.msg = res.msg
        target.checked = true
        target.checkedAt = Date.now()
        if (res.avatar) {
          target.avatar = res.avatar
          target.avatarLoadFailed = false
        }
        if (res.nickname && res.nickname !== 'auto') {
          target.nickname = res.nickname
        }
        if (res.finderUid) {
          target.finderUid = res.finderUid
        }
      }
    } catch (err: any) {
      row.isValid = false
      row.msg = err.message || '检测失败'
      row.checked = true
      if (target !== row) {
        target.isValid = false
        target.msg = err.message || '检测失败'
        target.checked = true
      }
    } finally {
      row.loading = false
      row.isSyncing = false
      if (target !== row) {
        target.loading = false
        target.isSyncing = false
      }
      saveToStorage()
    }
  }

  // 批量检测所有账号
  const checkAllAccounts = async () => {
    checkingAll.value = true
    await Promise.all(accounts.value.map(acc => checkAccount(acc)))
    checkingAll.value = false
  }

  // 扫码/授权登录并加入分组（自动解析出带 Emoji 的真实平台昵称与安全 UID）
  const loginAccount = async (platform: string, customAccount: string, groupsToAdd: string[] = [], headed: boolean = true) => {
    const res: any = await LoginAccount(platform, customAccount || 'auto', headed)
    const targetAccountKey = res.account || customAccount || 'auto'
    const targetNickname = res.nickname || targetAccountKey
    const targetUid = res.finderUid || ''
    const targetAvatar = res.avatar || ''

    if (targetAccountKey === 'auto') {
      return res
    }

    let exist = accounts.value.find(a => a.platform === platform && a.account === targetAccountKey)
    if (!exist && targetUid) {
      exist = accounts.value.find(a => a.platform === platform && a.finderUid === targetUid)
    }
    if (!exist) {
      exist = {
        platform,
        account: targetAccountKey,
        nickname: targetNickname,
        finderUid: targetUid,
        avatar: targetAvatar,
        groups: groupsToAdd,
        checked: false
      }
      accounts.value.push(exist)
    } else {
      exist.account = targetAccountKey
      exist.nickname = targetNickname
      exist.finderUid = targetUid
      if (targetAvatar) exist.avatar = targetAvatar
      if (groupsToAdd.length) {
        const set = new Set([...(exist.groups || []), ...groupsToAdd])
        exist.groups = Array.from(set)
      }
    }
    saveToStorage()
    await checkAccount(exist)
    return res
  }

  // 刷新并从后端物理文件及本地 Cookie 目录重新同步账号数据 (自动反向发现与双向对齐)
  const fetchAccounts = async () => {
    try {
      // 1. 通过通用存储适配器完成首屏与磁盘双向同步及冷迁移
      await accountStorage.load((synced) => {
        accounts.value = synced
        rebuildGroups()
      })

      // 2. 将数据与本地 cookies/*.json 文件进行全量对齐与反向发现
      if (typeof (window as any).go !== 'undefined' && SyncAccountsWithCookies) {
        const syncedJSON = await SyncAccountsWithCookies(JSON.stringify(accountStorage.get()))
        if (syncedJSON) {
          const list = JSON.parse(syncedJSON)
          accounts.value = list.map((a: any) => ({
            ...migrateAccountGroups({ ...a }),
            loading: false,
            isSyncing: false
          }))
          rebuildGroups()
          accountStorage.save(accounts.value)
        }
      }
    } catch (e) {
      console.warn('Sync accounts with backend failed, fallback to local cache', e)
    }
  }

  // 初始化时自动触发一次全量物理对齐
  fetchAccounts()

  // 快捷保存/更新刚识别到的账号凭证 (严格防串号与防误覆盖)
  const saveLoggedInAccount = (platform: string, account: string, nickname?: string, finderUid?: string, isValid?: boolean, avatar?: string) => {
    // 严禁将临时标识 auto 存入持久化账号列表
    if (!account || account === 'auto') {
      return null
    }

    // 优先按平台与唯一标识 account 精确匹配
    let exist = accounts.value.find(a => a.platform === platform && a.account === account)
    if (!exist && finderUid && finderUid.length > 3) {
      exist = accounts.value.find(a => a.platform === platform && a.finderUid === finderUid)
    }

    if (!exist) {
      exist = {
        platform,
        account,
        nickname: nickname || account,
        finderUid: finderUid || '',
        avatar: avatar || '',
        groups: [],
        isValid: isValid !== undefined ? isValid : false,
        checked: isValid !== undefined,
        isSyncing: false
      }
      accounts.value.push(exist)
    } else {
      exist.account = account
      if (nickname) exist.nickname = nickname
      if (finderUid) exist.finderUid = finderUid
      if (avatar) {
        exist.avatar = avatar
        exist.avatarLoadFailed = false
      }
      if (isValid !== undefined) {
        exist.isValid = isValid
        exist.checked = true
      }
      exist.isSyncing = false
    }
    saveToStorage()
    return exist
  }

  return {
    groups,
    accounts,
    checkingAll,
    addGroup,
    addToGroup,
    removeFromGroup,
    addAccountsToGroup,
    toggleAccountGroup,
    removeAccount,
    checkAccount,
    checkAllAccounts,
    loginAccount,
    fetchAccounts,
    saveLoggedInAccount,
    groupCounts,
    renameGroup,
    removeGroup
  }
})
