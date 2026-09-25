/**
 * 自媒体平台配置字典与元数据定义 (严格对齐 docs/api_specification.md 规范)
 */

export interface PlatformConfig {
  id: string
  name: string
  alias: string
  brandColor: string
  gradient: string
  supportsVideo: boolean
  supportsNote: boolean
  icon: string
  placeholder: string
}

export const PLATFORMS: PlatformConfig[] = [
  {
    id: 'douyin',
    name: '抖音',
    alias: 'Douyin',
    brandColor: '#000000',
    gradient: 'linear-gradient(135deg, #000000 0%, #262626 100%)',
    supportsVideo: true,
    supportsNote: true,
    icon: 'VideoCamera',
    placeholder: '抖音短视频创作与图文 (支持小黄车/合集)'
  },
  {
    id: 'xiaohongshu',
    name: '小红书',
    alias: 'XHS',
    brandColor: '#ff2442',
    gradient: 'linear-gradient(135deg, #ff2442 0%, #ff4d6a 100%)',
    supportsVideo: true,
    supportsNote: true,
    icon: 'Picture',
    placeholder: '小红书笔记与种草短视频'
  },
  {
    id: 'kuaishou',
    name: '快手',
    alias: 'Kuaishou',
    brandColor: '#FF4906',
    gradient: 'linear-gradient(135deg, #FF4906 0%, #ff8a00 100%)',
    supportsVideo: true,
    supportsNote: true,
    icon: 'Film',
    placeholder: '快手创作者服务 (短视频/图文/合集)'
  },
  {
    id: 'tencent',
    name: '视频号',
    alias: 'Channels',
    brandColor: '#FA9D3B',
    gradient: 'linear-gradient(135deg, #FA9D3B 0%, #ffb35c 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'ChatDotRound',
    placeholder: '视频号生态发布 (短标题/原创/草稿)'
  },
  {
    id: 'bilibili',
    name: 'B站',
    alias: 'Bilibili',
    brandColor: '#FB7299',
    gradient: 'linear-gradient(135deg, #FB7299 0%, #ff8fab 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'VideoPlay',
    placeholder: 'B站高清视频投稿 (需指定分区分类)'
  }
  // 暂时注释以下平台，仅保留：抖音、小红书、快手、视频号、B站
  /*
  ,
  {
    id: 'youtube',
    name: 'YouTube',
    alias: 'YouTube',
    brandColor: '#ff0000',
    gradient: 'linear-gradient(135deg, #ff0000 0%, #cc0000 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'Monitor',
    placeholder: 'YouTube 全球视频分发 (播放列表/公开性)'
  },
  {
    id: 'baijiahao',
    name: '百家号',
    alias: 'Baijiahao',
    brandColor: '#2932e1',
    gradient: 'linear-gradient(135deg, #2932e1 0%, #4e6ef2 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'Document',
    placeholder: '百度百家号创作平台'
  },
  {
    id: 'weibo',
    name: '微博视频',
    alias: 'Weibo',
    brandColor: '#e6162d',
    gradient: 'linear-gradient(135deg, #e6162d 0%, #ff5263 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'Share',
    placeholder: '新浪微博高清视频'
  },
  {
    id: 'alipay',
    name: '支付宝生活号',
    alias: 'Alipay',
    brandColor: '#1677ff',
    gradient: 'linear-gradient(135deg, #1677ff 0%, #4096ff 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'Wallet',
    placeholder: '支付宝生活号创作者中心'
  },
  {
    id: 'hupu',
    name: '虎扑',
    alias: 'Hupu',
    brandColor: '#c01e2f',
    gradient: 'linear-gradient(135deg, #c01e2f 0%, #e63946 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'Trophy',
    placeholder: '虎扑社区视频发布'
  }
  */
]

// B站常用分区字典 (严格对齐 B站创作者服务平台最新级联分类)
export const BILIBILI_PARTITIONS = [
  { id: 230, name: '科技数码 - 软件应用 / 计算机技术' },
  { id: 122, name: '科技数码 - 野生技术协会' },
  { id: 240, name: '人工智能 - 创新应用 / 前沿探索' },
  { id: 171, name: '游戏 - 电子竞技' },
  { id: 17,  name: '游戏 - 单机游戏' },
  { id: 21,  name: '生活经验 - 日常生活' },
  { id: 138, name: '生活经验 - 搞笑趣味' },
  { id: 163, name: '美食 - 美食制作' },
  { id: 217, name: '知识 - 科学科普' },
  { id: 201, name: '知识 - 商业财经' },
  { id: 157, name: '影视 - 影视剪辑' },
  { id: 130, name: '音乐 - 音乐综合' }
]

export const UNKNOWN_PLATFORM = (id: string): PlatformConfig => ({
  id, name: `未知平台(${id})`, alias: id, brandColor: '#94a3b8',
  gradient: 'linear-gradient(135deg, #64748b 0%, #94a3b8 100%)',
  supportsVideo: true, supportsNote: false, icon: 'QuestionFilled', placeholder: ''
})
export const getPlatformConfig = (id: string): PlatformConfig =>
  PLATFORMS.find(p => p.id === id) || UNKNOWN_PLATFORM(id)
