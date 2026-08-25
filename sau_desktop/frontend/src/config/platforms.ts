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
    brandColor: '#fe2c55',
    gradient: 'linear-gradient(135deg, #fe2c55 0%, #ff0050 100%)',
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
    brandColor: '#ff5000',
    gradient: 'linear-gradient(135deg, #ff5000 0%, #ff8a00 100%)',
    supportsVideo: true,
    supportsNote: true,
    icon: 'Film',
    placeholder: '快手创作者服务 (短视频/图文/合集)'
  },
  {
    id: 'tencent',
    name: '微信视频号',
    alias: 'Channels',
    brandColor: '#07c160',
    gradient: 'linear-gradient(135deg, #07c160 0%, #10d870 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'ChatDotRound',
    placeholder: '微信视频号生态发布 (短标题/原创/草稿)'
  },
  {
    id: 'bilibili',
    name: '哔哩哔哩',
    alias: 'Bilibili',
    brandColor: '#00aeec',
    gradient: 'linear-gradient(135deg, #00aeec 0%, #2acaff 100%)',
    supportsVideo: true,
    supportsNote: false,
    icon: 'VideoPlay',
    placeholder: 'B站高清视频投稿 (需指定分区分类)'
  },
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
]

// B站常用分区字典
export const BILIBILI_PARTITIONS = [
  { id: 230, name: '科技 - 软件应用/计算机技术' },
  { id: 122, name: '科技 - 野生技术协会' },
  { id: 171, name: '游戏 - 电子竞技' },
  { id: 21, name: '生活 - 日常' },
  { id: 138, name: '生活 - 搞笑' },
  { id: 163, name: '生活 - 美食制作' },
  { id: 217, name: '知识 - 科学科普' },
  { id: 201, name: '知识 - 商业财经' }
]

export const getPlatformConfig = (id: string): PlatformConfig => {
  return PLATFORMS.find(p => p.id === id) || PLATFORMS[0]
}
