<template>
  <div class="task-center-workspace">
    <!-- 1. 进度总览 + 主控 -->
    <div class="task-stats-bar glass-card">
      <!-- 左：进度条 + 数字 -->
      <div class="progress-overview">
        <div class="progress-head">
          <span class="idx">1</span>
          <span class="section-name">发布控制台</span>
          <span class="progress-title">
            {{ taskStore.successTasksCount + taskStore.failedTasksCount }} / {{ taskStore.tasks.length }} 已完成
          </span>
          <span class="progress-sub" v-if="taskStore.isExecuting">
            预计还需 {{ estimatedMinutes }} 分钟 · {{ taskStore.lanes.length }} 个通道同时发布
          </span>
          <span class="progress-sub" v-else-if="taskStore.queuedTasksCount > 0">
            {{ taskStore.queuedTasksCount }} 个任务待发布，点「开始发布」即可执行
          </span>
          <span class="progress-sub" v-else>全部计划已完成</span>
        </div>

        <el-progress
          :percentage="overallPercent"
          :stroke-width="10"
          :show-text="false"
          :color="progressColor"
        />

        <div class="stat-chips">
          <span class="chip ok">✅ 成功 {{ taskStore.successTasksCount }}</span>
          <span class="chip running" v-if="taskStore.runningTasksCount > 0">🔄 发布中 {{ taskStore.runningTasksCount }}</span>
          <span class="chip fail" v-if="taskStore.failedTasksCount > 0">❌ 失败 {{ taskStore.failedTasksCount }}</span>
          <span class="chip queued" v-if="taskStore.queuedTasksCount > 0">⏸ 待发布 {{ taskStore.queuedTasksCount }}</span>
        </div>
      </div>

      <!-- 右：主控按钮 -->
      <div class="stats-actions">
        <el-button
          v-if="taskStore.isExecuting"
          type="danger"
          size="large"
          class="exec-btn"
          @click="taskStore.cancelWorkflow"
        >
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>停止发布</span>
        </el-button>

        <el-button
          v-else
          type="primary"
          size="large"
          class="exec-btn gradient-btn-matrix"
          :disabled="taskStore.queuedTasksCount === 0"
          @click="handleStartPublish"
        >
          <el-icon><Promotion /></el-icon>
          <span>开始发布 ({{ taskStore.queuedTasksCount }} 个待发)</span>
        </el-button>

        <!-- 次级设置：收纳成一条 -->
        <div class="stats-secondary">
          <el-dropdown trigger="click" @command="handleAutoDistribute">
            <el-button size="small" text class="ghost-btn">
              <el-icon><Setting /></el-icon>
              <span class="ghost-text">分配方式</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="anti-risk">🛡️ 按平台自动分配（同平台排队，不同平台同时）</el-dropdown-item>
                <el-dropdown-item divided command="1">1 个通道（全部依次发布）</el-dropdown-item>
                <el-dropdown-item command="2" v-if="taskStore.maxConcurrency >= 2">2 个通道（同时发布）</el-dropdown-item>
                <el-dropdown-item command="3" v-if="taskStore.maxConcurrency >= 3">3 个通道（推荐）</el-dropdown-item>
                <el-dropdown-item divided command="max">全部通道同时（按上限 {{ taskStore.maxConcurrency }} 个）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <span class="interval-box" title="同一通道内两个任务之间的等待秒数，间隔越大越不容易触发平台风控">
            <span class="interval-label">每条间隔</span>
            <el-input-number
              v-model="globalInterval"
              :min="0"
              :max="3600"
              :step="5"
              size="small"
              style="width: 76px"
              controls-position="right"
              @change="handleGlobalIntervalChange"
            />
            <span class="interval-unit">秒</span>
          </span>

          <el-button size="small" text class="ghost-btn" @click="openGlobalLogs">
            <el-icon><Monitor /></el-icon>
            <span class="ghost-text">日志</span>
            <span class="log-indicator-dot" v-if="taskStore.runningTasksCount > 0"></span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 2. 计划工作台：左计划列表 + 右发布明细 -->
    <div class="task-workspace" v-if="taskStore.tasks.length > 0">

      <!-- 左：计划列表 -->
      <div class="task-list-panel glass-card">
        <!-- 工具栏 -->
        <div class="list-toolbar">
          <div class="toolbar-left">
            <span class="idx">2</span>
            <span class="section-name">发布计划</span>
            <span class="list-count">{{ planGroups.length }} 个</span>
          </div>

          <div class="toolbar-right">
            <!-- 筛选：收成下拉，省横向空间 -->
            <el-select v-model="listFilter" size="small" class="filter-select">
              <el-option value="all" label="全部计划" />
              <el-option
                value="failed"
                :label="`只看失败 (${taskStore.failedTasksCount})`"
                :disabled="taskStore.failedTasksCount === 0"
              />
              <el-option value="running" label="进行中" />
            </el-select>

            <!-- 清理已完成：图标按钮 + tooltip -->
            <el-tooltip content="清理已完成的计划" placement="top">
              <el-button size="small" text class="icon-btn" @click="taskStore.clearFinishedTasks">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>

            <!-- 批次中心：历史批次归档与一键重发 -->
            <el-tooltip content="批次中心（历史批次与一键重发）" placement="top">
              <el-button size="small" text class="icon-btn" @click="showBatchDrawer = true">
                <el-icon><CollectionTag /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <!-- 计划列表（1 行 = 1 个计划 = 1 个 batchId） -->
        <div class="plan-list-wrap custom-scrollbar">
          <div
            v-for="p in planGroups"
            :key="p.key"
            class="plan-item"
            :class="[p.planStatus, { 'is-selected': selectedPlanId === p.key }]"
            @click="handleSelectPlan(p.key)"
          >
            <!-- 多选勾选框 -->
            <el-checkbox
              class="plan-check"
              :model-value="checkedPlanIds.includes(p.key)"
              @click.stop
              @change="(v: any) => {
                if (v) checkedPlanIds = Array.from(new Set([...checkedPlanIds, p.key]))
                else checkedPlanIds = checkedPlanIds.filter(id => id !== p.key)
              }"
            />

            <div class="plan-body">
              <div class="plan-title" :title="p.name">{{ p.name }}</div>
              <div class="plan-sub">
                <span class="plan-progress">{{ p.done }}/{{ p.total }}</span>
                <span class="p-chip ok"     v-if="p.success">✅ {{ p.success }}</span>
                <span class="p-chip run"    v-if="p.running">🔄 {{ p.running }}</span>
                <span class="p-chip bad"    v-if="p.failed">❌ {{ p.failed }}</span>
                <span
                  class="p-chip queued"
                  v-if="p.queued"
                  :title="`${p.queued} 条待发布`"
                >待发 {{ p.queued }}</span>
              </div>
            </div>

            <el-button
              v-if="p.running === 0"
              class="plan-del-btn"
              size="small"
              text
              @click.stop="handleRemovePlan(p)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <div v-if="planGroups.length === 0" class="list-empty">
            {{ listFilter === 'failed' ? '没有失败的计划 🎉' : '当前筛选条件下没有计划' }}
          </div>
        </div>
      </div>

      <!-- 右：发布明细表 -->
      <div class="plan-detail-panel glass-card">
        <div v-if="tabPlans.length > 0">
          <!-- ③ 区头 -->
          <div class="section-head">
            <span class="idx">3</span>
            <span class="section-name">发布明细</span>
          </div>

          <!-- 计划 Tab 栏 -->
          <el-tabs
            v-model="activePlanTab"
            class="plan-tabs"
            type="card"
            @tab-remove="closePlanTab"
            closable
          >
            <el-tab-pane
              v-for="p in tabPlans"
              :key="p.key"
              :name="p.key"
              :closable="tabPlans.length > 1"
            >
              <template #label>
                <span
                  class="tab-label"
                  :title="`${p.name} · ${planStatusText(p)} ${p.done}/${p.total}`"
                >
                  <span class="tab-dot" :class="p.planStatus"></span>
                  <span class="tab-name">{{ p.name }}</span>
                </span>
              </template>
            </el-tab-pane>
          </el-tabs>

          <!-- 状态条：计划名已在 Tab 上，此处不再重复（含查看视角，合并成一行） -->
          <div class="detail-bar" v-if="selectedPlan">
            <span
              v-if="currentPlanStatusText"
              class="detail-status"
              :class="selectedPlan.planStatus"
            >
              {{ currentPlanStatusText }}
            </span>
            <span class="detail-eta" v-if="selectedPlan.running > 0">
              预计还需 {{ estimatedMinutes }} 分钟
            </span>

            <div class="detail-bar-right" v-if="maxDetailDepth > 0">
              <span class="vlb-label">查看视角</span>
              <el-select v-model="detailViewLevel" size="small" class="view-select">
                <el-option :value="0" label="逐条明细" />
                <el-option
                  v-for="lv in maxDetailDepth"
                  :key="lv"
                  :value="lv"
                  :label="`按第 ${lv} 层目录${levelSampleName(lv) ? '（' + levelSampleName(lv) + '）' : ''}`"
                />
              </el-select>
            </div>
          </div>

          <!-- 逐条明细（视角 = 逐条） -->
          <div class="plan-detail-table custom-scrollbar" v-if="!detailGroups">
            <table>
              <thead>
                <tr>
                  <th style="width: 44px">#</th>
                  <th>内容</th>
                  <th style="width: 190px">发布账号</th>
                  <th style="width: 130px">状态</th>
                  <th style="width: 130px">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(t, idx) in (selectedPlan?.tasks || [])"
                  :key="t.id"
                  class="detail-row"
                  :class="[t.status, { 'is-selected': selectedTaskId === t.id }]"
                  @click="selectedTaskId = t.id"
                >
                  <td class="col-order">{{ idx + 1 }}</td>

                  <td class="col-content">
                    <div class="cell-main" :title="t.videoFileName || t.title">
                      {{ t.videoFileName || t.title || '—' }}
                    </div>
                    <div class="cell-sub" v-if="t.batchName">{{ t.batchName }}</div>
                  </td>

                  <td class="col-account">
                    <span class="plat-dot" :style="{ background: platformColor(t.platform) }" />
                    <span>{{ t.nickname || t.account }}</span>
                  </td>

                  <td class="col-status">
                    <span class="status-pill" :class="t.status">
                      <el-icon v-if="t.status === 'running'" class="is-loading"><Loading /></el-icon>
                      <el-icon v-else-if="t.status === 'success'"><CircleCheck /></el-icon>
                      <el-icon v-else-if="t.status === 'failed'"><CircleClose /></el-icon>
                      <el-icon v-else><Clock /></el-icon>
                      <span>{{ statusText(t) }}</span>
                    </span>
                    <div class="fail-line" v-if="t.status === 'failed' && failureReason(t)" :title="failureReason(t)">
                      {{ failureReason(t) }}
                    </div>
                  </td>

                  <td class="col-actions">
                    <template v-if="t.status === 'failed' || t.status === 'cancelled'">
                      <el-button size="small" type="primary" link @click.stop="taskStore.retryTask(t.id)">重试</el-button>
                    </template>
                    <template v-else-if="t.status === 'running'">
                      <el-button size="small" type="danger" link @click.stop="taskStore.cancelTask(t.id)">中止</el-button>
                    </template>
                    <el-button size="small" link @click.stop="openTaskLogs(t)">日志</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 分组明细（视角 = 按第 N 层） -->
          <div class="plan-detail-table custom-scrollbar" v-else>
            <div v-for="g in detailGroups" :key="g.key" class="detail-group">
              <!-- 分组头 -->
              <div class="detail-group-head" @click="toggleDetailGroup(g.key)">
                <el-icon class="dg-arrow" :class="{ open: expandedDetailGroups.includes(g.key) }">
                  <ArrowRight />
                </el-icon>
                <span class="dg-label">{{ g.label }}</span>
                <span class="dg-progress">{{ g.done }}/{{ g.total }}</span>
                <span class="dg-chip ok"     v-if="g.success">✅ {{ g.success }}</span>
                <span class="dg-chip run"    v-if="g.running">🔄 {{ g.running }}</span>
                <span class="dg-chip bad"    v-if="g.failed">❌ {{ g.failed }}</span>
                <span class="dg-chip queued" v-if="g.queued">⏸ {{ g.queued }}</span>
              </div>

              <!-- 分组内明细（复用同一套行模板） -->
              <table v-if="expandedDetailGroups.includes(g.key)">
                <thead>
                  <tr>
                    <th style="width: 40px">#</th>
                    <th>内容</th>
                    <th style="width: 170px">发布账号</th>
                    <th style="width: 130px">状态</th>
                    <th style="width: 140px">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(t, idx) in g.tasks"
                    :key="t.id"
                    class="detail-row"
                    :class="[t.status, { 'is-selected': selectedTaskId === t.id }]"
                    @click="selectedTaskId = t.id"
                  >
                    <td class="col-order">{{ idx + 1 }}</td>

                    <td class="col-content">
                      <div class="cell-main" :title="t.videoFileName || t.title">
                        {{ t.videoFileName || t.title || '—' }}
                      </div>
                      <div class="cell-sub" v-if="t.batchName">{{ t.batchName }}</div>
                    </td>

                    <td class="col-account">
                      <span class="plat-dot" :style="{ background: platformColor(t.platform) }" />
                      <span>{{ t.nickname || t.account }}</span>
                    </td>

                    <td class="col-status">
                      <span class="status-pill" :class="t.status">
                        <el-icon v-if="t.status === 'running'" class="is-loading"><Loading /></el-icon>
                        <el-icon v-else-if="t.status === 'success'"><CircleCheck /></el-icon>
                        <el-icon v-else-if="t.status === 'failed'"><CircleClose /></el-icon>
                        <el-icon v-else><Clock /></el-icon>
                        <span>{{ statusText(t) }}</span>
                      </span>
                      <div class="fail-line" v-if="t.status === 'failed' && failureReason(t)" :title="failureReason(t)">
                        {{ failureReason(t) }}
                      </div>
                    </td>

                    <td class="col-actions">
                      <template v-if="t.status === 'failed' || t.status === 'cancelled'">
                        <el-button size="small" type="primary" link @click.stop="taskStore.retryTask(t.id)">重试</el-button>
                      </template>
                      <template v-else-if="t.status === 'running'">
                        <el-button size="small" type="danger" link @click.stop="taskStore.cancelTask(t.id)">中止</el-button>
                      </template>
                      <el-button size="small" link @click.stop="openTaskLogs(t)">日志</el-button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 选中某条时的日志 -->
          <div class="detail-logs" v-if="selectedTask">
            <div class="logs-title">
              执行日志 · {{ selectedTask.nickname || selectedTask.account }}
            </div>
            <div class="logs-list custom-scrollbar">
              <div v-for="(l, i) in (selectedTask.logs || []).slice(-30)" :key="i" class="log-line" :class="l.type">
                <span class="log-time">{{ l.time || '' }}</span>
                <span class="log-text">{{ l.message }}</span>
              </div>
              <div v-if="!selectedTask.logs || selectedTask.logs.length === 0" class="logs-empty">暂无日志</div>
            </div>
          </div>
        </div>

        <div v-else class="detail-empty">
          <el-icon :size="26"><Document /></el-icon>
          <span>点击左侧计划查看发布明细</span>
        </div>
      </div>
    </div>

    <!-- 3. 防风控冲突提示栏（仅在有冲突时显示） -->
    <div class="risk-bar glass-card" v-if="taskStore.platformConflicts.length > 0">
      <div class="risk-alert-box">
        <el-icon class="risk-icon"><WarningFilled /></el-icon>
        <span class="risk-text">
          检测到 <strong>{{ taskStore.platformConflicts.map(p => getPlatformStyle(p).name).join('、') }}</strong> 的任务分散在多个通道里同时发布，可能触发平台频次风控
        </span>
        <el-button size="small" type="warning" plain @click="taskStore.autoDistributeTasksToLanes()">
          一键优化防风控
        </el-button>
      </div>
    </div>

    <!-- 5. 抽屉式任务详情与实时终端日志控制台 -->
    <TaskLogDrawer
      v-model="showLogDrawer"
      :task="selectedTaskForDrawer"
      :initialTab="drawerInitialTab"
    />

    <!-- 批次中心：历史批次归档与一键重发 -->
    <BatchManagerDrawer
      v-model="showBatchDrawer"
      @republished="handleBatchRepublished"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onErrorCaptured } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, ArrowDown, CircleCheck, CircleClose, Clock, CollectionTag, Delete, Document, Loading, Monitor, Promotion, Remove, Setting, WarningFilled } from '@element-plus/icons-vue'
import { getPlatformConfig } from '../config/platforms'
import { useTaskStore } from '../stores/taskStore'
import TaskLogDrawer from '../components/matrix/TaskLogDrawer.vue'
import BatchManagerDrawer from '../components/matrix/BatchManagerDrawer.vue'
import type { PublishTask, TaskStatus } from '../types/task'

/** 渲染错误边界：捕获组件内所有未处理异常，显示到界面上 */
onErrorCaptured((err) => {
  console.error('[TaskCenter 渲染错误]', err)
  ElMessage.error('页面渲染异常：' + ((err as any)?.message || err?.message || String(err)))
  return false
})

const taskStore = useTaskStore()

/** 全局间隔（读写所有通道的 delayBetweenTasks；未设置时默认 15 秒） */
const globalInterval = ref<number>(15)

/** 初始化：取首个通道的间隔作为显示值 */
onMounted(() => {
  const first = taskStore.lanes[0]
  if (first) globalInterval.value = first.delayBetweenTasks ?? 15
})

/** 改间隔 → 同步到所有通道（并提示） */
const handleGlobalIntervalChange = (val: number | undefined) => {
  const v = Number(val) || 0
  taskStore.lanes.forEach((lane: any) => {
    lane.delayBetweenTasks = v
  })
  ElMessage.success(`每条间隔已设为 ${v} 秒，将在该通道内的任务之间生效`)
}

// 进度总览计算属性
/** 完成率（成功 + 失败 视为已结束） */
const overallPercent = computed(() => {
  const total = taskStore.tasks.length
  if (total === 0) return 0
  return Math.round(((taskStore.successTasksCount + taskStore.failedTasksCount) / total) * 100)
})

/** 进度条颜色：有失败偏黄，否则主色渐变 */
const progressColor = computed(() =>
  taskStore.failedTasksCount > 0 ? 'var(--status-warning)' : 'var(--primary-color)'
)

/** 粗略预计剩余分钟（按已用时间与完成比例外推） */
const estimatedMinutes = computed(() => {
  const done = taskStore.successTasksCount + taskStore.failedTasksCount
  if (done === 0 || !taskStore.isExecuting) return 0
  const remain = taskStore.tasks.length - done
  if (remain <= 0) return 0
  const avgSecPerTask = 90
  return Math.max(1, Math.ceil((remain * avgSecPerTask) / 60 / Math.max(1, taskStore.lanes.length)))
})

// ---- 左侧计划列表 ----
type ListFilter = 'all' | 'failed' | 'running'
const listFilter = ref<ListFilter>('all')

/** 按筛选条件过滤后的任务 */
const filteredTasks = computed(() => {
  let list = taskStore.tasks

  if (listFilter.value === 'failed') {
    list = list.filter((t) => t.status === 'failed')
  } else if (listFilter.value === 'running') {
    list = list.filter((t) => t.status === 'running' || t.status === 'queued')
  }

  return list
})

// ---- 计划列表（1 行 = 1 个计划 = 1 个 batchId）----

/** 计划列表：按 batchId 聚合，附战果统计 */
const planGroups = computed(() => {
  const map = new Map<string, {
    key: string
    name: string
    createdAt: string
    tasks: any[]
  }>()

  filteredTasks.value.forEach((t) => {
    const key = t.batchId || 'unknown'
    if (!map.has(key)) {
      map.set(key, {
        key,
        name: t.batchName || '未命名计划',
        createdAt: t.createdAt || '',
        tasks: []
      })
    }
    map.get(key)!.tasks.push(t)
  })

  return Array.from(map.values()).map((g) => {
    const success = g.tasks.filter((t) => t.status === 'success').length
    const failed  = g.tasks.filter((t) => t.status === 'failed').length
    const running = g.tasks.filter((t) => t.status === 'running').length
    const queued  = g.tasks.filter((t) => t.status === 'queued').length
    return {
      ...g,
      total: g.tasks.length,
      success, failed, running, queued,
      done: success + failed,
      /** 计划整体状态：有执行中→蓝；有失败→红；全成功→绿；否则灰 */
      planStatus: running > 0 ? 'running'
                : failed > 0  ? 'failed'
                : success === g.tasks.length ? 'success'
                : 'queued'
    }
  })
})

/** 当前选中的计划 */
const selectedPlanId = ref<string>('')
const selectedPlan = computed(() =>
  planGroups.value.find((g) => g.key === selectedPlanId.value) || null
)

// ---- 右侧发布明细：查看视角 ----
/** 0 = 逐条明细（不分组）；N = 按第 N 层目录分组 */
const detailViewLevel = ref<number>(0)
/** 展开的分组 */
const expandedDetailGroups = ref<string[]>([])

/** 当前计划里素材的最大目录深度（用于动态生成选项） */
const maxDetailDepth = computed(() => {
  let max = 0
  selectedPlan.value?.tasks.forEach((t: any) => {
    const n = (t.folderCrumbs || []).length
    if (n > max) max = n
  })
  return max
})

/** 第 N 层目录的示例名（给下拉选项做提示，如「帐号1」） */
function levelSampleName(level: number): string {
  const t = selectedPlan.value?.tasks.find((x: any) => (x.folderCrumbs || []).length >= level)
  return t?.folderCrumbs?.[level - 1] || ''
}

/** 分组结果（detailViewLevel === 0 时为 null，表示逐条展示） */
const detailGroups = computed(() => {
  const plan = selectedPlan.value
  if (!plan || detailViewLevel.value === 0) return null

  const lv = detailViewLevel.value
  const map = new Map<string, { key: string; label: string; tasks: any[] }>()

  plan.tasks.forEach((t: any) => {
    const crumbs: string[] = t.folderCrumbs || []
    const parts = crumbs.slice(0, lv)
    const label = parts.length > 0 ? parts.join(' / ') : '未分组'
    if (!map.has(label)) map.set(label, { key: label, label, tasks: [] })
    map.get(label)!.tasks.push(t)
  })

  return Array.from(map.values()).map((g) => {
    const success = g.tasks.filter((t) => t.status === 'success').length
    const failed  = g.tasks.filter((t) => t.status === 'failed').length
    const running = g.tasks.filter((t) => t.status === 'running').length
    const queued  = g.tasks.filter((t) => t.status === 'queued').length
    return {
      ...g,
      total: g.tasks.length,
      success, failed, running, queued,
      done: success + failed,
      groupStatus: running > 0 ? 'running'
                 : failed > 0  ? 'failed'
                 : success === g.tasks.length ? 'success'
                 : 'queued'
    }
  })
})

/** 切换视角时默认展开所有分组 */
watch(detailViewLevel, () => {
  expandedDetailGroups.value = detailGroups.value?.map((g) => g.key) || []
})

/** 展开/折叠某个分组 */
const toggleDetailGroup = (key: string) => {
  const i = expandedDetailGroups.value.indexOf(key)
  if (i >= 0) expandedDetailGroups.value.splice(i, 1)
  else expandedDetailGroups.value.push(key)
}

/** 切换计划时重置视角 */
watch(selectedPlanId, () => {
  detailViewLevel.value = 0
  expandedDetailGroups.value = []
  selectedTaskId.value = ''
})

// ---- 右侧发布明细 ----
/** 当前选中的任务 ID（点击明细某行时更新） */
const selectedTaskId = ref<string>('')

/** 日志区 DOM ref（用于自动滚动到底） */
const logScrollEl = ref<HTMLElement | null>(null)

/** 当前选中的任务对象（找不到时为空） */
const selectedTask = computed(() =>
  taskStore.tasks.find((t) => t.id === selectedTaskId.value) || null
)

/** 选中计划 key 变化时自动选中该计划的第一条 */
watch(
  () => selectedPlanId.value,
  () => {
    if (!selectedPlan.value) return
    // 保持 selectedTaskId 不变（用户可能在看某条日志）
    // 如果当前选中任务不在新计划内，则切到第一条
    const stillInPlan = selectedPlan.value.tasks.some((t: any) => t.id === selectedTaskId.value)
    if (!stillInPlan && selectedPlan.value.tasks.length > 0) {
      selectedTaskId.value = selectedPlan.value.tasks[0].id
    }
    // 切计划时重置视角
    detailViewLevel.value = 0
    expandedDetailGroups.value = []
  }
)

/** 选中任务时或日志更新时自动滚动到底 */
watch(
  [selectedTaskId, () => selectedTask.value?.logs?.length],
  async () => {
    await nextTick()
    const el = document.querySelector('.logs-list') as HTMLElement | null
    if (el) el.scrollTop = el.scrollHeight
  }
)

/** 计划状态文案（待发布返回空字符串，由右侧徽章的 v-if 隐藏） */
function planStatusText(p: any): string {
  if (p.running > 0) return '发布中'
  if (p.failed > 0)  return `${p.failed} 条失败`
  if (p.total > 0 && p.success === p.total) return '已完成'
  // 待发布：不显示徽章（Tab 的空心环已表达，顶部控制台也有行动指引）
  return ''
}

/** computed 版，避免模板中重复调用两次 */
const currentPlanStatusText = computed(() =>
  selectedPlan.value ? planStatusText(selectedPlan.value) : ''
)

/** 状态文案 */
function statusText(t: any): string {
  switch (t.status) {
    case 'running': return `发布中${t.progress ? ' ' + t.progress + '%' : ''}`
    case 'success': return '已发布'
    case 'failed':  return '失败'
    case 'cancelled': return '已中止'
    case 'queued':  return '待发布'
    default:        return t.status
  }
}

/** 失败原因：优先取最后一条 error 级日志 */
function failureReason(t: any): string {
  const logs = t.logs || []
  for (let i = logs.length - 1; i >= 0; i--) {
    if (logs[i].type === 'error') return logs[i].message
  }
  return ''
}

/** 删除整个计划（二次确认） */
const handleRemovePlan = async (p: any) => {
  try {
    await ElMessageBox.confirm(
      `将删除计划「${p.name}」及其 ${p.total} 条发布，删除后不可恢复。`,
      '确认删除计划？',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  taskStore.removeTasks(p.tasks.map((t: any) => t.id))
  checkedTaskIds.value = []
  if (selectedPlanId.value === p.key) selectedPlanId.value = ''
  if (p.tasks.some((t: any) => t.id === selectedTaskId.value)) selectedTaskId.value = ''
}

// 抽屉状态
const showLogDrawer = ref(false)
const selectedTaskForDrawer = ref<PublishTask | null>(null)
/** 批次中心抽屉（历史批次与一键重发） */
const showBatchDrawer = ref(false)
/** 日志抽屉默认定位的标签页 */
const drawerInitialTab = ref<'terminal' | 'live'>('terminal')

/** 平台色 */
function platformColor(platform: string): string {
  return getPlatformStyle(platform).brandColor || 'var(--text-muted)'
}

const getPlatformStyle = (platformId: string) => {
  return getPlatformConfig(platformId)
}

const getStatusText = (status: TaskStatus) => {
  switch (status) {
    case 'running': return '执行中'
    case 'queued': return '排队中'
    case 'success': return '发布成功'
    case 'failed': return '发布失败'
    case 'cancelled': return '已取消'
    default: return '待调度'
  }
}

const openGlobalLogs = () => {
  selectedTaskForDrawer.value = null
  drawerInitialTab.value = 'terminal'
  showLogDrawer.value = true
}

const openTaskLogs = (task: PublishTask, tab: 'terminal' | 'live' = 'terminal') => {
  selectedTaskForDrawer.value = task
  drawerInitialTab.value = tab
  showLogDrawer.value = true
}

/** 批次中心一键重发后：把新生成的批次作为当前计划打开 */
const handleBatchRepublished = (newBatchId: string) => {
  openPlanTabs.value = [newBatchId]
  activePlanTab.value = newBatchId
  selectedPlanId.value = newBatchId
  taskStore.setPlanQueue([newBatchId])
}

const handleAutoDistribute = (cmd: string) => {
  if (cmd === 'anti-risk') {
    taskStore.autoDistributeTasksToLanes()
    ElMessage.success('已按平台分配：同平台排队，不同平台同时发布')
  } else if (cmd === 'max') {
    taskStore.autoDistributeTasksToLanes(undefined, taskStore.maxConcurrency)
    ElMessage.success(`已按通道上限（${taskStore.maxConcurrency} 个）平均分配`)
  } else {
    const num = parseInt(cmd, 10)
    if (!isNaN(num)) {
      taskStore.autoDistributeTasksToLanes(undefined, num)
      ElMessage.success(`已平均分配到 ${num} 个通道`)
    }
  }
}

// ---- 多选 ----
const checkedTaskIds = ref<string[]>([])

/** 切换单个任务勾选状态 */
const toggleTaskCheck = (taskId: string, checked: boolean) => {
  if (checked) {
    checkedTaskIds.value = Array.from(new Set([...checkedTaskIds.value, taskId]))
  } else {
    checkedTaskIds.value = checkedTaskIds.value.filter((id) => id !== taskId)
  }
}

// ---- 计划 Tab（多计划逐个串行执行）----
/** 已打开的计划 Tab（batchId 列表，顺序 = 执行顺序） */
const openPlanTabs = ref<string[]>([])
/** 当前激活的 Tab */
const activePlanTab = ref<string>('')

/** Tab 对应的计划对象 */
const tabPlans = computed(() =>
  openPlanTabs.value
    .map((id) => planGroups.value.find((p) => p.key === id))
    .filter(Boolean) as any[]
)

/** 打开一个计划 Tab（已存在则只激活） */
function openPlanTab(batchId: string) {
  if (!openPlanTabs.value.includes(batchId)) openPlanTabs.value.push(batchId)
  activePlanTab.value = batchId
  selectedPlanId.value = batchId
  taskStore.setPlanQueue(openPlanTabs.value)
}

/** 关闭一个计划 Tab（从队列移除） */
function closePlanTab(batchId: string) {
  const i = openPlanTabs.value.indexOf(batchId)
  if (i < 0) return
  openPlanTabs.value.splice(i, 1)
  taskStore.removeFromPlanQueue(batchId)

  if (activePlanTab.value === batchId) {
    const next = openPlanTabs.value[Math.max(0, i - 1)]
    activePlanTab.value = next || ''
    selectedPlanId.value = next || ''
  }
}

/** 默认选中第一个计划（自动打开 Tab） */
watch(
  () => planGroups.value.length,
  () => {
    if (!selectedPlanId.value && planGroups.value.length > 0) {
      const first = planGroups.value[0]
      selectedPlanId.value = first.key
      openPlanTab(first.key)
    }
  },
  { immediate: true }
)

/** 切换 Tab（只切视图，不动执行） */
watch(activePlanTab, (id) => {
  if (id && openPlanTabs.value.includes(id)) selectedPlanId.value = id
})

/** 勾选的计划（多选） */
const checkedPlanIds = ref<string[]>([])

watch(checkedPlanIds, (ids) => {
  if (ids.length > 0) {
    openPlanTabs.value = [...ids]
    if (!ids.includes(activePlanTab.value)) activePlanTab.value = ids[0]
    taskStore.setPlanQueue(ids)
  }
})

/**
 * 左侧点击计划：
 * · 没有任何勾选 → 打开单个 Tab（替换全部）
 * · 有勾选 → 只切换激活的 Tab（多选模式由勾选驱动）
 */
function handleSelectPlan(batchId: string) {
  // 多选模式下：只切激活 Tab，绝不重建列表
  if (checkedPlanIds.value.length > 0) {
    if (openPlanTabs.value.includes(batchId) && activePlanTab.value !== batchId) {
      activePlanTab.value = batchId
    }
    return
  }

  // 已经是当前唯一 Tab → 直接返回（避免无意义的数组重建）
  if (openPlanTabs.value.length === 1 && openPlanTabs.value[0] === batchId) {
    if (selectedPlanId.value !== batchId) selectedPlanId.value = batchId
    return
  }

  openPlanTabs.value = [batchId]
  activePlanTab.value = batchId
  selectedPlanId.value = batchId
  taskStore.setPlanQueue([batchId])
}

/** 执行时自动切到正在执行的计划 Tab */
watch(
  () => taskStore.activePlanId,
  (id) => {
    if (id && openPlanTabs.value.includes(id)) {
      activePlanTab.value = id
      selectedPlanId.value = id
    }
  }
)

/** 计划列表变化时，清理已消失的 Tab */
watch(
  () => planGroups.value.map((p) => p.key).join(','),
  () => {
    const alive = new Set(planGroups.value.map((p) => p.key))
    openPlanTabs.value = openPlanTabs.value.filter((id) => alive.has(id))
    if (!openPlanTabs.value.includes(activePlanTab.value)) {
      activePlanTab.value = openPlanTabs.value[0] || ''
      selectedPlanId.value = activePlanTab.value
    }
  }
)

/** 开始发布：有队列走队列，无队列走老行为 */
function handleStartPublish() {
  if (openPlanTabs.value.length > 0) {
    taskStore.setPlanQueue(openPlanTabs.value)
    taskStore.startPlanQueue()
  } else {
    taskStore.triggerMultiLaneExecution()
  }
}
</script>

<style scoped>
/* ===== 整体布局 ===== */
.task-center-workspace {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 88px);
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

/* ===== 顶部总览 ===== */
.task-stats-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 18px;
  border-radius: 12px;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  backdrop-filter: blur(16px);
}

.progress-overview { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.progress-head { display: flex; align-items: center; gap: 8px; }

/* 区块编号：方形小标（与「发布工作台」保持同一形态） */
.idx {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-color);
  background: rgba(79, 70, 229, 0.10);
  border: 1px solid rgba(79, 70, 229, 0.28);
  flex-shrink: 0;
}

.section-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

/* ③ 区头 */
.section-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.progress-title { font-size: 15px; font-weight: 700; color: var(--text-main); margin-left: 4px; }
.progress-sub { font-size: 12px; color: var(--text-muted); }

.stat-chips { display: flex; gap: 16px; font-size: 12px; }
.chip { display: inline-flex; align-items: center; gap: 4px; }
.chip.ok      { color: var(--status-success); }
.chip.fail    { color: var(--status-danger); }
.chip.running { color: var(--primary-color); }
.chip.queued  { color: var(--text-muted); }

/* ===== 主控按钮区 ===== */
.stats-actions { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.stats-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-left: 14px;
  border-left: 1px solid var(--border-subtle);
}

.exec-btn { min-width: 140px; font-weight: 600; }
.gradient-btn-matrix {
  background: linear-gradient(135deg, var(--primary-color), #6366f1);
  border: none;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
}

.ghost-btn { color: var(--text-muted); font-size: 12.5px; }
.ghost-btn:hover { color: var(--primary-color); background: rgba(79, 70, 229, 0.08); }
.ghost-text { margin: 0 2px; }

.log-indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--status-success);
  margin-left: 4px;
  display: inline-block;
  animation: pulse-dot 1.4s ease-in-out infinite;
}
@keyframes pulse-dot { 0%,100% { opacity: 1 } 50% { opacity: .35 } }

/* ===== 间隔设置 ===== */
.interval-box { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-muted); }
.interval-label { white-space: nowrap; }
.interval-unit { white-space: nowrap; }

/* ===== 防风控冲突提示栏 ===== */
.risk-bar { display: flex; align-items: center; justify-content: center; padding: 8px 16px; flex-shrink: 0; }
.risk-alert-box {
  display: flex; align-items: center; gap: 8px;
  padding: 3px 10px; border-radius: 6px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  font-size: 11px; color: var(--status-warning); white-space: nowrap;
}
.risk-icon { font-size: 13px; color: var(--status-warning); }

/* ===== 左侧计划列表 ===== */
.task-list-panel {
  flex: 0 0 360px;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0;
  overflow: hidden;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.toolbar-left { display: flex; align-items: center; gap: 7px; min-width: 0; }
.toolbar-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.filter-select { width: 118px; }
.filter-select :deep(.el-select__wrapper) { font-size: 12.5px; }

.icon-btn { color: var(--text-muted); padding: 4px 6px; }
.icon-btn:hover { color: var(--status-danger); background: rgba(239, 68, 68, 0.08); }

.list-count { font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.section-name { font-size: 14px; font-weight: 700; color: var(--text-main); white-space: nowrap; }

.plan-list-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 6px;
}

.plan-check { flex-shrink: 0; margin-right: 2px; }

.plan-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 10px 11px;
  margin-bottom: 2px;
  border-radius: 9px;
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: background-color .14s, border-color .14s;
}
.plan-item:hover { background: var(--bg-input); }
.plan-item.is-selected {
  background: rgba(79, 70, 229, 0.10);
  border-left-color: var(--primary-color);
}
.plan-item.running { border-left-color: var(--primary-color); }
.plan-item.failed  { border-left-color: var(--status-danger); }

.plan-body { flex: 1; min-width: 0; }
.plan-title {
  font-size: 13px; font-weight: 650; color: var(--text-main);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.35;
}
.plan-sub { display: flex; align-items: center; gap: 8px; margin-top: 5px; font-size: 11.5px; }
.plan-progress { color: var(--text-muted); font-weight: 600; font-variant-numeric: tabular-nums; }
.p-chip.ok     { color: var(--status-success); }
.p-chip.bad    { color: var(--status-danger); }
.p-chip.run    { color: var(--primary-color); }
.p-chip.queued { color: var(--text-muted); }

.plan-del-btn { flex-shrink: 0; opacity: 0; transition: opacity .15s; color: var(--status-danger); padding: 2px 4px; }
.plan-item:hover .plan-del-btn { opacity: 1; }
.plan-item.is-selected .plan-del-btn { opacity: .55; }

/* ===== 右侧发布明细 ===== */
.plan-detail-panel {
  flex: 1; min-width: 0; min-height: 0;
  display: flex; flex-direction: column;
  padding: 14px 16px; overflow: hidden;
}

/* Tab 条 */
.plan-tabs { flex-shrink: 0; width: 100%; min-width: 0; }
.plan-tabs :deep(.el-tabs__header) { margin-bottom: 8px; }
.plan-tabs :deep(.el-tabs__item) { font-size: 12.5px; height: 32px; line-height: 32px; padding: 0 11px; }
.plan-tabs :deep(.el-tabs__item.is-active) { font-weight: 600; }
.plan-tabs :deep(.el-tabs__content) { display: none; }

.tab-label { display: inline-flex; align-items: center; gap: 6px; }
.tab-name { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 状态圆点（与列表、明细的状态色统一） */
.tab-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tab-dot.success { background: var(--status-success); }
.tab-dot.failed  { background: var(--status-danger); }
.tab-dot.running {
  background: var(--primary-color);
  animation: pulse-dot 1.4s ease-in-out infinite;
}
/* 待发布：空心圆环（实心灰点太弱，会被误认为"没状态"） */
.tab-dot.queued {
  background: transparent;
  border: 2px solid var(--text-muted);
  opacity: .7;
  box-sizing: border-box;
}



/* 明细状态条（合并：状态徽章 + 查看视角，同一行） */
.detail-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.detail-bar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 7px;
}
.view-select { width: 190px; }
.vlb-label { font-size: 12px; color: var(--text-muted); white-space: nowrap; }

/* 状态徽章（detail-bar 内使用） */
.detail-status {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 18px;
}
.detail-status.queued  { color: var(--text-muted);     background: var(--bg-input); }
.detail-status.running { color: var(--primary-color);  background: rgba(79, 70, 229, 0.10); }
.detail-status.success { color: var(--status-success); background: rgba(16, 185, 129, 0.10); }
.detail-status.failed  { color: var(--status-danger);  background: rgba(239, 68, 68, 0.10); }

.detail-eta { font-size: 12px; color: var(--text-muted); }

/* 明细表 */
.plan-detail-table {
  flex: 1;
  min-height: 120px;
  overflow-y: auto;
  margin-top: 10px;
}
.plan-detail-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.plan-detail-table th {
  position: sticky;
  top: 0;
  background: var(--bg-detail);
  padding: 9px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
  z-index: 2;
  color: var(--text-main);
}
.detail-row td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}
.detail-row { cursor: pointer; }
.detail-row:hover td { background: rgba(99, 102, 241, 0.06); }
.detail-row.is-selected td { background: rgba(99, 102, 241, 0.09); }

/* 单元格文字（与对应表一致：主文字 12px，次要 11px） */
.col-order { text-align: center; color: var(--text-muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.cell-main { font-size: 12px; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-sub  { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.status-pill { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; }
.status-pill.success { color: var(--status-success); }
.status-pill.failed  { color: var(--status-danger); }
.status-pill.running { color: var(--primary-color); }
.status-pill.queued,
.status-pill.cancelled { color: var(--text-muted); }

.fail-line {
  margin-top: 3px; font-size: 11px; color: var(--status-danger);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px;
}

/* 日志区 */
.detail-logs {
  flex: 0 0 auto;
  max-height: 30%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px; margin-top: 8px;
}
.logs-title { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
.logs-list {
  flex: 1; min-height: 60px; overflow-y: auto;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11.5px; line-height: 1.6;
}
.log-line { display: flex; gap: 8px; padding: 2px 0; color: var(--text-main); }
.log-line.error { color: var(--status-danger); }
.log-line.warn { color: var(--status-warning); }
.log-time { color: var(--text-muted); flex-shrink: 0; }
.logs-empty { color: var(--text-muted); font-size: 12px; padding: 10px 0; }

/* ===== 空状态 ===== */
.list-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px; padding: 40px 16px;
  color: var(--text-muted); font-size: 12.5px;
}
.detail-empty {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; color: var(--text-muted); font-size: 13px;
}
.detail-empty .el-icon { color: var(--text-muted); opacity: .5; }



.detail-group { border-bottom: 1px solid var(--border-subtle); }
.detail-group:last-child { border-bottom: none; }
.detail-group-head {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 6px; cursor: pointer; border-radius: 6px;
}
.detail-group-head:hover { background: var(--bg-input); }
.dg-arrow { font-size: 11px; color: var(--text-muted); transition: transform .18s; }
.dg-arrow.open { transform: rotate(90deg); }
.dg-label { font-size: 12.5px; font-weight: 600; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.dg-progress { font-size: 11.5px; color: var(--text-muted); font-weight: 600; flex-shrink: 0; }
.dg-chip { font-size: 11.5px; flex-shrink: 0; }
.dg-chip.ok     { color: var(--status-success); }
.dg-chip.bad    { color: var(--status-danger); }
.dg-chip.run    { color: var(--primary-color); }
.dg-chip.queued { color: var(--text-muted); }

/* ===== 工作台布局 ===== */
.task-workspace {
  flex: 1; min-height: 0;
  display: flex; gap: 12px; align-items: stretch;
  overflow: hidden;
}

/* ===== 滚动条细化 ===== */
.custom-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, .35);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, .55); }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }

/* ===== 硬编码色清除 ===== */
.running-card .stat-num { color: var(--primary-color); }
.queued-card  .stat-num { color: var(--text-muted); }
.success-card .stat-num { color: var(--status-success); }
.failed-card  .stat-num { color: var(--status-danger); }

/* stat-card base */
.stat-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 5px 12px; border-radius: 8px;
  background: var(--bg-detail); border: 1px solid var(--border-subtle); min-width: 64px;
}
.stat-num { font-size: 16px; font-weight: 700; color: var(--text-main); line-height: 1.2; }
.stat-label { font-size: 10px; color: var(--text-secondary); margin-top: 1px; }

/* 窄屏堆叠 */
@media (max-width: 1100px) {
  .task-workspace { flex-direction: column; }
  .task-list-panel { flex: 0 0 auto; max-width: 100%; max-height: 40vh; }
}
</style>
