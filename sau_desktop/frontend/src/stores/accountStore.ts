import { defineStore } from 'pinia'
import { ref } from 'vue'
import { CheckAccountStatus, LoginAccount } from '../../wailsjs/go/main/App'

export interface AccountItem {
  platform: string
  account: string       // 底层安全文件标识 (如 sphGLRxSCzBVA5O 或 user_001)
  nickname?: string     // 真实展示昵称（完整保留 Emoji 和特殊符号）
  finderUid?: string    // 平台唯一 UID (如 sphGLRxSCzBVA5O)
  group: string         // 分组标签，例如 "默认分组", "美食矩阵", "科技出海"
  isValid?: boolean
  checked?: boolean
  msg?: string
  loading?: boolean
}

export const useAccountStore = defineStore('account', () => {
  // 分组列表
  const groups = ref<string[]>([
    '默认分组',
    '美食矩阵组',
    '数码科技组',
    '生活日常组'
  ])

  // 默认初始账号数据 (优先展示 nickname，若无则展示 account)
  const defaultAccounts: AccountItem[] = [
    { platform: 'douyin', account: 'test_account', nickname: '抖音科技号 🚀', group: '默认分组', checked: false },
    { platform: 'douyin', account: 'douyin_food_01', nickname: '吃货小分队 🍜', group: '美食矩阵组', checked: false },
    { platform: 'xiaohongshu', account: 'xhs_lifestyle_01', nickname: '日常好物研习社 ✨', group: '生活日常组', checked: false },
    { platform: 'xiaohongshu', account: 'xhs_tech_01', nickname: '极客实验室 ⚡️', group: '数码科技组', checked: false },
    { platform: 'kuaishou', account: 'ks_user_01', nickname: '快手老铁分享 🎬', group: '美食矩阵组', checked: false },
    { platform: 'bilibili', account: 'bili_tech_main', nickname: '干货极客UP 📺', group: '数码科技组', checked: false },
    { platform: 'tencent', account: 'sphGLRxSCzBVA5O', nickname: '迟遇山野知秋 🌿', finderUid: 'sphGLRxSCzBVA5O', group: '生活日常组', checked: false }
  ]

  // 从本地加载或使用默认值
  const savedAccs = localStorage.getItem('sau_accounts')
  let parsedAccs: AccountItem[] = defaultAccounts
  if (savedAccs) {
    try {
      parsedAccs = JSON.parse(savedAccs)
      // 迁移历史 tencent_1233 项
      parsedAccs = parsedAccs.map(acc => {
        if (acc.platform === 'tencent' && (acc.account === '1233' || acc.account === 'auto') && acc.finderUid) {
          acc.account = acc.finderUid
        }
        return acc
      })
    } catch (e) {
      parsedAccs = defaultAccounts
    }
  }
  const accounts = ref<AccountItem[]>(parsedAccs)

  const saveToStorage = () => {
    localStorage.setItem('sau_accounts', JSON.stringify(accounts.value))
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

  // 删除/解绑账号
  const removeAccount = (platform: string, account: string) => {
    const idx = accounts.value.findIndex(a => a.platform === platform && a.account === account)
    if (idx >= 0) {
      accounts.value.splice(idx, 1)
      saveToStorage()
    }
  }

  // 检测单个账号状态
  const checkAccount = async (row: AccountItem) => {
    row.loading = true
    try {
      const res = await CheckAccountStatus(row.platform, row.account)
      row.isValid = res.isValid
      row.msg = res.msg
      row.checked = true
    } catch (err: any) {
      row.isValid = false
      row.msg = err.message || '检测失败'
      row.checked = true
    } finally {
      row.loading = false
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

    let exist = accounts.value.find(a => a.platform === platform && (a.account === targetAccountKey || (targetUid && a.finderUid === targetUid)))
    if (!exist) {
      exist = {
        platform,
        account: targetAccountKey,
        nickname: targetNickname,
        finderUid: targetUid,
        group: group || '默认分组',
        checked: false
      }
      accounts.value.push(exist)
    } else {
      exist.account = targetAccountKey
      exist.nickname = targetNickname
      exist.finderUid = targetUid
      exist.group = group || exist.group
    }
    saveToStorage()
    await checkAccount(exist)
    return res
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
    loginAccount
  }
})
