<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 class="text-2xl font-bold tracking-tight text-surface-900 dark:text-surface-0">Issue 工作台</h2>
              <p class="text-sm text-surface-500 dark:text-surface-400">跨审查问题视图，支持筛选、批量状态更新与快速处理</p>
            </div>
            <div class="flex items-center gap-2">
              <Button label="重置筛选" text size="small" :disabled="loading" @click="resetFilters" />
              <Button label="查询" size="small" :loading="loading" @click="handleSearch" />
            </div>
          </div>

          <div class="grid grid-cols-1 gap-3 lg:grid-cols-3 xl:grid-cols-4">
            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">项目</span>
              <Select
                v-model="selectedProjectId"
                :options="projectOptions"
                option-label="label"
                option-value="value"
                class="w-full"
                placeholder="全部项目"
              />
            </label>

            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">严重度</span>
              <Select
                v-model="selectedSeverity"
                :options="severityOptions"
                option-label="label"
                option-value="value"
                class="w-full"
                placeholder="全部严重度"
              />
            </label>

            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">审查状态</span>
              <Select
                v-model="selectedReviewStatus"
                :options="reviewStatusOptions"
                option-label="label"
                option-value="value"
                class="w-full"
                placeholder="全部状态"
              />
            </label>

            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">处理状态</span>
              <Select
                v-model="selectedActionStatus"
                :options="actionStatusOptions"
                option-label="label"
                option-value="value"
                class="w-full"
                placeholder="全部处理状态"
              />
            </label>

            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">开始时间</span>
              <InputText v-model="startAt" type="datetime-local" class="w-full" />
            </label>

            <label class="flex flex-col gap-1">
              <span class="text-xs text-surface-500">结束时间</span>
              <InputText v-model="endAt" type="datetime-local" class="w-full" />
            </label>

            <label class="flex flex-col gap-1 xl:col-span-2">
              <span class="text-xs text-surface-500">作者</span>
              <InputText
                v-model="author"
                class="w-full"
                placeholder="按作者姓名或邮箱匹配"
                @keydown.enter="handleSearch"
              />
            </label>
          </div>
        </div>
      </template>
    </Card>

    <Card v-if="selectedCount > 0">
      <template #content>
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div class="space-y-2">
            <div class="text-sm font-medium text-surface-800 dark:text-surface-100">已选择 {{ selectedCount }} 项（仅当前页）</div>
            <div class="flex flex-wrap gap-2">
              <Button size="small" severity="success" :loading="batchLoading" @click="submitBatchAction('fixed')">标记已修复</Button>
              <Button size="small" severity="warn" :loading="batchLoading" @click="submitBatchAction('todo')">标记待处理</Button>
              <Button size="small" severity="secondary" :loading="batchLoading" @click="submitBatchAction('ignored')">标记已忽略</Button>
              <Button size="small" severity="info" :loading="batchLoading" @click="submitBatchAction('reopened')">标记重新打开</Button>
            </div>
          </div>
          <div class="grid w-full grid-cols-1 gap-2 lg:w-[460px]">
            <InputText v-model="actionActor" placeholder="处理人（默认当前登录用户）" />
            <Textarea v-model="actionNote" rows="2" placeholder="处理备注（可选）" />
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="relative overflow-x-auto">
          <table class="w-full min-w-[1280px] text-sm text-surface-800 dark:text-surface-100">
            <thead>
              <tr class="border-b border-surface-200/70 text-left text-xs font-semibold uppercase tracking-wide text-surface-600 dark:border-surface-600/70 dark:bg-surface-800/40 dark:text-surface-200">
                <th class="w-10 px-2 py-3">
                  <Checkbox
                    binary
                    :model-value="isCurrentPageAllSelected"
                    :indeterminate="isCurrentPagePartiallySelected && !isCurrentPageAllSelected"
                    @change="toggleSelectAllCurrentPage"
                  />
                </th>
                <th class="px-2 py-3">项目</th>
                <th class="px-2 py-3">MR</th>
                <th class="px-2 py-3">文件/行</th>
                <th class="px-2 py-3">严重度</th>
                <th class="min-w-[280px] px-2 py-3">问题描述</th>
                <th class="px-2 py-3">作者</th>
                <th class="px-2 py-3">审查状态</th>
                <th class="px-2 py-3">处理状态</th>
                <th class="px-2 py-3">最近处理</th>
                <th class="px-2 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in findings"
                :key="row.id"
                class="border-b border-surface-100/80 align-top transition hover:bg-surface-50/70 dark:border-surface-700/70 dark:hover:bg-surface-700/55"
              >
                <td class="px-2 py-3">
                  <Checkbox binary :model-value="isSelected(row.id)" @change="toggleSelectRow(row.id)" />
                </td>
                <td class="px-2 py-3 text-surface-800 dark:text-surface-100">{{ row.review.project_name || '-' }}</td>
                <td class="px-2 py-3">
                  <div class="space-y-1">
                    <Tag severity="info">!{{ row.review.merge_request_iid }}</Tag>
                    <button
                      type="button"
                      class="block text-xs text-primary hover:underline"
                      @click="goToReview(row.review.id)"
                    >
                      审查 #{{ row.review.id }}
                    </button>
                  </div>
                </td>
                <td class="px-2 py-3">
                  <div class="max-w-[300px] break-all font-mono text-xs text-surface-700 dark:text-surface-200">{{ row.file_path || '-' }}</div>
                  <div class="text-xs text-surface-500">{{ formatLineRange(row.line_start, row.line_end) }}</div>
                </td>
                <td class="px-2 py-3">
                  <Tag :severity="severityTag(row.severity)">{{ severityLabel(row.severity) }}</Tag>
                </td>
                <td class="px-2 py-3">
                  <p class="line-clamp-3 leading-5 text-surface-800 dark:text-surface-100">{{ row.message || '-' }}</p>
                </td>
                <td class="px-2 py-3 text-surface-700 dark:text-surface-200">{{ row.review.author_name || row.review.author_email || '-' }}</td>
                <td class="px-2 py-3">
                  <Tag :severity="reviewStatusSeverity(row.review.status)">{{ reviewStatusLabel(row.review.status) }}</Tag>
                </td>
                <td class="px-2 py-3">
                  <Tag :severity="actionStatusSeverity(row.action_status)">{{ actionStatusLabel(row.action_status) }}</Tag>
                </td>
                <td class="px-2 py-3 text-xs text-surface-600 dark:text-surface-300">
                  <template v-if="row.latest_action">
                    <div class="font-medium text-surface-700 dark:text-surface-200">{{ row.latest_action.actor || '-' }}</div>
                    <div>{{ formatDisplayTime(row.latest_action.action_at) }}</div>
                  </template>
                  <span v-else>-</span>
                </td>
                <td class="px-2 py-3 text-right">
                  <div class="flex justify-end gap-1">
                    <Button size="small" text @click="goToReview(row.review.id)">详情</Button>
                    <Button size="small" text severity="success" :loading="rowActionLoadingId === row.id" @click="submitRowAction(row.id, 'fixed')">修复</Button>
                    <Button size="small" text severity="warn" :loading="rowActionLoadingId === row.id" @click="submitRowAction(row.id, 'todo')">待办</Button>
                    <Button size="small" text severity="secondary" :loading="rowActionLoadingId === row.id" @click="submitRowAction(row.id, 'ignored')">忽略</Button>
                    <Button size="small" text severity="info" :loading="rowActionLoadingId === row.id" @click="submitRowAction(row.id, 'reopened')">重开</Button>
                  </div>
                </td>
              </tr>
              <tr v-if="!loading && findings.length === 0">
                <td colspan="11" class="px-3 py-10 text-center text-surface-500 dark:text-surface-400">暂无符合条件的问题记录</td>
              </tr>
            </tbody>
          </table>

          <div v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur-[1px] dark:bg-surface-900/70">
            <div class="inline-flex items-center gap-2 rounded-lg border border-surface-200 bg-white px-3 py-2 text-surface-600 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
              <Loader2 class="h-4 w-4 animate-spin" />
              加载中...
            </div>
          </div>
        </div>

        <div class="mt-4 flex flex-col gap-3 border-t border-surface-200/60 pt-4 sm:flex-row sm:items-center sm:justify-between dark:border-surface-700/60">
          <span class="text-xs text-surface-500 dark:text-surface-400">共 {{ total }} 条记录</span>
          <div class="flex items-center gap-2">
            <Button text size="small" :disabled="currentPage <= 1 || loading" @click="changePage(currentPage - 1)">上一页</Button>
            <span class="text-xs text-surface-600 dark:text-surface-300">第 {{ currentPage }} / {{ totalPages }} 页</span>
            <Button text size="small" :disabled="currentPage >= totalPages || loading" @click="changePage(currentPage + 1)">下一页</Button>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import { createReviewFindingActionsBatch, getProjects, getReviewFindingsList } from '@/api/index'
import { formatBackendDateTime } from '@/utils/datetime'
import { getReviewStatusMeta } from '@/utils/reviewStatus'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

type FindingActionType = 'fixed' | 'ignored' | 'todo' | 'reopened'

interface WorkbenchReviewMeta {
  id: number
  project_id: number
  project_name: string
  merge_request_iid: number
  merge_request_title: string
  author_name: string
  author_email: string
  status: string
  created_at: string | null
}

interface WorkbenchActionMeta {
  id: number
  finding_id: number
  action_type: string
  actor: string
  note: string
  action_at: string | null
}

interface WorkbenchFinding {
  id: number
  review_id: number
  severity: string
  file_path: string
  line_start: number | null
  line_end: number | null
  message: string
  created_at: string | null
  action_status: string
  latest_action: WorkbenchActionMeta | null
  review: WorkbenchReviewMeta
}

interface ProjectOption {
  label: string
  value: number | null
}

const router = useRouter()
const auth = useAuthStore()
auth.hydrate()

const loading = ref(false)
const batchLoading = ref(false)
const rowActionLoadingId = ref<number | null>(null)

const findings = ref<WorkbenchFinding[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const selectedIds = ref<number[]>([])

const selectedProjectId = ref<number | null>(null)
const selectedSeverity = ref('')
const selectedReviewStatus = ref('')
const selectedActionStatus = ref('')
const author = ref('')
const startAt = ref('')
const endAt = ref('')

const actionActor = ref(auth.username || '')
const actionNote = ref('')

const projectOptions = ref<ProjectOption[]>([{ label: '全部项目', value: null }])

const severityOptions = [
  { label: '全部严重度', value: '' },
  { label: '阻断 (critical)', value: 'critical' },
  { label: '严重 (high)', value: 'high' },
  { label: '中等 (medium)', value: 'medium' },
  { label: '轻微 (low)', value: 'low' },
]

const reviewStatusOptions = [
  { label: '全部状态', value: '' },
  { label: '等待中', value: 'pending' },
  { label: '进行中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const actionStatusOptions = [
  { label: '全部处理状态', value: '' },
  { label: '未处理', value: 'unprocessed' },
  { label: '已修复', value: 'fixed' },
  { label: '待处理', value: 'todo' },
  { label: '已忽略', value: 'ignored' },
  { label: '重新打开', value: 'reopened' },
]

const selectedCount = computed(() => selectedIds.value.length)

const totalPages = computed(() => {
  const pages = Math.ceil(total.value / pageSize.value)
  return Math.max(pages, 1)
})

const currentPageIds = computed(() => findings.value.map((item) => item.id))

const isCurrentPageAllSelected = computed(() => {
  if (currentPageIds.value.length === 0) return false
  return currentPageIds.value.every((id) => selectedIds.value.includes(id))
})

const isCurrentPagePartiallySelected = computed(() => {
  if (currentPageIds.value.length === 0) return false
  const selectedOnPage = currentPageIds.value.filter((id) => selectedIds.value.includes(id)).length
  return selectedOnPage > 0 && selectedOnPage < currentPageIds.value.length
})

const clearSelection = () => {
  selectedIds.value = []
}

const toIsoString = (value: string): string | undefined => {
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const parsed = new Date(trimmed)
  if (Number.isNaN(parsed.getTime())) return undefined
  return parsed.toISOString()
}

const fetchProjects = async () => {
  try {
    const unique = new Map<number, ProjectOption>()
    let page = 1
    let expectedTotal = 0
    let loadedCount = 0
    const maxPages = 200

    while (page <= maxPages) {
      const resp = await getProjects({ page })
      const results = Array.isArray(resp?.results) ? resp.results : []
      expectedTotal = Number(resp?.count || expectedTotal || 0)
      if (results.length === 0) break

      for (const item of results) {
        const projectId = typeof item?.project_id === 'number' ? item.project_id : null
        if (projectId == null) continue
        unique.set(projectId, {
          label: String(item?.project_name || `项目 ${projectId}`),
          value: projectId,
        })
      }

      loadedCount += results.length
      if (expectedTotal > 0 && loadedCount >= expectedTotal) break
      page += 1
    }

    projectOptions.value = [{ label: '全部项目', value: null }, ...[...unique.values()].sort((a, b) => a.label.localeCompare(b.label))]
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

const fetchFindings = async (allowClamp: boolean = true) => {
  loading.value = true
  clearSelection()
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      project_id: selectedProjectId.value ?? undefined,
      severities: selectedSeverity.value || undefined,
      review_statuses: selectedReviewStatus.value || undefined,
      action_statuses: selectedActionStatus.value || undefined,
      author: author.value.trim() || undefined,
      start_at: toIsoString(startAt.value),
      end_at: toIsoString(endAt.value),
    }

    const resp = await getReviewFindingsList(params)
    findings.value = Array.isArray(resp?.results) ? resp.results : []
    total.value = Number(resp?.total || resp?.count || 0)
    if (allowClamp) {
      const pages = Math.max(Math.ceil(total.value / pageSize.value), 1)
      if (currentPage.value > pages) {
        currentPage.value = pages
        await fetchFindings(false)
        return
      }
    }
  } catch (error: any) {
    console.error('获取 Issue 工作台列表失败:', error)
    toast.error(error?.response?.data?.detail || '获取 Issue 工作台列表失败')
    findings.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchFindings()
}

const resetFilters = () => {
  selectedProjectId.value = null
  selectedSeverity.value = ''
  selectedReviewStatus.value = ''
  selectedActionStatus.value = ''
  author.value = ''
  startAt.value = ''
  endAt.value = ''
  currentPage.value = 1
  fetchFindings()
}

const changePage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchFindings()
}

const isSelected = (id: number): boolean => selectedIds.value.includes(id)

const toggleSelectRow = (id: number) => {
  if (isSelected(id)) {
    selectedIds.value = selectedIds.value.filter((item) => item !== id)
    return
  }
  selectedIds.value = [...selectedIds.value, id]
}

const toggleSelectAllCurrentPage = () => {
  if (isCurrentPageAllSelected.value) {
    selectedIds.value = []
    return
  }
  selectedIds.value = [...currentPageIds.value]
}

const doBatchAction = async (actionType: FindingActionType, ids: number[]) => {
  const actor = actionActor.value.trim()
  if (!actor) {
    toast.warning('请先填写处理人')
    return false
  }
  if (ids.length === 0) {
    toast.warning('请先选择要处理的记录')
    return false
  }

  try {
    const resp = await createReviewFindingActionsBatch({
      finding_ids: ids,
      action_type: actionType,
      actor,
      note: actionNote.value.trim(),
    })

    const successCount = Number(resp?.success_count || 0)
    const failedCount = Number(resp?.failed_count || 0)
    if (failedCount > 0) {
      toast.warning(`批量处理完成，成功 ${successCount} 条，失败 ${failedCount} 条`)
    } else {
      toast.success(`批量处理成功，共 ${successCount} 条`)
    }
    return true
  } catch (error: any) {
    console.error('批量处理失败:', error)
    toast.error(error?.response?.data?.detail || '批量处理失败')
    return false
  }
}

const submitBatchAction = async (actionType: FindingActionType) => {
  batchLoading.value = true
  try {
    const ok = await doBatchAction(actionType, selectedIds.value)
    if (!ok) return
    actionNote.value = ''
    clearSelection()
    await fetchFindings()
  } finally {
    batchLoading.value = false
  }
}

const submitRowAction = async (id: number, actionType: FindingActionType) => {
  rowActionLoadingId.value = id
  try {
    const ok = await doBatchAction(actionType, [id])
    if (!ok) return
    actionNote.value = ''
    clearSelection()
    await fetchFindings()
  } finally {
    rowActionLoadingId.value = null
  }
}

const goToReview = (reviewId: number) => {
  router.push(`/reviews/${reviewId}`)
}

const formatLineRange = (lineStart: number | null, lineEnd: number | null): string => {
  if (lineStart == null) return '行号 -'
  if (lineEnd != null && lineEnd !== lineStart) return `L${lineStart}-L${lineEnd}`
  return `L${lineStart}`
}

const severityTag = (severity: string): 'danger' | 'warn' | 'success' | 'secondary' => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical' || normalized === 'high') return 'danger'
  if (normalized === 'medium') return 'warn'
  if (normalized === 'low') return 'success'
  return 'secondary'
}

const severityLabel = (severity: string): string => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical') return '阻断'
  if (normalized === 'high') return '严重'
  if (normalized === 'medium') return '中等'
  if (normalized === 'low') return '轻微'
  return severity || '未知'
}

const actionStatusLabel = (status: string): string => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'unprocessed') return '未处理'
  if (normalized === 'fixed') return '已修复'
  if (normalized === 'todo') return '待处理'
  if (normalized === 'ignored') return '已忽略'
  if (normalized === 'reopened') return '重新打开'
  return status || '未知'
}

const actionStatusSeverity = (status: string): 'success' | 'warn' | 'info' | 'secondary' => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'fixed') return 'success'
  if (normalized === 'todo') return 'warn'
  if (normalized === 'reopened') return 'info'
  return 'secondary'
}

const reviewStatusLabel = (status: string): string => getReviewStatusMeta(status).label
const reviewStatusSeverity = (status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' => getReviewStatusMeta(status).severity

const formatDisplayTime = (value: string | null | undefined): string => formatBackendDateTime(value)

onMounted(async () => {
  await fetchProjects()
  await fetchFindings()
})
</script>
