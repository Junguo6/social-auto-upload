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
  const mode = ruleConfig?.episodeMode || 'auto'
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

/**
 * 统一根据规则生成视频的最终主标题
 */
export function resolveMediaTitle(
  template: string,
  media: { parsedEpisode?: number; fileName: string },
  mediaIndex: number,
  ruleConfig?: Partial<BatchRuleConfig>
): string {
  const tpl = template.trim() || media.fileName
  const epStr = resolveEpisodeNumber(media, mediaIndex, ruleConfig)
  const baseName = media.fileName.replace(/\.[^/.]+$/, '')
  const todayStr = new Date().toISOString().split('T')[0]

  return tpl
    .replace(/\{集数\}/g, epStr)
    .replace(/\{视频名\}/g, baseName)
    .replace(/\{日期\}/g, todayStr)
}
