import { ElMessage, ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import { engine } from '../../wailsjs/go/models'
import type { MasterForm, PlatformOverrideSetting, SelectedTargetAccount, BatchRuleConfig, MediaItem } from '../types/matrix'
import { resolveMediaTitle } from '../utils/matrixHelper'

export function useMatrixPublish() {
  const router = useRouter()
  const taskStore = useTaskStore()

  /**
   * 创建并入队矩阵发布任务批次 (精准三级级联参数解析: 账号定制 -> 平台定制 -> 全局主模板)
   */
  const createPublishBatch = (params: {
    selectedTargets: SelectedTargetAccount[]
    masterForm: MasterForm
    platformOverrides: Record<string, PlatformOverrideSetting>
    accountOverrides: Record<string, PlatformOverrideSetting>
    concurrency: number
    isHeadless: boolean
  }) => {
    const { selectedTargets, masterForm, platformOverrides, accountOverrides, concurrency, isHeadless } = params

    if (selectedTargets.length === 0) {
      ElMessage.warning('请至少勾选 1 个可用的目标矩阵账号')
      return null
    }

    if (masterForm.action === 'upload-video' && !masterForm.filePath) {
      ElMessage.warning('请先在左侧选择需要发布的本地视频文件')
      return null
    }

    if (masterForm.action === 'upload-note' && masterForm.images.length === 0) {
      ElMessage.warning('请先在左侧添加图文笔记图片素材')
      return null
    }

    // 组装每个账号独立下发的精准 CLI 参数
    const rawTasks: engine.AccountPublishTask[] = []

    for (const tgt of selectedTargets) {
      const platOv = platformOverrides[tgt.platform]
      const accKey = `${tgt.platform}:${tgt.account}`
      const accOv = accountOverrides[accKey]

      // 判断定制优先级
      const isAccCust = accOv && accOv.isCustomized
      const isPlatCust = platOv && platOv.isCustomized

      // 1. 标题 (账号 -> 平台 -> 全局)
      let finalTitle = masterForm.title.trim() || '无标题作品'
      if (isAccCust && accOv.title.trim()) {
        finalTitle = accOv.title.trim()
      } else if (isPlatCust && platOv.title.trim()) {
        finalTitle = platOv.title.trim()
      }

      // 2. 正文文案
      let finalDesc = masterForm.desc
      if (isAccCust && accOv.desc !== undefined && accOv.desc !== '') {
        finalDesc = accOv.desc
      } else if (isPlatCust && platOv.desc !== undefined && platOv.desc !== '') {
        finalDesc = platOv.desc
      }

      // 3. 标签
      let finalTags = masterForm.tags
      if (isAccCust && accOv.tags !== undefined && accOv.tags !== '') {
        finalTags = accOv.tags
      } else if (isPlatCust && platOv.tags !== undefined && platOv.tags !== '') {
        finalTags = platOv.tags
      }

      // 4. 主封面图
      let finalThumbnail = masterForm.thumbnail
      if (isAccCust && accOv.thumbnail) {
        finalThumbnail = accOv.thumbnail
      } else if (isPlatCust && platOv.thumbnail) {
        finalThumbnail = platOv.thumbnail
      }

      // 5. 发布时机
      let finalSchedule = masterForm.schedule
      if (isAccCust && accOv.schedule) {
        finalSchedule = accOv.schedule
      } else if (isPlatCust && platOv.schedule) {
        finalSchedule = platOv.schedule
      }

      // 6. 专属特性字段继承源 (优先取定制的账号，其次平台)
      const activeExclusive = isAccCust ? accOv : (isPlatCust ? platOv : null)

      const task = engine.AccountPublishTask.createFrom({
        platform: tgt.platform,
        account: tgt.account,
        nickname: tgt.nickname || tgt.account,
        action: masterForm.action,
        filePath: masterForm.filePath,
        images: masterForm.images,
        title: finalTitle,
        desc: finalDesc,
        tags: finalTags,
        thumbnail: finalThumbnail,
        thumbnailLandscape: activeExclusive ? activeExclusive.thumbnailLandscape : '',
        thumbnailPortrait: activeExclusive ? activeExclusive.thumbnailPortrait : '',
        tid: activeExclusive && activeExclusive.tid > 0 ? activeExclusive.tid : (tgt.platform === 'bilibili' ? 230 : 0),
        shortTitle: activeExclusive ? activeExclusive.shortTitle : '',
        category: activeExclusive ? activeExclusive.category : '',
        draft: activeExclusive ? activeExclusive.draft : false,
        schedule: finalSchedule,
        declaration: activeExclusive ? activeExclusive.declaration : '',
        collection: activeExclusive ? activeExclusive.collection : '',
        productLink: activeExclusive ? activeExclusive.productLink : '',
        productTitle: activeExclusive ? activeExclusive.productTitle : '',
        visibility: activeExclusive ? activeExclusive.visibility : '0',
        playlist: activeExclusive ? activeExclusive.playlist : '',
        bgm: activeExclusive ? activeExclusive.bgm : '',
        note: activeExclusive ? activeExclusive.note : '',
        notef: activeExclusive ? activeExclusive.notef : '',
        headless: isHeadless
      })

      rawTasks.push(task)
    }

    // 提取视频源文件名
    const videoFileName = masterForm.filePath ? masterForm.filePath.split(/[/\\]/).pop() || '' : ''
    const defaultBatchTitle = masterForm.title.trim() || (videoFileName ? videoFileName.replace(/\.[^/.]+$/, '') : '矩阵发布')
    const batchName = `${defaultBatchTitle.slice(0, 18)} (${rawTasks.length}个账号)`

    const batchId = taskStore.enqueueBatch({
      batchName,
      videoFileName,
      thumbnail: masterForm.thumbnail,
      rawTasks,
      concurrency
    })

    ElNotification({
      title: '🚀 矩阵发布任务已成功提交！',
      message: `已入队 [${batchName}]，包含 ${rawTasks.length} 个矩阵分发通道。系统将自动按最大 ${concurrency} 并发有序调度！`,
      type: 'success',
      duration: 4000
    })

    return batchId
  }

  /**
   * 基于【视频 × 账号】交叉透视矩阵，一次性组装多视频 × 多账号的多任务批次
   */
  const createCrossMatrixPublishBatch = (params: {
    mediaList: MediaItem[]
    selectedAccounts: Array<{ platform: string; account: string; nickname?: string }>
    matrixMap: Record<string, Record<string, any>>
    masterForm: MasterForm
    ruleConfig: any
    concurrency: number
    isHeadless: boolean
  }) => {
    const { mediaList, selectedAccounts, matrixMap, masterForm, ruleConfig, concurrency, isHeadless } = params

    if (mediaList.length === 0) {
      ElMessage.warning('请先在步骤 ① 添加至少 1 个待发布视频文件')
      return null
    }

    if (selectedAccounts.length === 0) {
      ElMessage.warning('请先在步骤 ② 勾选至少 1 个目标矩阵账号')
      return null
    }

    const rawTasks: engine.AccountPublishTask[] = []
    const todayStr = new Date().toISOString().split('T')[0]

    // 遍历每一个视频 × 每一个账号
    mediaList.forEach((media, mIdx) => {
      const ep = media.parsedEpisode || (mIdx + 1)
      const baseName = media.fileName.replace(/\.[^/.]+$/, '')

      selectedAccounts.forEach((acc) => {
        const accKey = `${acc.platform}:${acc.account}`
        const cell = matrixMap[media.id]?.[accKey]

        // 若未配置或被用户标记为不发布，则跳过
        if (cell && !cell.enabled) return

        // 1. 计算该单元格最终标题
        let finalTitle = ''
        if (cell?.customTitle?.trim()) {
          finalTitle = cell.customTitle.trim()
        } else {
          finalTitle = resolveMediaTitle(masterForm.title, media, mIdx, ruleConfig)
        }

        // 2. 计算描述与标签
        const finalDesc = cell?.override?.desc !== undefined && cell.override.desc !== ''
          ? cell.override.desc
          : masterForm.desc

        const finalTags = cell?.override?.tags !== undefined && cell.override.tags !== ''
          ? cell.override.tags
          : masterForm.tags

        // 3. 计算排期时间
        let finalSchedule = ''
        const schedMode = cell?.scheduleMode || 'inherit'

        if (schedMode === 'immediate') {
          finalSchedule = ''
        } else if (schedMode === 'scheduled' && cell?.customSchedule) {
          finalSchedule = cell.customSchedule
        } else {
          // 继承全局
          if (ruleConfig.scheduleType === 'immediate') {
            finalSchedule = ''
          } else if (ruleConfig.scheduleType === 'interval' && ruleConfig.startScheduleTime) {
            try {
              const start = new Date(ruleConfig.startScheduleTime.replace(/-/g, '/'))
              const offsetMs = mIdx * (ruleConfig.intervalMinutes || 30) * 60 * 1000
              const sched = new Date(start.getTime() + offsetMs)
              const y = sched.getFullYear()
              const m = String(sched.getMonth() + 1).padStart(2, '0')
              const d = String(sched.getDate()).padStart(2, '0')
              const h = String(sched.getHours()).padStart(2, '0')
              const min = String(sched.getMinutes()).padStart(2, '0')
              finalSchedule = `${y}-${m}-${d} ${h}:${min}`
            } catch (e) {
              finalSchedule = ''
            }
          } else if (ruleConfig.scheduleType === 'custom' && masterForm.schedule) {
            finalSchedule = masterForm.schedule
          }
        }

        const ov = cell?.override || {}

        const task = engine.AccountPublishTask.createFrom({
          platform: acc.platform,
          account: acc.account,
          nickname: acc.nickname || acc.account,
          action: 'upload-video',
          filePath: media.filePath,
          images: [],
          title: finalTitle || baseName,
          desc: finalDesc,
          tags: finalTags,
          thumbnail: ov.thumbnail || masterForm.thumbnail,
          thumbnailLandscape: ov.thumbnailLandscape || '',
          thumbnailPortrait: ov.thumbnailPortrait || '',
          tid: ov.tid > 0 ? ov.tid : (acc.platform === 'bilibili' ? 230 : 0),
          shortTitle: ov.shortTitle || '',
          category: ov.category || '',
          draft: ov.draft || false,
          schedule: finalSchedule,
          declaration: ov.declaration || '',
          collection: ov.collection || '',
          productLink: ov.productLink || '',
          productTitle: ov.productTitle || '',
          visibility: ov.visibility || 'public',
          playlist: ov.playlist || '',
          bgm: ov.bgm || '',
          note: ov.note || '',
          notef: ov.notef || '',
          headless: isHeadless
        })

        rawTasks.push(task)
      })
    })

    if (rawTasks.length === 0) {
      ElMessage.warning('矩阵中没有勾选任何有效的发布单元格')
      return null
    }

    const firstMediaName = mediaList[0]?.fileName?.replace(/\.[^/.]+$/, '') || '多视频矩阵'
    const batchName = `${firstMediaName} 等 ${mediaList.length} 个视频 (${rawTasks.length}次发布)`

    const batchId = taskStore.enqueueBatch({
      batchName,
      videoFileName: mediaList.map(m => m.fileName).join(', '),
      thumbnail: masterForm.thumbnail,
      rawTasks,
      concurrency
    })

    ElNotification({
      title: '🚀 批量矩阵发布任务已提交！',
      message: `已将 ${mediaList.length} 个视频、共 ${rawTasks.length} 次发布任务推入调度器，最大 ${concurrency} 并发执行中。`,
      type: 'success',
      duration: 4500
    })

    return batchId
  }

  return {
    createPublishBatch,
    createCrossMatrixPublishBatch
  }
}
