import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { CheckAccountStatus, DeleteAccountCredential, LoginAccount } from '../../wailsjs/go/main/App'

/** 默认分组名（不可改名、不可删除；删除分组时账号回落到这里） */
export const DEFAULT_GROUP = '默认分组'

export interface AccountItem {
  platform: string
  account: string       // 底层安全文件标识 (如 account_01 或 user_001)
  nickname?: string     // 真实展示昵称（完整保留 Emoji 和特殊符号）
  finderUid?: string    // 平台唯一 UID
  avatar?: string       // 平台真实高清头像 URL
  avatarLoadFailed?: boolean // 头像加载失败兜底标记
  group: string         // 分组标签，例如 "默认分组", "美食矩阵", "科技出海"
  isValid?: boolean
  checked?: boolean
  msg?: string
  loading?: boolean
  isSyncing?: boolean   // 会话结束或状态校验中动画标识
}

export const useAccountStore = defineStore('account', () => {
  // 分组列表
  const groups = ref<string[]>([
    DEFAULT_GROUP
  ])

  // 默认初始账号数据 (初始为空)
  const defaultAccounts: AccountItem[] = []

  // 从本地加载或使用默认值
  const savedAccs = localStorage.getItem('sau_accounts')
  let parsedAccs: AccountItem[] = defaultAccounts
  if (savedAccs) {
    try {
      parsedAccs = JSON.parse(savedAccs)
      parsedAccs = parsedAccs.map(acc => {
        if (acc.platform === 'tencent' && acc.account === 'auto' && acc.finderUid) {
          acc.account = acc.finderUid
        }
        acc.loading = false
        acc.isSyncing = false
        return acc
      })
    } catch (e) {
      parsedAccs = defaultAccounts
    }
  }
  const accounts = ref<AccountItem[]>(parsedAccs)

  const saveToStorage = () => {
    // 持久化存储时剔除 loading 和 isSyncing 运行时临时状态，杜绝污染本地存储导致永久卡在同步中
    const cleanList = accounts.value.map(a => {
      const { loading, isSyncing, ...rest } = a
      return rest
    })
    localStorage.setItem('sau_accounts', JSON.stringify(cleanList))
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

  // 修改账号分组
  const updateAccountGroup = (platform: string, account: string, newGroup: string) => {
    const target = accounts.value.find(a => a.platform === platform && a.account === account)
    if (target) {
      target.group = newGroup
      saveToStorage()
    }
  }

  // 每个分组的账号数（用于分组管理弹窗与选择弹层）
  const groupCounts = computed(() => {
    const map: Record<string, number> = {}
    groups.value.forEach((g) => { map[g] = 0 })
    accounts.value.forEach((a) => {
      const g = a.group || DEFAULT_GROUP
      map[g] = (map[g] || 0) + 1
    })
    return map
  })

  /**
   * 重命名分组：同步更新组内所有账号。
   * 默认分组不允许改名；新名字不能与已有分组重名。
   * @returns 错误信息（成功时返回空字符串）
   */
  const renameGroup = (oldName: string, newName: string): string => {
    const trimmed = (newName || '').trim()
    if (!trimmed) return '分组名不能为空'
    if (oldName === DEFAULT_GROUP) return '默认分组不可改名'
    if (trimmed === oldName) return ''
    if (groups.value.includes(trimmed)) return '已存在同名分组'

    groups.value = groups.value.map((g) => (g === oldName ? trimmed : g))
    accounts.value.forEach((a) => {
      if ((a.group || DEFAULT_GROUP) === oldName) a.group = trimmed
    })
    saveToStorage()
    return ''
  }

  /**
   * 删除分组：组内账号回落到默认分组（不删除账号本身）。
   * 默认分组不可删除。
   * @returns 受影响并已转移的账号数；-1 表示不允许删除
   */
  const removeGroup = (name: string): number => {
    if (name === DEFAULT_GROUP) return -1

    let moved = 0
    accounts.value.forEach((a) => {
      if ((a.group || DEFAULT_GROUP) === name) {
        a.group = DEFAULT_GROUP
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
  const loginAccount = async (platform: string, customAccount: string, group: string, headed: boolean = true) => {
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
        group: group || '默认分组',
        checked: false
      }
      accounts.value.push(exist)
    } else {
      exist.account = targetAccountKey
      exist.nickname = targetNickname
      exist.finderUid = targetUid
      if (targetAvatar) exist.avatar = targetAvatar
      exist.group = group || exist.group
    }
    saveToStorage()
    await checkAccount(exist)
    return res
  }

  // 刷新并从本地存储重新同步账号数据
  const fetchAccounts = () => {
    const saved = localStorage.getItem('sau_accounts')
    if (saved) {
      try {
        const list = JSON.parse(saved)
        accounts.value = list.map((a: any) => ({
          ...a,
          loading: false,
          isSyncing: false
        }))
      } catch (e) {}
    }
  }

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
        group: '默认分组',
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
    updateAccountGroup,
    removeAccount,
    checkAccount,
    checkAllAccounts,
    loginAccount,
    fetchAccounts,
    saveLoggedInAccount,
    groupCounts,
    renameGroup,
    removeGroup,
    DEFAULT_GROUP
  }
})
