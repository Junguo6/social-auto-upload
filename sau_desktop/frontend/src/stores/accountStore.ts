import { defineStore } from 'pinia'
import { ref } from 'vue'
import { CheckAccountStatus, LoginAccount } from '../../wailsjs/go/main/App'

export interface AccountItem {
  platform: string
  account: string
  group: string // 分组标签，例如 "默认分组", "美食矩阵", "科技出海"
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

  // 默认初始账号数据
  const defaultAccounts: AccountItem[] = [
    { platform: 'douyin', account: 'test_account', group: '默认分组', checked: false },
    { platform: 'douyin', account: 'douyin_food_01', group: '美食矩阵组', checked: false },
    { platform: 'xiaohongshu', account: 'xhs_lifestyle_01', group: '生活日常组', checked: false },
    { platform: 'xiaohongshu', account: 'xhs_tech_01', group: '数码科技组', checked: false },
    { platform: 'kuaishou', account: 'ks_user_01', group: '美食矩阵组', checked: false },
    { platform: 'bilibili', account: 'bili_tech_main', group: '数码科技组', checked: false },
    { platform: 'tencent', account: 'channels_vlog', group: '生活日常组', checked: false }
  ]

  // 从本地加载或使用默认值
  const savedAccs = localStorage.getItem('sau_accounts')
  const accounts = ref<AccountItem[]>(savedAccs ? JSON.parse(savedAccs) : defaultAccounts)

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

  // 扫码/授权登录并加入分组
  const loginAccount = async (platform: string, account: string, group: string, headed: boolean = true) => {
    const res = await LoginAccount(platform, account, headed)
    let exist = accounts.value.find(a => a.platform === platform && a.account === account)
    if (!exist) {
      exist = { platform, account, group: group || '默认分组', checked: false }
      accounts.value.push(exist)
    } else {
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
