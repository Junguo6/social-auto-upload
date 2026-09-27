import type { MediaItem, BatchRuleConfig } from '../types/matrix'

/**
 * 智能从文件名中提取真实的短剧/视频分集编号
 * 过滤干扰项：清晰度(1080p)、总集数(80集全)、季/部(第1季)、日期年份(2024)、括号副本等
 */
export function parseEpisodeFromFileName(name: string): number | undefined {
  if (!name) return undefined

  // 1. 去掉文件扩展名 (如 .mp4)
  let clean = name.replace(/\.[a-zA-Z0-9]+$/, '')

  // 2. 剥除明确的干扰项（清晰度、全集/共X集、第X季、日期等）
  clean = clean
    .replace(/(?:1080|720|480|360|2160)p?/gi, ' ') // 1080p, 720p
    .replace(/(?:4k|2k|hd|uhd|fhd)/gi, ' ')        // 4k, hd
    .replace(/(?:共|全)\s*\d+\s*[集话期篇]/gi, ' ') // 全80集 / 共100集
    .replace(/\d+\s*[集话期篇]\s*(?:全|完)/gi, ' ') // 80集全 / 100集完
    .replace(/(?:第)?\s*\d+\s*[季部]/gi, ' ')       // 第1季 / 第2部
    .replace(/(?:19|20)\d{2}[-_.]?\d{2}[-_.]?\d{2}/g, ' ') // 2024-09-11
    .replace(/(?:19|20)\d{2}/g, ' ')               // 年份 2024

  // 3. 策略A: 显式集数标记 (如: 第01集 / 第1集 / ep01 / EP01 / E01 / 01集)
  const mKeyword = clean.match(/(?:^|[\s_#\-\[\(【（])(?:第|ep|EP|[Ee])\s*(\d{1,4})(?:[集话期篇]|[\s_#\-\]\)】）]|$)/) ||
                   clean.match(/第\s*(\d{1,4})\s*[集话期篇]?/)
  if (mKeyword && mKeyword[1]) {
    return parseInt(mKeyword[1], 10)
  }

  // 策略B: 数字紧跟“集/话/期/篇”
  const mSuffix = clean.match(/(\d{1,4})\s*[集话期篇]/)
  if (mSuffix && mSuffix[1]) {
    return parseInt(mSuffix[1], 10)
  }

  // 策略C: 括号/中括号内的纯数字 (如 【01】、[02]、(3))
  const mBrackets = clean.match(/[\[\(【（]\s*(\d{1,4})\s*[\]\)】）]/)
  if (mBrackets && mBrackets[1]) {
    return parseInt(mBrackets[1], 10)
  }

  // 策略D: 分隔符连接的数字 (如 _01, -02, #03, " 04")
  const mDelim = clean.match(/(?:[-_#\s])(\d{1,4})(?:[-_#\s]|$)/)
  if (mDelim && mDelim[1]) {
    return parseInt(mDelim[1], 10)
  }

  // 策略E: 文件名开头是数字且有分隔符 (如 01_短剧.mp4)
  const mStart = clean.match(/^(\d{1,4})(?:[-_#\s])/)
  if (mStart && mStart[1]) {
    return parseInt(mStart[1], 10)
  }

  // 策略F: 整个名字就是纯数字 (如 1.mp4, 02.mp4)
  const mPureNum = clean.match(/^(\d{1,4})$/)
  if (mPureNum && mPureNum[1]) {
    return parseInt(mPureNum[1], 10)
  }

  return undefined
}

/**
 * 统一根据规则计算目标视频的集数显示文本 (支持强制顺序自增与补零)
 */
export function resolveEpisodeNumber(
  media: { parsedEpisode?: number; fileName?: string },
  mediaIndex: number,
  ruleConfig?: Partial<BatchRuleConfig>
): string {
  const mode = ruleConfig?.episodeMode || 'sequence'
  const startEp = typeof ruleConfig?.startEpisode === 'number' && !isNaN(ruleConfig.startEpisode)
    ? ruleConfig.startEpisode
    : 1
  const step = typeof ruleConfig?.episodeStep === 'number' && !isNaN(ruleConfig.episodeStep)
    ? ruleConfig.episodeStep
    : 1
  const padZero = !!ruleConfig?.padZero

  let epNum: number

  if (mode === 'sequence') {
    // 强制顺序自增模式：第 index 个视频 = startEp + index * step
    epNum = startEp + mediaIndex * step
  } else {
    // 自动模式：优先使用高精度从当前文件名探测的集数 (防止旧代码被 .mp4 后缀污染存入 4)
    let detected: number | undefined = undefined
    if (media.fileName) {
      detected = parseEpisodeFromFileName(media.fileName)
    }

    if (detected !== undefined) {
      epNum = detected
    } else if (typeof media.parsedEpisode === 'number' && !isNaN(media.parsedEpisode) && media.parsedEpisode !== 4) {
      // 保留用户在第一步手动微调过的个性化集数
      epNum = media.parsedEpisode
    } else {
      // 兜底顺序编号
      epNum = startEp + mediaIndex * step
    }
  }

  if (padZero && epNum >= 0 && epNum < 10) {
    return `0${epNum}`
  }
  return String(epNum)
}

export interface AvailableVariable {
  key: string
  label: string
  desc: string
  sampleVal?: string
  isLevel?: boolean
}

export const AVAILABLE_VARIABLES: AvailableVariable[] = [
  { key: '{视频名}', label: '视频名', desc: '去后缀的文件名' },
  { key: '{集数}', label: '集数', desc: '智能提取/自增集数' },
  { key: '{序号}', label: '序号', desc: '视频在列表中的顺序 (1, 2...)' },
  { key: '{上级目录}', label: '上级目录', desc: '直接父文件夹名 (如剧名/集数)' },
  { key: '{根目录}', label: '根目录', desc: '素材库最外层根目录名' },
  { key: '{日期}', label: '日期', desc: '当前日期 (YYYY-MM-DD)' },
  { key: '{时间}', label: '时间', desc: '当前时间 (HH:mm)' },
]

/**
 * 根据第一步上传的真实视频素材与单位层级，动态构建精准可选变量列表
 */
export function buildDynamicVariables(
  sampleMedia?: { fileName?: string; filePath?: string; folderCrumbs?: string[]; parsedEpisode?: number },
  unitLevel?: number,
  ruleConfig?: Partial<BatchRuleConfig>
): AvailableVariable[] {
  const vars: AvailableVariable[] = []

  const fileName = sampleMedia?.fileName || '迟遇山野知秋_第01集.mp4'
  const baseName = fileName.replace(/\.[^/.]+$/, '')
  const ep = resolveEpisodeNumber({ parsedEpisode: sampleMedia?.parsedEpisode, fileName }, 0, ruleConfig)
  const crumbs = sampleMedia?.folderCrumbs || []

  // 1. 核心名称与集数
  vars.push({
    key: '{视频名}',
    label: '视频名',
    desc: '去扩展名的视频文件名',
    sampleVal: baseName
  })
  vars.push({
    key: '{集数}',
    label: '集数',
    desc: '智能提取或规则自增的集数编号',
    sampleVal: ep
  })

  // 2. 与第一步「上传视频」层级完全同步的多级目录变量
  if (crumbs.length > 0) {
    crumbs.forEach((crumbName, idx) => {
      const level = idx + 1
      vars.push({
        key: `{第${level}层目录}`,
        label: `第${level}层目录`,
        desc: `第一步上传划分的第 ${level} 层目录名称`,
        sampleVal: crumbName,
        isLevel: true
      })
    })

    // 若指定了分配单位层级 (unitLevel > 0)，单独提供「单位目录名」快捷变量
    if (typeof unitLevel === 'number' && unitLevel > 0 && crumbs.length >= unitLevel) {
      const unitName = crumbs[unitLevel - 1]
      vars.push({
        key: '{单位目录名}',
        label: `单位目录名(第${unitLevel}层)`,
        desc: `当前第 ${unitLevel} 层分配单位目录名 (对应表分组依据)`,
        sampleVal: unitName,
        isLevel: true
      })
    }

    // 上级目录与根目录快捷别名
    const parentFolder = crumbs[crumbs.length - 1]
    const rootFolder = crumbs[0]

    vars.push({
      key: '{上级目录}',
      label: '上级目录',
      desc: '视频所在的直接上级文件夹名',
      sampleVal: parentFolder,
      isLevel: true
    })

    if (crumbs.length > 1) {
      vars.push({
        key: '{根目录}',
        label: '根目录',
        desc: '素材库最外层顶级文件夹名',
        sampleVal: rootFolder,
        isLevel: true
      })
    }
  } else {
    // 兜底基础目录变量
    vars.push({
      key: '{上级目录}',
      label: '上级目录',
      desc: '视频所在的直接上级文件夹名',
      sampleVal: '默认目录'
    })
    vars.push({
      key: '{根目录}',
      label: '根目录',
      desc: '素材最外层根目录名',
      sampleVal: '素材库'
    })
  }

  // 3. 通用序号与日期时间
  vars.push({
    key: '{序号}',
    label: '序号',
    desc: '视频在列表中的顺位数字 (从 1 开始)',
    sampleVal: '1'
  })
  vars.push({
    key: '{日期}',
    label: '日期',
    desc: '发布当天日期 (YYYY-MM-DD)',
    sampleVal: new Date().toISOString().slice(0, 10)
  })
  vars.push({
    key: '{时间}',
    label: '时间',
    desc: '当前时间 (HH:mm)',
    sampleVal: `${String(new Date().getHours()).padStart(2, '0')}:${String(new Date().getMinutes()).padStart(2, '0')}`
  })

  return vars
}

/**
 * 从媒体对象中提取父级文件夹名与根目录名
 */
export function extractFolderNames(media: { folderCrumbs?: string[]; filePath?: string }): { folderName: string; rootFolder: string } {
  if (media.folderCrumbs && media.folderCrumbs.length > 0) {
    const folderName = media.folderCrumbs[media.folderCrumbs.length - 1] || ''
    const rootFolder = media.folderCrumbs[0] || ''
    return { folderName, rootFolder }
  }

  if (media.filePath) {
    const norm = media.filePath.replace(/\\/g, '/')
    const dir = norm.substring(0, norm.lastIndexOf('/'))
    if (dir) {
      const parts = dir.split('/').filter(Boolean)
      if (parts.length > 0) {
        const folderName = parts[parts.length - 1] || ''
        let rootCandidate = parts[0]
        if (parts.length >= 3 && (rootCandidate.endsWith(':') || rootCandidate === 'Users' || rootCandidate === 'home')) {
          rootCandidate = parts[parts.length - 1]
        }
        return { folderName, rootFolder: rootCandidate || folderName }
      }
    }
  }

  return { folderName: '默认目录', rootFolder: '素材库' }
}

/**
 * 统一模板字符串变量解析器 (支持标题、描述、短标题、合集、剧集、活动等)
 */
export function resolveTemplateString(
  template: string,
  media: { parsedEpisode?: number; fileName?: string; filePath?: string; folderCrumbs?: string[] },
  mediaIndex: number = 0,
  ruleConfig?: Partial<BatchRuleConfig>,
  unitLevel?: number
): string {
  if (!template) return ''

  const fileName = media.fileName || (media.filePath ? media.filePath.split(/[/\\]/).pop() || '' : '视频')
  const epStr = resolveEpisodeNumber({ parsedEpisode: media.parsedEpisode, fileName }, mediaIndex, ruleConfig)
  const baseName = fileName.replace(/\.[^/.]+$/, '')
  
  const crumbs = media.folderCrumbs || []
  const { folderName, rootFolder } = extractFolderNames(media)
  
  const now = new Date()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  const orderNumStr = String(mediaIndex + 1)

  let result = template
    .replace(/\{视频名\}/g, baseName)
    .replace(/\{文件名\}/g, baseName)
    .replace(/\{视频全名\}/g, fileName)
    .replace(/\{集数\}/g, epStr)
    .replace(/\{序号\}/g, orderNumStr)
    .replace(/\{日期\}/g, todayStr)
    .replace(/\{时间\}/g, timeStr)
    .replace(/\{文件夹名\}/g, folderName)
    .replace(/\{上级目录\}/g, folderName)
    .replace(/\{父目录\}/g, folderName)
    .replace(/\{根目录\}/g, rootFolder)

  // 支持当前分配单位层级目录名
  if (typeof unitLevel === 'number' && unitLevel > 0 && crumbs.length >= unitLevel) {
    const unitName = crumbs[unitLevel - 1] || ''
    result = result
      .replace(/\{单位目录名\}/g, unitName)
      .replace(/\{单位目录\}/g, unitName)
      .replace(/\{分组目录名\}/g, unitName)
  }

  // 动态解析 {第1层目录} ... {第N层目录}
  for (let i = 0; i < 10; i++) {
    const level = i + 1
    const val = crumbs[i] || (level === 1 ? rootFolder : '')
    const re1 = new RegExp(`\\{第${level}层目录\\}`, 'g')
    const re2 = new RegExp(`\\{第${level}级目录\\}`, 'g')
    const re3 = new RegExp(`\\{第${level}层文件夹\\}`, 'g')
    const re4 = new RegExp(`\\{第${level}级文件夹\\}`, 'g')
    result = result.replace(re1, val).replace(re2, val).replace(re3, val).replace(re4, val)
  }

  return result
}

/**
 * 统一根据规则生成视频的最终主标题
 */
export function resolveMediaTitle(
  template: string,
  media: { parsedEpisode?: number; fileName: string; filePath?: string; folderCrumbs?: string[] },
  mediaIndex: number = 0,
  ruleConfig?: Partial<BatchRuleConfig>,
  unitLevel?: number
): string {
  const tpl = template.trim() || media.fileName
  return resolveTemplateString(tpl, media, mediaIndex, ruleConfig, unitLevel)
}
