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

// 7. 待发布素材项 (Media Item)
export interface MediaItem {
  id: string
  filePath: string
  fileName: string
  fileSize?: string
  duration?: string
  format?: string
  parsedEpisode?: number
}

// 8. 矩阵单元格配置 (Matrix Cell Config)
export interface MatrixCellConfig {
  enabled: boolean            // 是否发布
  scheduleMode: 'immediate' | 'scheduled' | 'inherit' // 立即 / 独立定时 / 继承全局
  customSchedule?: string     // 独立定时时间 YYYY-MM-DD HH:mm
  customTitle?: string        // 单元格独立专属标题
  isCustomized: boolean       // 是否存在专属微调
  override: PlatformOverrideSetting // 平台专属差异化配置
}

// 9. 批量变量与规则配置 (Batch Rule Config)
export interface BatchRuleConfig {
  titleTemplate: string       // 如: "{视频名} - 第{集数}集"
  episodeMode?: 'auto' | 'sequence' // auto: 优先文件名智能识别; sequence: 强制按序号递增，默认 auto
  startEpisode?: number       // 起始集数，默认 1
  episodeStep?: number        // 集数递进步长，默认 1
  padZero?: boolean           // 是否补零 (如 01, 02)，默认 false
  scheduleType: 'immediate' | 'interval' | 'custom' // 统一立即 / 递增排期间隔 / 自定义
  startScheduleTime: string   // 递增起始时间
  intervalMinutes: number     // 递增发布间隔(分钟)，如 30
}

