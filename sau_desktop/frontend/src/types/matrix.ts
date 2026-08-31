/**
 * 全景矩阵发布工作台核心数据模型与类型定义
 */

// 1. 全局基础主模板表单模型 (Master Form)
export interface MasterForm {
  action: 'upload-video' | 'upload-note'
  filePath: string
  images: string[]
  title: string
  desc: string
  tags: string
  thumbnail: string
  schedule: string
}

// 2. 单平台 / 单账号独立覆盖定制参数模型 (Override Setting)
export interface PlatformOverrideSetting {
  isCustomized: boolean
  title: string
  desc: string
  tags: string
  thumbnail: string
  thumbnailLandscape: string
  thumbnailPortrait: string
  tid: number
  shortTitle: string
  category: string
  draft: boolean
  schedule: string
  declaration: string
  collection: string
  productLink: string
  productTitle: string
  visibility: string
  playlist: string
  bgm: string
  note: string
  notef: string
}

// 3. 矩阵预设持久化模板 (Preset)
export interface MatrixPreset {
  id: string
  name: string
  createdAt: string
  master: MasterForm
  platformOverrides: Record<string, PlatformOverrideSetting>
  accountOverrides: Record<string, PlatformOverrideSetting>
}

// 4. 目标已选账号项
export interface SelectedTargetAccount {
  platform: string
  account: string
  nickname?: string
}

// 5. 实时标准输出终端日志项
export interface LiveLogItem {
  time: string
  type: string
  message: string
}

// 6. 多账号一键同步选项模型 (Sync Options)
export interface SyncConfigFields {
  title: boolean
  desc: boolean
  tags: boolean
  thumbnail: boolean
  schedule: boolean
  platformExclusive: boolean
}
