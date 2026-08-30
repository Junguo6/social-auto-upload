<template>
  <div class="publish-workspace">
    <!-- 顶部步骤指示器 (Step Wizard) -->
    <div class="steps-nav glass-card">
      <div 
        class="step-item" 
        :class="{ active: currentStep === 1, done: currentStep > 1 }"
        @click="currentStep = 1"
      >
        <div class="step-num">1</div>
        <div class="step-text">
          <div class="step-title">编辑素材与文案</div>
          <div class="step-sub">媒体选择、标题、标签与封面</div>
        </div>
      </div>
      <div class="step-divider"></div>

      <div 
        class="step-item" 
        :class="{ active: currentStep === 2, done: currentStep > 2 }"
        @click="currentStep = 2"
      >
        <div class="step-num">2</div>
        <div class="step-text">
          <div class="step-title">选择矩阵发布目标</div>
          <div class="step-sub">按分组/平台勾选矩阵账号 (已选 {{ selectedTargets.length }} 个)</div>
        </div>
      </div>
      <div class="step-divider"></div>

      <div 
        class="step-item" 
        :class="{ active: currentStep === 3, done: currentStep === 3 }"
        @click="publishStore.isPublishing && (currentStep = 3)"
      >
        <div class="step-num">3</div>
        <div class="step-text">
          <div class="step-title">并发执行与监控</div>
          <div class="step-sub">实时并发调度与发布结果</div>
        </div>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- STEP 1: 作品素材与文案配置 (沉浸式全宽编辑区) -->
    <!-- ========================================================================= -->
    <div v-show="currentStep === 1" class="step-content">
      <div class="step-cards-container">
        <!-- 1.1 媒体素材卡片 -->
        <el-card class="glass-card full-card">
          <template #header>
            <div class="card-header-flex">
              <div class="header-title">
                <el-icon><Film /></el-icon>
                <span>作品媒体类型与文件</span>
              </div>
              <el-button size="small" type="info" link @click="fillDemoData">一键载入演示作品</el-button>
            </div>
          </template>

          <div class="media-type-row">
            <div 
              class="type-box" 
              :class="{ active: form.action === 'upload-video' }"
              @click="form.action = 'upload-video'"
            >
              <div class="type-box-icon"><el-icon><VideoCamera /></el-icon></div>
              <div class="type-box-info">
                <div class="title">高清短视频</div>
                <div class="desc">支持 MP4, MOV, MKV 等主流高清视频</div>
              </div>
            </div>

            <div 
              class="type-box" 
              :class="{ active: form.action === 'upload-note' }"
              @click="form.action = 'upload-note'"
            >
              <div class="type-box-icon"><el-icon><Picture /></el-icon></div>
              <div class="type-box-info">
                <div class="title">图文笔记</div>
                <div class="desc">支持 PNG, JPG 等多图轮播笔记</div>
              </div>
            </div>
          </div>

          <!-- 视频选择区 -->
          <div class="file-zone" v-if="form.action === 'upload-video'">
            <div class="file-picked-card" v-if="form.filePath">
              <div class="picked-icon"><el-icon><VideoPlay /></el-icon></div>
              <div class="picked-meta">
                <span class="file-name">{{ getFileName(form.filePath) }}</span>
                <span class="file-path">{{ form.filePath }}</span>
              </div>
              <div class="picked-actions">
                <el-button size="small" type="primary" plain @click="selectVideoFile">更换文件</el-button>
                <el-button size="small" type="danger" link @click="form.filePath = ''">清除</el-button>
              </div>
            </div>

            <div class="upload-dropzone" v-else @click="selectVideoFile">
              <el-icon class="drop-icon"><UploadFilled /></el-icon>
              <div class="drop-text">点击浏览并选择本地待发布的视频文件</div>
              <div class="drop-tip">支持直接读取本地绝对路径，无需压缩上传</div>
            </div>
          </div>

          <!-- 图文选择区 -->
          <div class="file-zone" v-else>
            <el-input 
              v-model="form.imagesText" 
              placeholder="输入图片绝对路径（多张图片使用英文逗号分隔）"
            >
              <template #append>
                <el-button @click="selectImageFile">
                  <el-icon><FolderOpened /></el-icon>
                  <span>选择素材图片</span>
                </el-button>
              </template>
            </el-input>
          </div>
        </el-card>

        <!-- 1.2 标题与文案 -->
        <el-card class="glass-card full-card">
          <template #header>
            <div class="header-title">
              <el-icon><EditPen /></el-icon>
              <span>标题、描述文案与热门话题</span>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="作品标题">
              <el-input 
                v-model="form.title" 
                maxlength="80" 
                show-word-limit 
                placeholder="输入吸引眼球的作品标题 (抖音/小红书≤30字，快手/视频号≤50字，B站≤80字)..." 
              />
            </el-form-item>

            <el-form-item label="作品正文描述 / 文案 (B站投稿为必填简介)">
              <el-input 
                v-model="form.desc" 
                type="textarea" 
                :rows="4" 
                placeholder="输入详细的视频描述、简介、或小红书正文笔记文案..." 
              />
            </el-form-item>

            <el-form-item label="热门话题标签 (Tags)">
              <el-input 
                v-model="form.tags" 
                placeholder="英文逗号分隔，例如: AI工具,自动发布,干货分享" 
              />
              <div class="quick-tags">
                <span class="quick-tags-label">推荐快捷话题：</span>
                <el-tag 
                  v-for="tag in presetTags" 
                  :key="tag" 
                  size="small" 
                  class="clickable-tag"
                  @click="appendTag(tag)"
                >
                  #{{ tag }}
                </el-tag>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 1.3 定时发布与合规声明 -->
        <el-card class="glass-card full-card">
          <template #header>
            <div class="header-title">
              <el-icon><Calendar /></el-icon>
              <span>定时发布与合规标记</span>
            </div>
          </template>

          <div class="params-grid">
            <div class="param-row">
              <div class="param-label-box">
                <span class="title">定时发布时间 (可选)</span>
                <span class="sub">留空为立即自动发布；选择时间将自动开启平台定时发布</span>
              </div>
              <el-date-picker
                v-model="form.schedule"
                type="datetime"
                placeholder="选择定时时间 (留空为立即发布)"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 240px"
              ></el-date-picker>
            </div>

            <div class="param-row">
              <div class="param-label-box">
                <span class="title">AI 内容生成声明</span>
                <span class="sub">符合各大平台的合规标记要求</span>
              </div>
              <el-select v-model="form.declaration" style="width: 220px">
                <el-option label="声明内容由 AI 生成" value="内容由AI生成" />
                <el-option label="自主原创声明" value="原创作品" />
                <el-option label="不特别声明" value="" />
              </el-select>
            </div>
          </div>
        </el-card>

        <!-- 1.4 高级封面与平台特有配置 (折叠) -->
        <el-card class="glass-card full-card">
          <template #header>
            <div class="card-header-flex toggle-title" @click="showAdvanced = !showAdvanced">
              <div class="header-title">
                <el-icon><Operation /></el-icon>
                <span>自定义封面与平台特定扩展属性 (可选)</span>
              </div>
              <el-icon class="arrow-icon">{{ showAdvanced ? '▼' : '▶' }}</el-icon>
            </div>
          </template>

          <div v-show="showAdvanced" class="advanced-body">
            <div class="sub-group-title">🖼️ 自定义封面设置</div>
            <div class="params-grid">
              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">通用主封面图</span>
                  <span class="sub">{{ form.thumbnail || '未指定主封面图片' }}</span>
                </div>
                <el-button size="small" plain @click="selectThumbnailFile('main')">选择封面</el-button>
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">横版封面 (抖音/视频号)</span>
                  <span class="sub">{{ form.thumbnailLandscape || '未指定' }}</span>
                </div>
                <el-button size="small" plain @click="selectThumbnailFile('landscape')">选择横版</el-button>
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">竖版封面 (抖音/视频号)</span>
                  <span class="sub">{{ form.thumbnailPortrait || '未指定' }}</span>
                </div>
                <el-button size="small" plain @click="selectThumbnailFile('portrait')">选择竖版</el-button>
              </div>
            </div>

            <div class="sub-group-title" style="margin-top: 18px;">🎯 平台专属扩展配置</div>
            <div class="params-grid">
              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">B站投稿分区分类 (TID)</span>
                  <span class="sub">分发至哔哩哔哩时生效</span>
                </div>
                <el-select v-model="form.tid" style="width: 240px">
                  <el-option 
                    v-for="part in BILIBILI_PARTITIONS" 
                    :key="part.id" 
                    :label="part.name" 
                    :value="part.id" 
                  />
                </el-select>
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">微信视频号特有短标题</span>
                  <span class="sub">用于视频号流式卡片短标题</span>
                </div>
                <el-input v-model="form.shortTitle" placeholder="例如: 爆款AI神器" style="width: 220px" />
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">视频号存为草稿</span>
                  <span class="sub">仅上传至草稿箱，不立即公开发布</span>
                </div>
                <el-switch v-model="form.draft" active-text="存为草稿" />
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">抖音小黄车带货商品链接</span>
                  <span class="sub">挂载商品链接 URL</span>
                </div>
                <el-input v-model="form.productLink" placeholder="商品详情 URL..." style="width: 260px" />
              </div>

              <div class="param-row">
                <div class="param-label-box">
                  <span class="title">专栏/合集名称</span>
                  <span class="sub">抖音/快手/视频号/百家号专栏</span>
                </div>
                <el-input v-model="form.collection" placeholder="合集名称..." style="width: 200px" />
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 步骤1底部导航 -->
      <div class="bottom-action-bar glass-card">
        <div class="action-summary">
          <span class="summary-title">{{ form.title || '（尚未填写标题）' }}</span>
          <span class="summary-file">{{ form.filePath ? getFileName(form.filePath) : '未选文件' }}</span>
        </div>
        <el-button type="primary" class="gradient-btn next-btn" @click="goToStep2">
          <span>下一步：选择矩阵发布目标</span>
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- STEP 2: 沉浸式矩阵目标账号选择 (全宽 Grid 卡片大看板) -->
    <!-- ========================================================================= -->
    <div v-show="currentStep === 2" class="step-content">
      <el-card class="glass-card full-card matrix-picker-card">
        <template #header>
          <div class="card-header-flex">
            <div class="header-title">
              <el-icon><Connection /></el-icon>
              <span>选择本次分发的矩阵目标账号</span>
            </div>
            <div class="header-meta-badge">
              <el-tag size="default" type="primary" effect="dark" round>
                已选中 {{ selectedTargets.length }} 个矩阵账号
              </el-tag>
            </div>
          </div>
        </template>

        <!-- 快速过滤与分组一键勾选工具条 -->
        <div class="matrix-toolbar">
          <div class="toolbar-section">
            <span class="toolbar-label">按矩阵分组一键选择：</span>
            <div class="btn-group">
              <el-button size="small" type="primary" plain @click="selectAllAccounts">
                全选全部账号
              </el-button>
              <el-button 
                v-for="grp in accountStore.groups" 
                :key="grp"
                size="small" 
                plain
                @click="selectByGroup(grp)"
              >
                {{ grp }}
              </el-button>
              <el-button size="small" type="danger" link @click="selectedTargets = []">
                清空所选
              </el-button>
            </div>
          </div>

          <div class="toolbar-section">
            <span class="toolbar-label">按平台一键勾选：</span>
            <div class="btn-group">
              <el-button 
                v-for="plat in activePlatformsInAccounts" 
                :key="plat.id"
                size="small" 
                plain
                @click="selectByPlatform(plat.id)"
              >
                {{ plat.name }}
              </el-button>
            </div>
          </div>
        </div>

        <!-- 账号全宽大网格 (Matrix Grid) -->
        <div class="matrix-cards-grid">
          <div 
            v-for="acc in accountStore.accounts" 
            :key="acc.platform + acc.account"
            class="matrix-acc-card glass-card"
            :class="{ selected: isTargetSelected(acc.platform, acc.account) }"
            @click="toggleTarget(acc.platform, acc.account)"
          >
            <div class="card-left">
              <el-checkbox 
                :model-value="isTargetSelected(acc.platform, acc.account)" 
                @click.stop="toggleTarget(acc.platform, acc.account)"
              />
              <div class="plat-badge-lg" :style="{ background: getPlatformStyle(acc.platform).gradient }">
                <el-icon><component :is="getPlatformStyle(acc.platform).icon" /></el-icon>
              </div>
            </div>

            <div class="card-mid">
              <div class="acc-title-row">
                <span class="acc-name-text">{{ acc.nickname || acc.account }}</span>
                <el-tag size="small" type="info" class="grp-badge">{{ acc.group || '默认分组' }}</el-tag>
              </div>
              <div class="acc-sub-row">
                <span class="plat-tag-text">{{ getPlatformStyle(acc.platform).name }}</span>
                <span class="status-indicator-text" :class="acc.isValid ? 'valid' : 'invalid'">
                  ● {{ acc.checked ? (acc.isValid ? '凭证就绪' : '凭证失效') : '待检测' }}
                </span>
              </div>
            </div>


            <div class="card-right-check">
              <el-icon v-if="isTargetSelected(acc.platform, acc.account)" class="check-icon"><CircleCheckFilled /></el-icon>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 步骤2底部导航 -->
      <div class="bottom-action-bar glass-card">
        <el-button size="default" plain @click="currentStep = 1">
          <el-icon><ArrowLeft /></el-icon>
          <span>上一步：修改作品内容</span>
        </el-button>

        <div class="action-summary">
          <span>共勾选 <strong class="highlight">{{ selectedTargets.length }}</strong> 个账号</span>
          <span class="dot">·</span>
          <span>并发数: <strong>{{ settingsStore.settings.concurrency }}</strong> 窗口</span>
        </div>

        <el-button 
          type="primary" 
          class="gradient-btn publish-btn-lg" 
          :loading="publishStore.isPublishing" 
          @click="handleStartPublish"
        >
          <el-icon><Promotion /></el-icon>
          <span>启动矩阵并发批量发布 🚀</span>
        </el-button>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- STEP 3: 并发执行大盘看板 (实时状态监控) -->
    <!-- ========================================================================= -->
    <div v-show="currentStep === 3" class="step-content">
      <el-card class="glass-card full-card status-dashboard-card">
        <template #header>
          <div class="card-header-flex">
            <div class="header-title">
              <el-icon><Loading v-if="publishStore.isPublishing" class="is-loading" /><CircleCheck v-else /></el-icon>
              <span>{{ publishStore.isPublishing ? '矩阵并发发布执行中...' : '矩阵发布批次执行完成' }}</span>
            </div>
            <div class="header-actions">
              <el-button 
                v-if="publishStore.isPublishing" 
                size="small" 
                type="danger" 
                plain 
                @click="publishStore.cancelPublish"
              >
                中止全部任务
              </el-button>
              <el-button 
                v-else 
                size="small" 
                type="primary" 
                class="gradient-btn" 
                @click="currentStep = 1"
              >
                再发一条作品
              </el-button>
            </div>
          </div>
        </template>

        <!-- 批次状态汇总统计 -->
        <div class="batch-summary-banner">
          <div class="banner-item">
            <span class="num">{{ selectedTargets.length }}</span>
            <span class="label">目标发布总数</span>
          </div>
          <div class="banner-item success">
            <span class="num">{{ getSuccessCount() }}</span>
            <span class="label">已发布成功</span>
          </div>
          <div class="banner-item fail">
            <span class="num">{{ getFailedCount() }}</span>
            <span class="label">异常/失败</span>
          </div>
          <div class="banner-item running">
            <span class="num">{{ getRunningCount() }}</span>
            <span class="label">调度执行中</span>
          </div>
        </div>

        <!-- 各账号执行状态卡片列表 -->
        <div class="execution-grid">
          <div 
            v-for="tgt in selectedTargets" 
            :key="tgt.platform + tgt.account"
            class="exec-acc-card glass-card"
            :class="getAccountExecStatus(tgt.platform, tgt.account)"
          >
            <div class="exec-card-top">
              <div class="plat-mini-badge" :style="{ background: getPlatformStyle(tgt.platform).gradient }">
                <el-icon><component :is="getPlatformStyle(tgt.platform).icon" /></el-icon>
              </div>
              <div class="exec-meta">
                <div class="exec-name">{{ getAccountDisplayName(tgt.platform, tgt.account) }}</div>
                <div class="exec-plat">{{ getPlatformStyle(tgt.platform).name }}</div>
              </div>
              <div class="exec-state-badge">

                <el-tag 
                  size="small" 
                  :type="getAccountStateTagType(tgt.platform, tgt.account)"
                >
                  {{ getAccountStateText(tgt.platform, tgt.account) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 步骤3底部导航 -->
      <div class="bottom-action-bar glass-card">
        <el-button size="default" plain @click="currentStep = 2">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回选择目标</span>
        </el-button>
        <div class="action-summary">
          <span>详细底层输出可在下方控制台查看</span>
        </div>
        <el-button 
          size="default" 
          type="primary" 
          class="gradient-btn" 
          @click="currentStep = 1"
        >
          返回重新创作
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { PLATFORMS, BILIBILI_PARTITIONS, getPlatformConfig } from '../config/platforms'
import { usePublishStore } from '../stores/publishStore'
import { useAccountStore } from '../stores/accountStore'
import { useSettingsStore } from '../stores/settingsStore'
import { SelectLocalFile } from '../../wailsjs/go/main/App'

const publishStore = usePublishStore()
const accountStore = useAccountStore()
const settingsStore = useSettingsStore()

const currentStep = ref(1)
const showAdvanced = ref(false)
const presetTags = ['AI工具', '自动发布', '自媒体运营', '效率神器', '科技生活', '爆款干货']

const form = reactive({
  action: 'upload-video',
  filePath: '',
  imagesText: '',
  title: '',
  desc: '',
  tags: 'AI工具,自动发布,干货分享',
  schedule: '',
  declaration: settingsStore.settings.declaration || '内容由AI生成',
  thumbnail: '',
  thumbnailLandscape: '',
  thumbnailPortrait: '',
  tid: 230,
  shortTitle: '',
  category: '',
  draft: false,
  collection: '',
  productLink: '',
  productTitle: '',
  visibility: 'public',
  playlist: '',
  bgm: '',
  note: ''
})

const selectedTargets = ref<Array<{ platform: string; account: string }>>([
  { platform: 'douyin', account: 'test_account' }
])

// 统计账号列表中存在哪些平台
const activePlatformsInAccounts = computed(() => {
  const platIds = Array.from(new Set(accountStore.accounts.map(a => a.platform)))
  return PLATFORMS.filter(p => platIds.includes(p.id))
})

const isTargetSelected = (platform: string, account: string) => {
  return selectedTargets.value.some(t => t.platform === platform && t.account === account)
}

const toggleTarget = (platform: string, account: string) => {
  const idx = selectedTargets.value.findIndex(t => t.platform === platform && t.account === account)
  if (idx >= 0) {
    selectedTargets.value.splice(idx, 1)
  } else {
    selectedTargets.value.push({ platform, account })
  }
}

const selectAllAccounts = () => {
  selectedTargets.value = accountStore.accounts.map(a => ({ platform: a.platform, account: a.account }))
  ElMessage.success(`已全选 ${selectedTargets.value.length} 个矩阵账号`)
}

const selectByGroup = (groupName: string) => {
  const grpAccs = accountStore.accounts.filter(a => a.group === groupName)
  selectedTargets.value = grpAccs.map(a => ({ platform: a.platform, account: a.account }))
  ElMessage.success(`已选中「${groupName}」下的 ${selectedTargets.value.length} 个账号`)
}

const selectByPlatform = (platformId: string) => {
  const platAccs = accountStore.accounts.filter(a => a.platform === platformId)
  selectedTargets.value = platAccs.map(a => ({ platform: a.platform, account: a.account }))
  const platName = getPlatformConfig(platformId).name
  ElMessage.success(`已选中 ${platName} 的 ${selectedTargets.value.length} 个账号`)
}

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getAccountDisplayName = (platform: string, account: string) => {
  const acc = accountStore.accounts.find(a => a.platform === platform && a.account === account)
  return acc?.nickname || account
}


const getFileName = (path: string) => {
  if (!path) return ''
  const parts = path.split(/[\/\\]/)
  return parts[parts.length - 1]
}

const appendTag = (tag: string) => {
  if (!form.tags) {
    form.tags = tag
  } else if (!form.tags.includes(tag)) {
    form.tags = `${form.tags}, ${tag}`
  }
}

const fillDemoData = () => {
  form.action = 'upload-video'
  form.filePath = 'videos/demo.mp4'
  form.title = 'Wails 矩阵自动化批量发布演示作品'
  form.desc = '基于 Go 协程高并发池驱动的多账号多平台一键并发分发体验！'
  form.tags = 'AI工具,自动发布,自媒体运营'
  selectAllAccounts()
  ElMessage.success('已载入演示作品数据')
}

const selectVideoFile = async () => {
  try {
    const path = await SelectLocalFile('选择发布视频文件', ['*.mp4', '*.mov', '*.mkv'])
    if (path) {
      form.filePath = path
    }
  } catch (err: any) {
    ElMessage.error('选择文件失败: ' + err)
  }
}

const selectImageFile = async () => {
  try {
    const path = await SelectLocalFile('选择素材图片', ['*.png', '*.jpg', '*.jpeg'])
    if (path) {
      form.imagesText = form.imagesText ? `${form.imagesText}, ${path}` : path
    }
  } catch (err: any) {
    ElMessage.error('选择图片失败: ' + err)
  }
}

const selectThumbnailFile = async (type: 'main' | 'landscape' | 'portrait') => {
  try {
    const path = await SelectLocalFile('选择封面图片', ['*.png', '*.jpg', '*.jpeg'])
    if (path) {
      if (type === 'main') form.thumbnail = path
      else if (type === 'landscape') form.thumbnailLandscape = path
      else if (type === 'portrait') form.thumbnailPortrait = path
      ElMessage.success('封面图片已选择')
    }
  } catch (err: any) {
    ElMessage.error('选择封面失败: ' + err)
  }
}

const goToStep2 = () => {
  if (form.action === 'upload-video' && !form.filePath) {
    ElMessage.warning('请先选择要发布的视频文件')
    return
  }
  if (!form.title) {
    ElMessage.warning('请先输入作品标题')
    return
  }
  currentStep.value = 2
}

const handleStartPublish = async () => {
  if (selectedTargets.value.length === 0) {
    ElMessage.warning('请至少勾选一个矩阵发布目标账号')
    return
  }

  // 针对 B站 投稿的必填校验
  const hasBilibili = selectedTargets.value.some(t => t.platform === 'bilibili')
  if (hasBilibili && !form.desc) {
    ElMessage.warning('已选账号包含 B 站投稿，必须填写作品描述/简介')
    currentStep.value = 1
    return
  }

  const concurrency = settingsStore.settings.concurrency || 3
  const headless = settingsStore.settings.headless

  currentStep.value = 3 // 自动切到执行监控大盘

  let imagesList: string[] = []
  if (form.action === 'upload-note' && form.imagesText) {
    imagesList = form.imagesText.split(',').map(s => s.trim()).filter(Boolean)
  }

  try {
    const results = await publishStore.executeBatchPublish({
      targets: selectedTargets.value,
      concurrency: concurrency,
      action: form.action,
      filePath: form.filePath,
      images: imagesList,
      title: form.title,
      desc: form.desc,
      tags: form.tags,
      thumbnail: form.thumbnail,
      thumbnailLandscape: form.thumbnailLandscape,
      thumbnailPortrait: form.thumbnailPortrait,
      tid: form.tid,
      shortTitle: form.shortTitle,
      category: form.category,
      draft: form.draft,
      schedule: form.schedule,
      declaration: form.declaration,
      collection: form.collection,
      productLink: form.productLink,
      productTitle: form.productTitle,
      visibility: form.visibility,
      playlist: form.playlist,
      bgm: form.bgm,
      note: form.note,
      notef: '',
      headless: headless
    })

    const successCount = results.filter(r => r.success).length
    ElMessage.success(`🎉 矩阵发布批次执行完成！成功: ${successCount} / 总数: ${results.length}`)
  } catch (err: any) {
    ElMessage.error('矩阵批量发布异常: ' + (err.message || err))
  }
}

// 状态辅助函数
const getAccountExecStatus = (platform: string, account: string) => {
  return publishStore.batchAccountStates[`${platform}:${account}`] || 'pending'
}

const getAccountStateTagType = (platform: string, account: string) => {
  const state = publishStore.batchAccountStates[`${platform}:${account}`]
  if (state === 'success') return 'success'
  if (state === 'failed') return 'danger'
  if (state === 'running') return 'warning'
  return 'info'
}

const getAccountStateText = (platform: string, account: string) => {
  const state = publishStore.batchAccountStates[`${platform}:${account}`]
  if (state === 'success') return '已发布成功'
  if (state === 'failed') return '发布异常'
  if (state === 'running') return '调度发布中...'
  return '排队等待'
}

const getSuccessCount = () => {
  return Object.values(publishStore.batchAccountStates).filter(s => s === 'success').length
}

const getFailedCount = () => {
  return Object.values(publishStore.batchAccountStates).filter(s => s === 'failed').length
}

const getRunningCount = () => {
  return Object.values(publishStore.batchAccountStates).filter(s => s === 'running').length
}
</script>

<style scoped>
.publish-workspace {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 顶部步骤条 (Wizard Steps) */
.steps-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s ease;
}

.step-item.active {
  opacity: 1;
}

.step-item.done {
  opacity: 0.85;
}

.step-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-muted);
}

.step-item.active .step-num {
  background: var(--primary-gradient);
  color: #fff;
  border: none;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.4);
}

.step-item.done .step-num {
  background: var(--status-success);
  color: #fff;
  border: none;
}

.step-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.step-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.step-divider {
  width: 40px;
  height: 1px;
  background: var(--border-subtle);
}

/* 页面内容区 */
.step-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step-cards-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.full-card {
  margin-bottom: 0;
}

.card-header-flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.toggle-title {
  cursor: pointer;
}

.arrow-icon {
  font-size: 11px;
  color: var(--text-muted);
}

/* 媒体类型 */
.media-type-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.type-box {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.type-box:hover {
  border-color: var(--border-highlight);
}

.type-box.active {
  background: rgba(99, 102, 241, 0.12);
  border-color: var(--primary-color);
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.15);
}

.type-box-icon {
  font-size: 26px;
  color: var(--primary-color);
  display: flex;
}

.type-box-info .title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.type-box-info .desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 上传区 */
.upload-dropzone {
  border: 2px dashed var(--border-subtle);
  border-radius: 12px;
  padding: 36px 20px;
  text-align: center;
  cursor: pointer;
  background: var(--bg-detail);
  transition: all 0.2s ease;
}

.upload-dropzone:hover {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.drop-icon {
  font-size: 42px;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.drop-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.drop-tip {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.file-picked-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  padding: 14px 18px;
  border-radius: 12px;
}

.picked-icon {
  font-size: 28px;
  color: var(--primary-color);
}

.picked-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.picked-meta .file-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.picked-meta .file-path {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.picked-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 话题 */
.quick-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.quick-tags-label {
  font-size: 11px;
  color: var(--text-muted);
}

.clickable-tag {
  cursor: pointer;
  background: var(--bg-detail) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-secondary) !important;
  transition: all 0.2s ease;
}

.clickable-tag:hover {
  background: var(--primary-color) !important;
  color: #fff !important;
  border-color: var(--primary-color) !important;
}

/* 参数表格行 */
.params-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}

.param-label-box {
  display: flex;
  flex-direction: column;
}

.param-label-box .title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.param-label-box .sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.sub-group-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 8px;
}

/* 底部操作条 */
.bottom-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-radius: 12px;
}

.action-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.action-summary .highlight {
  color: var(--primary-color);
  font-size: 15px;
}

.action-summary .summary-title {
  font-weight: 700;
  color: var(--text-main);
}

.action-summary .summary-file {
  color: var(--text-muted);
  font-size: 11px;
}

.next-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px !important;
}

/* ========================================================================= */
/* STEP 2: 矩阵选择网格 */
/* ========================================================================= */
.matrix-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-detail);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 18px;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  min-width: 120px;
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.matrix-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.matrix-acc-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 12px;
  cursor: pointer;
  background: var(--bg-detail) !important;
  border: 1px solid var(--border-subtle) !important;
  transition: all 0.2s ease;
}

.matrix-acc-card:hover {
  border-color: var(--border-highlight) !important;
}

.matrix-acc-card.selected {
  background: rgba(99, 102, 241, 0.1) !important;
  border-color: var(--primary-color) !important;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15) !important;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plat-badge-lg {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.card-mid {
  flex: 1;
  margin-left: 10px;
  overflow: hidden;
}

.acc-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.acc-name-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grp-badge {
  font-size: 10px;
  height: 18px;
  line-height: 16px;
  padding: 0 4px;
}

.acc-sub-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.plat-tag-text {
  font-size: 11px;
  color: var(--text-muted);
}

.status-indicator-text {
  font-size: 10px;
}

.status-indicator-text.valid {
  color: var(--status-success);
}

.status-indicator-text.invalid {
  color: var(--status-danger);
}

.card-right-check {
  font-size: 20px;
  color: var(--primary-color);
}

.publish-btn-lg {
  padding: 10px 28px !important;
  font-size: 14px !important;
}

/* ========================================================================= */
/* STEP 3: 执行大盘 */
/* ========================================================================= */
.batch-summary-banner {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.banner-item {
  background: var(--bg-detail);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.banner-item .num {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-main);
}

.banner-item .label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.banner-item.success .num {
  color: var(--status-success);
}

.banner-item.fail .num {
  color: var(--status-danger);
}

.banner-item.running .num {
  color: var(--primary-color);
}

.execution-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.exec-acc-card {
  padding: 14px;
  border-radius: 10px;
}

.exec-acc-card.success {
  border-color: rgba(16, 185, 129, 0.4) !important;
}

.exec-acc-card.failed {
  border-color: rgba(239, 68, 68, 0.4) !important;
}

.exec-acc-card.running {
  border-color: rgba(99, 102, 241, 0.5) !important;
}

.exec-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plat-mini-badge {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 15px;
}

.exec-meta {
  flex: 1;
  overflow: hidden;
}

.exec-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exec-plat {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
