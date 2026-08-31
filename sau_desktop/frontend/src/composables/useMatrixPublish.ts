import { ElMessage, ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import { engine } from '../../wailsjs/go/models'
import type { MasterForm, PlatformOverrideSetting, SelectedTargetAccount } from '../types/matrix'

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
      title: '发布任务已创建',
      message: `已将 ${rawTasks.length} 个账号的发布任务加入后台执行队列（已按防风控策略智能分流）。点击可前往「任务管理中心」查看实时进度。`,
      type: 'success',
      duration: 4500,
      onClick: () => {
        router.push('/tasks')
      }
    })

    return batchId
  }

  return {
    createPublishBatch
  }
}
