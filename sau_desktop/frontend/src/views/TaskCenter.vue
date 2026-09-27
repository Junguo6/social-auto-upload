<template>
  <div class="task-center-workspace">
    <!-- 1. 进度总览 + 主控 -->
    <div class="task-stats-bar glass-card">
      <!-- 左：进度条 + 数字 -->
      <div class="progress-overview">
        <!-- 行 1：编号 + 标题 + 正在执行的计划 + 队列位置 -->
        <div class="progress-head">
          <span class="idx">1</span>
          <span class="section-name">发布控制台</span>

          <span class="head-plan" v-if="activePlanName">
            正在执行：<b>{{ activePlanName }}</b>
            <span class="queue-pos" v-if="planQueueTotal > 1">
              （第 {{ planQueueIndex }}/{{ planQueueTotal }} 个）
            </span>
          </span>
        </div>

        <!-- 空态①：还没有任何计划 → 引导去创建 -->
        <div class="console-empty-hint" v-if="!hasPlans">
          <el-icon class="hint-ic"><InfoFilled /></el-icon>
          <span>
            还没有发布计划
            <span class="hint-sub">去「发布工作台」配置好内容与账号后，点「创建发布计划」</span>
          </span>
          <el-button size="small" type="primary" plain class="hint-btn" @click="goPublishCenter">
            去创建发布计划
          </el-button>
        </div>

        <!-- 空态②：有计划但未勾选 → 引导勾选 -->
        <div class="console-empty-hint" v-else-if="!hasSelection">
          <el-icon class="hint-ic"><InfoFilled /></el-icon>
          <span>
            请在下方「<b>发布计划</b>」中勾选要执行发布的计划
            <span class="hint-sub">（可多选，勾选后点「开始发布」）</span>
          </span>
        </div>

        <!-- 行 2：完成进度 + 百分比 + 提示语（执行中不在这儿显示耗时，由 time-line 接管） -->
        <div class="progress-line" v-if="hasSelection">
          <span class="progress-title">{{ scopeStats.done }} / {{ scopeStats.total }} 已完成</span>
          <span class="progress-pct">{{ scopeStats.percent }}%</span>

          <span class="progress-eta muted" v-if="scopeStats.queued > 0">
            {{ scopeStats.queued }} 个任务待发布，点「开始发布」即可执行
          </span>
          <span class="progress-eta muted" v-else-if="scopeStats.total > 0">
            所选计划已全部完成
          </span>
        </div>

        <el-progress
          v-if="hasSelection"
          :percentage="scopeStats.percent"
          :stroke-width="10"
          :show-text="false"
          :color="scopeStats.failed > 0 ? 'var(--status-warning)' : 'var(--primary-color)'"
        />

        <!-- 行 3：状态统计（只在有勾选时显示） -->
        <div class="stat-chips" v-if="hasSelection">
          <span class="chip ok">✅ 成功 {{ scopeStats.success }}</span>
          <span class="chip running" v-if="scopeStats.running > 0">🔄 发布中 {{ scopeStats.running }}</span>
          <span class="chip fail" v-if="scopeStats.failed > 0">❌ 失败 {{ scopeStats.failed }}</span>
          <span class="chip queued" v-if="scopeStats.queued > 0">⏸ 待发布 {{ scopeStats.queued }}</span>
        </div>

        <!-- 耗时行：仅执行中显示（真实测量，已耗时 + 平均速度 + 剩余预估） -->
        <div class="time-line" v-if="taskStore.isExecuting">
          <span class="tl-item">
            ⏱ 已耗时 <b>{{ humanDuration(elapsedSeconds) }}</b>
          </span>
          <span class="tl-sep">·</span>
          <span class="tl-item" v-if="etaSeconds > 0">
            剩余约 <b>{{ humanDuration(etaSeconds) }}</b>
          </span>
          <span class="tl-sep" v-if="avgSecondsPerTask > 0">·</span>
          <span class="tl-item muted" v-if="avgSecondsPerTask > 0">
            {{ scopeDoneCount }} 条平均 {{ avgSecondsPerTask }} 秒/条
          </span>
          <span class="tl-sep" v-if="etaClock">·</span>
          <span class="tl-item" v-if="etaClock">
            预计 <b>{{ etaClock }}</b> 完成
          </span>
        </div>

        <!-- 行 4：平台进度（有 2 个以上平台或有执行中任务时才显示） -->
        <div class="plat-progress" v-if="platformStats.length > 0">
          <span v-for="ps in platformStats" :key="ps.id" class="plat-item">
            <span class="plat-name">{{ ps.name }}</span>
            <span class="plat-bar">
              <i :style="{ width: ps.percent + '%', background: ps.color }"></i>
            </span>
            <span class="plat-num" :class="{ bad: ps.failed > 0 }">{{ ps.done }}/{{ ps.total }}</span>
          </span>
        </div>

        <!-- 行 5：正在发布 / 最后完成 -->
        <div class="now-publishing" v-if="taskStore.isExecuting && currentTask">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在发布：</span>
          <b class="np-media">{{ taskMediaName(currentTask) }}</b>
          <span class="np-arrow">→</span>
          <span class="plat-dot" :style="{ background: platformColor(currentTask.platform) }" />
          <span class="np-acct">{{ currentTask.nickname || currentTask.account }}</span>
          <span class="np-prog" v-if="currentTask.progress">{{ currentTask.progress }}%</span>
        </div>
        <div class="now-publishing done" v-else-if="lastFinishedTask">
          <el-icon :class="lastFinishedTask.status === 'success' ? 'ok' : 'bad'">
            <CircleCheck v-if="lastFinishedTask.status === 'success'" />
            <CircleClose v-else />
          </el-icon>
          <span>最后完成：</span>
          <b class="np-media">{{ taskMediaName(lastFinishedTask) }}</b>
          <span class="np-arrow">→</span>
          <span class="plat-dot" :style="{ background: platformColor(lastFinishedTask.platform) }" />
          <span class="np-acct">{{ lastFinishedTask.nickname || lastFinishedTask.account }}</span>
          <span class="np-state" :class="lastFinishedTask.status === 'success' ? 'ok' : 'bad'">
            {{ lastFinishedTask.status === 'success' ? '已发布' : '失败' }}
          </span>
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

        <el-tooltip
          v-if="!taskStore.isExecuting"
          :content="!hasSelection ? '请先在下方「发布计划」中勾选要发布的计划' : (scopeStats.queued === 0 ? '选中计划中没有待发布的任务' : '')"
          :disabled="hasSelection && scopeStats.queued > 0"
          placement="top"
        >
          <el-button
            type="primary"
            size="large"
            class="exec-btn gradient-btn-matrix"
            :disabled="!hasSelection || scopeStats.queued === 0"
            @click="handleStartPublish"
          >
            <el-icon><Promotion /></el-icon>
            <span>开始发布 ({{ scopeStats.queued }})</span>
          </el-button>
        </el-tooltip>

        <!-- 次级设置：每条间隔 + 逐个发布提示 -->
        <div class="stats-secondary">
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

          <el-tooltip content="当前为逐个发布（一条发完再发下一条）" placement="top">
            <span class="ghost-hint">
              <el-icon><InfoFilled /></el-icon>
              逐个发布
            </span>
          </el-tooltip>

          <el-button size="small" text class="ghost-btn" @click="openGlobalLogs">
            <el-icon><Monitor /></el-icon>
            <span class="ghost-text">日志</span>
            <span class="log-indicator-dot" v-if="taskStore.runningTasksCount > 0"></span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 2. 计划工作台：左计划列表 + 右发布明细（始终显示；没有计划时由左右两栏各自的空状态来引导用户） -->
    <div class="task-workspace">

      <!-- 左：计划列表 -->
      <div class="task-list-panel glass-card">
        <!-- 工具栏 -->
        <div class="list-toolbar">
          <div class="toolbar-left">
            <span class="idx">2</span>
            <span class="section-name" title="Ctrl / ⌘ + 点击可多选计划">发布计划</span>
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
          </div>
        </div>

        <!-- 计划列表（1 行 = 1 个计划 = 1 个 batchId） -->
        <div class="plan-list-wrap custom-scrollbar">
          <div
            v-for="p in planGroups"
            :key="p.key"
            class="plan-item"
            :class="[p.planStatus, { 'is-selected': selectedPlanId === p.key }]"
            @click="handleSelectPlan(p.key, $event)"
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
            <!-- 空态①：一条计划都没有 -->
            <template v-if="taskStore.tasks.length === 0">
              <FolderIcon :size="22" />
              <span>还没有发布计划</span>
              <el-button size="small" type="primary" link @click="goPublishCenter">
                去「发布工作台」创建
              </el-button>
            </template>
            <!-- 空态②：有计划，只是筛选后为空 -->
            <span v-else>
              {{ listFilter === 'failed' ? '没有失败的计划 🎉' : '当前筛选条件下没有计划' }}
            </span>
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
            <span class="detail-eta" v-if="selectedPlan.running > 0 && etaSeconds > 0">
              预计还需 {{ humanDuration(etaSeconds) }}
            </span>

            <span class="unit-wrap" v-if="maxDetailDepth > 0">
              按
              <select
                :value="detailViewLevel"
                class="level-select"
                title="按这一层的文件夹分组展示明细（只影响查看，不影响发布；每个计划各自记忆）"
                @change="e => (detailViewLevel = Number((e.target as HTMLSelectElement).value))"
              >
                <option v-for="lv in maxDetailDepth" :key="lv" :value="lv">
                  第{{ lv }}层目录
                </option>
                <option :value="0">每条明细</option>
              </select>
              查看
            </span>
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
                    <div class="cell-main" :title="t.params?.filePath || taskMediaName(t)">
                      {{ taskMediaName(t) }}
                    </div>
                    <div class="cell-sub" v-if="taskFolderPath(t)">{{ taskFolderPath(t) }}</div>
                  </td>

                  <td class="col-account">
                    <div class="acct-cell">
                      <span class="acct" :class="t.status" :title="`${t.nickname || t.account} · ${statusText(t)}`">
                        <span class="av" :style="{ background: platformMeta(t.platform).color }">
                          {{ platformMeta(t.platform).short }}
                        </span>
                        <span class="acct-name">{{ t.nickname || t.account }}</span>
                      </span>
                    </div>
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

          <!-- 分组明细（视角 = 按第 N 层）：形态对齐「内容与账号对应表」 -->
          <div class="plan-detail-table custom-scrollbar" v-else>
            <table>
              <thead>
                <tr>
                  <th style="width: 44px">#</th>
                  <th>内容</th>
                  <th style="width: 230px">发布账号</th>
                  <th style="width: 100px">结果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(g, gi) in detailGroups" :key="g.key" class="detail-group-row">
                  <td class="col-order">
                    <span class="order-badge">{{ gi + 1 }}</span>
                  </td>

                  <!-- 内容列：文件夹图标 + 名 + N 条 -->
                  <td class="col-content">
                    <div class="folder-cell" :title="g.label">
                      <FolderIcon v-if="g.label && g.label !== '未分组'" :size="15" />
                      <span v-else class="ic">🎬</span>
                      <span class="gname">{{ g.label }}</span>
                      <span class="cn">{{ g.total }} 条</span>
                    </div>
                  </td>

                  <!-- 发布账号列：账号胶囊（按账号去重聚合，带完成度） -->
                  <td class="col-accts">
                    <div class="chips">
                      <span
                        v-for="a in accountsOfGroup(g)"
                        :key="a.account"
                        class="acct"
                        :class="[a.aggStatus, { 'is-selected': a.tasks.some((t: any) => t.id === selectedTaskId) }]"
                        :title="`${a.nickname} · 成功 ${a.success}/${a.total}${a.failed ? ' · 失败 ' + a.failed : ''}`"
                        @click="selectedTaskId = (a.tasks.find((t: any) => t.status === 'running') || a.tasks.find((t: any) => t.status === 'failed') || a.tasks[0]).id"
                      >
                        <span class="av" :style="{ background: platformMeta(a.platform).color }">
                          {{ platformMeta(a.platform).short }}
                        </span>
                        <span class="acct-name">{{ a.nickname }}</span>
                        <span class="acct-cnt">{{ a.success }}/{{ a.total }}</span>
                        <el-icon v-if="a.aggStatus === 'success'" class="st ok"><CircleCheck /></el-icon>
                        <el-icon v-else-if="a.aggStatus === 'failed'" class="st bad"><CircleClose /></el-icon>
                        <el-icon v-else-if="a.aggStatus === 'running'" class="st run is-loading"><Loading /></el-icon>
                        <el-icon v-else class="st queued"><Clock /></el-icon>
                      </span>
                    </div>
                  </td>

                  <!-- 结果列：汇总 -->
                  <td>
                    <span v-if="g.failed > 0" class="badge bad">{{ g.success }}/{{ g.total }} 成功</span>
                    <span v-else-if="g.running > 0" class="badge run">发布中</span>
                    <span v-else-if="g.success === g.total" class="badge ok">全部完成</span>
                    <span v-else class="badge queued">待发布</span>
                  </td>
                </tr>
              </tbody>
            </table>
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
          <!-- 空态①：还没有任何计划 -->
          <template v-if="!hasPlans">
            <span>还没有可查看的发布明细</span>
            <span class="de-sub">创建发布计划后，这里会展示每条内容的发布进度与结果</span>
            <el-button size="small" type="primary" plain @click="goPublishCenter">
              去创建发布计划
            </el-button>
          </template>
          <!-- 空态②：有计划，但左侧未选中 -->
          <span v-else>点击左侧计划查看发布明细</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, CircleClose, Clock, Delete, Document, InfoFilled, Loading, Monitor, Promotion, Remove, WarningFilled } from '@element-plus/icons-vue'
import FolderIcon from '../components/common/FolderIcon.vue'
import { getPlatformConfig } from '../config/platforms'
import { useTaskStore } from '../stores/taskStore'
import TaskLogDrawer from '../components/matrix/TaskLogDrawer.vue'
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

/** 预计完成时刻（HH:mm） */
const currentTask = computed(() =>
  taskStore.tasks.find((t: any) => t.status === 'running') || null
)

/** 最后完成的任务（没有在执行时展示，避免那一行空着） */
const lastFinishedTask = computed(() => {
  const list = taskStore.tasks.filter((t: any) => t.status === 'success' || t.status === 'failed')
  return list.length > 0 ? list[list.length - 1] : null
})

/** 当前正在执行的计划名 */
const activePlanName = computed(() => {
  const id = taskStore.activePlanId
  if (!id) return ''
  return planGroups.value.find((p: any) => p.key === id)?.name || ''
})

/** 队列位置：第 N / 共 M 个计划 */
const planQueueTotal = computed(() => taskStore.pendingPlanQueue.length)
const planQueueIndex = computed(() => {
  const i = taskStore.pendingPlanQueue.indexOf(taskStore.activePlanId)
  return i >= 0 ? i + 1 : 0
})

/** 各平台的完成进度（用于平台进度条，数据源改为作用域） */
const platformStats = computed(() => {
  const map = new Map<string, { id: string; name: string; color: string; total: number; done: number; success: number; failed: number }>()

  scopeTasks.value.forEach((t: any) => {
    if (!map.has(t.platform)) {
      map.set(t.platform, {
        id: t.platform,
        name: getPlatformStyle(t.platform).name || t.platform,
        color: platformColor(t.platform),
        total: 0, done: 0, success: 0, failed: 0
      })
    }
    const it = map.get(t.platform)!
    it.total++
    if (t.status === 'success') { it.success++; it.done++ }
    else if (t.status === 'failed' || t.status === 'cancelled') { it.failed++; it.done++ }
  })

  return Array.from(map.values()).map((it) => ({
    ...it,
    percent: it.total > 0 ? Math.round((it.done / it.total) * 100) : 0
  }))
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
/**
 * 每个计划各自的查看视角（batchId → level），0 = 逐条明细，N = 按第 N 层目录分组。
 * 不同计划的素材结构可能不同（层数不一样），所以视角必须按计划分别记忆，
 * 不能做成全局设置，否则切到结构不同的计划时会出现空分组。
 */
const planViewLevels = ref<Record<string, number>>({})

/** 当前计划正在使用的查看视角（读、写都落到该计划自己的记录上） */
const detailViewLevel = computed({
  get: () => {
    const id = selectedPlanId.value
    return id ? (planViewLevels.value[id] ?? 0) : 0
  },
  set: (v: number) => {
    const id = selectedPlanId.value
    if (!id) return
    planViewLevels.value = { ...planViewLevels.value, [id]: Number(v) || 0 }
  }
})
/** 当前计划里素材的最大目录深度（用于动态生成选项） */
const maxDetailDepth = computed(() => {
  let max = 0
  selectedPlan.value?.tasks.forEach((t: any) => {
    const n = (t.folderCrumbs || []).length
    if (n > max) max = n
  })
  return max
})

// 视角超出该计划实际层数（如重新导入了更浅的素材）→ 自动回退到逐条，避免出现空分组
watch(
  [() => selectedPlanId.value, () => maxDetailDepth.value],
  () => {
    const id = selectedPlanId.value
    if (!id) return
    const cur = planViewLevels.value[id] ?? 0
    if (cur > maxDetailDepth.value) {
      planViewLevels.value = { ...planViewLevels.value, [id]: 0 }
    }
  },
  { immediate: true }
)

/**
 * 把分组内的任务按【账号】聚合：一个账号一个胶囊。
 * 胶囊状态取该账号下最需要关注的那个（失败 > 执行中 > 全成功 > 待发）。
 */
function accountsOfGroup(g: any) {
  const map = new Map<string, {
    platform: string
    account: string
    nickname: string
    tasks: any[]
  }>()

  g.tasks.forEach((t: any) => {
    const key = `${t.platform}:${t.account}`
    if (!map.has(key)) {
      map.set(key, {
        platform: t.platform,
        account: t.account,
        nickname: t.nickname || t.account,
        tasks: []
      })
    }
    map.get(key)!.tasks.push(t)
  })

  return Array.from(map.values()).map((a) => {
    const total   = a.tasks.length
    const success = a.tasks.filter((t: any) => t.status === 'success').length
    const failed  = a.tasks.filter((t: any) => t.status === 'failed').length
    const running = a.tasks.filter((t: any) => t.status === 'running').length
    const aggStatus = failed > 0 ? 'failed'
                    : running > 0 ? 'running'
                    : success === total ? 'success'
                    : 'queued'
    return { ...a, total, success, failed, running, aggStatus }
  })
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

/** 切换计划时清空任务选中（视角不再重置——每个计划保留自己的） */
watch(selectedPlanId, () => {
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

/** 该条任务实际发布的视频文件名（从 params.filePath 取，不要用批次那串拼接名） */
function taskMediaName(t: any): string {
  const p = t.params?.filePath || t.filePath || ''
  if (p) {
    const seg = p.split(/[\\/]/).pop() || ''
    if (seg) return seg
  }
  return t.title || '—'
}

/** 该条任务所属文件夹路径（去掉根文件夹名，更贴近用户视角） */
function taskFolderPath(t: any): string {
  const c: string[] = t.folderCrumbs || []
  return c.length > 1 ? c.slice(1).join(' / ') : ''
}

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
/** 日志抽屉默认定位的标签页 */
const drawerInitialTab = ref<'terminal' | 'live'>('terminal')

/** 平台色 */
function platformColor(platform: string): string {
  return getPlatformStyle(platform).brandColor || 'var(--text-muted)'
}

/** 平台简称 + 配色（与 ContentAccountTable.vue 保持同一套实现） */
function platformMeta(p: string): { short: string; color: string } {
  const PLATFORM_META: Record<string, { short: string; color: string }> = {
    douyin: { short: '抖', color: '#000000' },
    tencent: { short: '视', color: '#FA9D3B' },
    wechat: { short: '视', color: '#FA9D3B' },
    kuaishou: { short: '快', color: '#FF4906' },
    xiaohongshu: { short: '红', color: '#FF2442' },
    redbook: { short: '红', color: '#FF2442' },
    bilibili: { short: 'B', color: '#FB7299' },
  }
  const hit = PLATFORM_META[(p || '').toLowerCase()]
  if (hit) return hit
  let h = 0
  const s = p || '?'
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return { short: s.slice(0, 1).toUpperCase(), color: `hsl(${h}, 55%, 45%)` }
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

/** 控制台的作用域任务：勾选了计划 → 只算这些；没勾选 → 空（统计归零） */
const scopeTasks = computed(() => {
  if (checkedPlanIds.value.length === 0) return []
  const set = new Set(checkedPlanIds.value)
  return taskStore.tasks.filter((t: any) => set.has(t.batchId))
})

/** 作用域内的统计（发布控制台所有数字都用它） */
const scopeStats = computed(() => {
  const list = scopeTasks.value
  const success = list.filter((t: any) => t.status === 'success').length
  const failed  = list.filter((t: any) => t.status === 'failed' || t.status === 'cancelled').length
  const running = list.filter((t: any) => t.status === 'running').length
  const queued  = list.filter((t: any) => t.status === 'queued').length
  const total = list.length
  const done = success + failed
  return {
    total, success, failed, running, queued, done,
    percent: total > 0 ? Math.round((done / total) * 100) : 0
  }
})

/** 是否已有任何计划 */
const hasPlans = computed(() => planGroups.value.length > 0)

/** 跳到发布工作台去创建计划 */
const router = useRouter()
function goPublishCenter() {
  router.push('/')
}

/** 是否勾选了计划 */
const hasSelection = computed(() => checkedPlanIds.value.length > 0)

/** 心跳计时器：每秒更新一次，驱动 elapsedSeconds 刷新 */
const nowTick = ref(Date.now())
let tickTimer: number | undefined
onMounted(() => { tickTimer = window.setInterval(() => { nowTick.value = Date.now() }, 1000) })
onUnmounted(() => { if (tickTimer) window.clearInterval(tickTimer) })

/** 本次执行已耗时（秒） */
const elapsedSeconds = computed(() => {
  if (!taskStore.isExecuting || !taskStore.executionStartedAt) return 0
  // 引用 nowTick 以建立响应式依赖，保证每秒更新
  void nowTick.value
  return Math.max(0, Math.floor((Date.now() - taskStore.executionStartedAt) / 1000))
})

/** 当前作用域内已完成数（用于算平均速度） */
const scopeDoneCount = computed(() => scopeStats.value.done)

/** 平均每条任务耗时（秒）；样本不足时返回 0 */
const avgSecondsPerTask = computed(() => {
  const done = scopeDoneCount.value
  if (done === 0 || elapsedSeconds.value === 0) return 0
  return Math.round((elapsedSeconds.value * Math.max(1, taskStore.lanes.length)) / done)
})

/** 剩余预估秒数（按真实平均速度） */
const etaSeconds = computed(() => {
  const remain = scopeStats.value.total - scopeStats.value.done
  if (remain <= 0) return 0
  const avg = avgSecondsPerTask.value || 90
  return Math.round((remain * avg) / Math.max(1, taskStore.lanes.length))
})

/** 人类可读的时长：1 分 32 秒 / 12 秒 / 1 小时 5 分 */
function humanDuration(sec: number): string {
  if (sec <= 0) return '0 秒'
  if (sec < 60) return `${sec} 秒`
  const m = Math.floor(sec / 60)
  if (m < 60) return `${m} 分${sec % 60 > 0 ? ' ' + (sec % 60) + ' 秒' : ''}`
  const h = Math.floor(m / 60)
  return `${h} 小时 ${m % 60} 分`
}

/** 预计完成时刻（HH:mm） */
const etaClock = computed(() => {
  if (etaSeconds.value <= 0) return ''
  const d = new Date(Date.now() + etaSeconds.value * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
})

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
function handleSelectPlan(batchId: string, e?: MouseEvent) {
  // Ctrl / ⌘ + 点击 = 切换多选（不必精准点小勾选框）
  if (e && (e.ctrlKey || e.metaKey)) {
    if (checkedPlanIds.value.includes(batchId)) {
      checkedPlanIds.value = checkedPlanIds.value.filter((id) => id !== batchId)
    } else {
      checkedPlanIds.value = [...checkedPlanIds.value, batchId]
    }
    return
  }

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
  /* 不要写死 100vh —— 外层 .page-content 有 18px 内边距，
     写死会导致整体超高、底部被裁，滚动条看不到 */
  height: 100%;
  min-height: 0;
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

/* ---- 发布控制台：信息行 ---- */
.progress-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.head-plan { font-size: 12px; color: var(--text-muted); margin-left: 4px; }
.head-plan b { color: var(--text-main); font-weight: 600; }
.queue-pos { color: var(--primary-color); font-weight: 600; }

/* 未选计划时的空态提示（虚线框暗示"待完成"状态） */
.console-empty-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-main);
  background: rgba(79, 70, 229, 0.07);
  border: 1px dashed rgba(79, 70, 229, 0.32);
}
.console-empty-hint .hint-ic {
  font-size: 15px;
  color: var(--primary-color);
  flex-shrink: 0;
}
.console-empty-hint b { color: var(--primary-color); font-weight: 600; }
.console-empty-hint .hint-sub { color: var(--text-muted); font-size: 11.5px; }
.console-empty-hint .hint-btn { margin-left: auto; flex-shrink: 0; }

.progress-line { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.progress-title { font-size: 15px; font-weight: 700; color: var(--text-main); }
.progress-pct { font-size: 13px; font-weight: 700; color: var(--primary-color); font-variant-numeric: tabular-nums; }
.progress-eta { font-size: 12px; color: var(--text-muted); }
.progress-eta.muted { opacity: .8; }

/* 耗时行：真实测量已耗时 + 剩余预估 */
.time-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-main);
}
.tl-item b { color: var(--primary-color); font-variant-numeric: tabular-nums; }
.tl-item.muted { color: var(--text-muted); }
.tl-sep { color: var(--border-subtle); }

/* 平台进度 */
.plat-progress { display: flex; flex-wrap: wrap; gap: 14px; }
.plat-item { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; }
.plat-name { color: var(--text-muted); white-space: nowrap; }
.plat-bar {
  width: 54px; height: 5px; border-radius: 3px;
  background: var(--bg-input); overflow: hidden; flex-shrink: 0;
}
.plat-bar > i { display: block; height: 100%; border-radius: 3px; transition: width .3s; }
.plat-num { color: var(--text-main); font-weight: 600; font-variant-numeric: tabular-nums; }
.plat-num.bad { color: var(--status-danger); }

/* 正在发布 / 最后完成 */
.now-publishing {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-muted);
  padding: 6px 10px; border-radius: 7px;
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.18);
  min-width: 0;
}
.now-publishing.done { background: var(--bg-input); border-color: var(--border-subtle); }
.np-media { color: var(--text-main); font-weight: 600; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.np-arrow { color: var(--text-muted); }
.np-acct { color: var(--text-main); }
.np-prog { color: var(--primary-color); font-weight: 600; margin-left: 2px; }
.np-state.ok  { color: var(--status-success); font-weight: 600; }
.np-state.bad { color: var(--status-danger); font-weight: 600; }
.now-publishing .el-icon.ok  { color: var(--status-success); }
.now-publishing .el-icon.bad { color: var(--status-danger); }

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

.ghost-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: default;
}

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

/* 复选框：占一块 28x28 的热区，不用精准点击小方块 */
.plan-check {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-left: -6px;
  margin-right: 0;
  cursor: pointer;
}
/* 勾选框本体也放大一档，更好看 */
.plan-check :deep(.el-checkbox__inner) {
  width: 16px;
  height: 16px;
}
.plan-check :deep(.el-checkbox__inner::after) {
  left: 5px;
  top: 2px;
}
/* 悬停时给个反馈，暗示"这里可以点" */
.plan-item:hover .plan-check :deep(.el-checkbox__inner) {
  border-color: var(--primary-color);
}

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
/* 单位选择器：与「发布工作台 / 上传视频」同款（透明底 + 无框 + 主色字） */
.unit-wrap {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.level-select {
  font-size: 11px;
  font-weight: 600;
  padding: 0;
  margin: 0;
  border-radius: 6px;
  line-height: 17px;
  color: var(--primary-color);
  background: transparent;
  border: none;
  cursor: pointer;
  outline: none;
}

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
  flex: 1 1 auto;
  min-height: 0;
  /* 兜底：即使上面几层 flex 高度链没传下来，也保证表格内部可滚 */
  max-height: 52vh;
  overflow-y: auto;
  overscroll-behavior: contain;
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
.cell-sub  { font-size: 11px; color: var(--text-muted); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
  max-height: 480px;          
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
  margin-top: 8px;
}
.logs-title { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
.logs-list {
  flex: 1; min-height: 0; overflow-y: auto;
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
.detail-empty .de-sub { font-size: 11.5px; color: var(--text-muted); opacity: .85; }



/* ---- 分组明细行：与「内容与账号对应表」同款 ---- */
.detail-group-row td { padding: 9px 12px; border-bottom: 1px solid var(--border-subtle); vertical-align: middle; }
.detail-group-row:hover td { background: rgba(99, 102, 241, 0.06); }

/* 序号圆标 */
.order-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  font-size: 11px; font-weight: 700;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
}

/* 内容列 */
.folder-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
.folder-cell .ic { font-size: 14px; flex-shrink: 0; }
.gname { font-size: 12px; font-weight: 600; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cn { font-size: 11px; color: var(--text-muted); flex-shrink: 0; }

/* 账号胶囊（与 ContentAccountTable.vue 同款） */
.chips { display: flex; flex-wrap: wrap; gap: 5px; }
.acct {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; padding: 2px 8px 2px 3px;
  border-radius: 11px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-input);
  color: var(--text-main);
  cursor: pointer;
  transition: border-color .14s, background-color .14s;
}
.acct:hover { border-color: var(--primary-color); }
.acct.is-selected { border-color: var(--primary-color); background: rgba(79, 70, 229, 0.10); }
.acct .av {
  width: 15px; height: 15px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 700; color: #fff; flex-shrink: 0;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22);
}
.acct .acct-name { max-width: 92px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acct .acct-cnt { font-size: 10px; color: var(--text-muted); flex-shrink: 0; font-variant-numeric: tabular-nums; }
.acct.success .acct-cnt { color: var(--status-success); }
.acct.failed  .acct-cnt { color: var(--status-danger); }
.acct .st { font-size: 11px; flex-shrink: 0; }
.acct .st.ok { color: var(--status-success); }
.acct .st.bad { color: var(--status-danger); }
.acct .st.run { color: var(--primary-color); }
.acct .st.queued { color: var(--text-muted); }

/* 表格单元格里的账号胶囊：不换行、不撑破列宽 */
/* ⚠️ flex 不能加在 <td> 上，否则 td 失去 table-cell 身份导致行高/边框错位 */
.acct-cell { display: flex; align-items: center; min-width: 0; }
.col-account .acct { max-width: 100%; vertical-align: middle; }
.col-account .acct-name { max-width: 110px; }

/* 平台小圆点（正在发布行里还在用） */
.plat-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* 结果 badge */
.badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.badge.ok     { color: var(--status-success); background: rgba(16, 185, 129, 0.10); }
.badge.bad    { color: var(--status-danger);  background: rgba(239, 68, 68, 0.10); }
.badge.run    { color: var(--primary-color);  background: rgba(79, 70, 229, 0.10); }
.badge.queued { color: var(--text-muted);     background: var(--bg-input); }

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
