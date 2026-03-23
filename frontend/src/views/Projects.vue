<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight text-color">项目管理</h1>
        <p class="mt-1 text-xs text-surface-500">Manage webhook-enabled GitLab projects</p>
      </div>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Button outlined label="从 GitLab 导入" @click="openImportModal">
          <template #icon><Download class="h-4 w-4" /></template>
        </Button>
        <label class="block w-full sm:w-64">
          <IconField class="w-full">
            <InputIcon class="text-surface-400">
              <Search class="h-4 w-4" />
            </InputIcon>
            <InputText
              v-model="searchQuery"
              placeholder="搜索项目..."
              class="w-full shadow-sm"
            />
          </IconField>
        </label>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-muted-color">总项目数</div>
          <div class="mb-1 text-4xl font-bold tracking-tight text-color">{{ stats.totalProjects }}</div>
          <div class="text-2xs text-muted-color">已配置 Webhook</div>
        </div>
        <FolderKanban class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-primary/25 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-muted-color">活跃项目</div>
          <div class="mb-1 text-4xl font-bold tracking-tight text-color">{{ stats.activeProjects }}</div>
          <div class="text-2xs text-green-600 dark:text-green-300">审查功能已开启</div>
        </div>
        <CheckCircle2 class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-green-500/20 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-muted-color">本周审查</div>
          <div class="mb-1 text-4xl font-bold tracking-tight text-color">{{ stats.weeklyReviews }}</div>
          <div class="text-2xs text-muted-color">活跃项目审查</div>
        </div>
        <Activity class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-purple-500/20 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-muted-color">最近事件</div>
          <div class="mb-1 text-4xl font-bold tracking-tight text-color">{{ stats.recentEvents }}</div>
          <div class="text-2xs text-muted-color">24小时内</div>
        </div>
        <GitPullRequest class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-orange-500/20 dark:text-surface-600/40" />
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      <Card
        v-for="project in filteredProjects"
        :key="project.project_id"
        class="group h-full !rounded-2xl !border !border-surface-200/60 !bg-surface-0 !shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:!shadow-lg dark:!border-surface-700/60 dark:!bg-surface-900"
        :pt="{ body: { class: 'p-4 flex flex-col gap-1.5' } }"
      >
        <template #content>
          <div class="space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div class="flex min-w-0 flex-1 items-start gap-2.5">
                <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-600 shadow-md">
                  <GitBranch class="h-5 w-5 text-white" />
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="truncate text-sm font-semibold text-surface-900 transition-colors group-hover:text-primary-600 dark:text-surface-0">
                    {{ project.project_name }}
                  </h3>
                  <p class="mt-0.5 truncate text-xs text-surface-500">{{ project.namespace }}</p>
                </div>
              </div>
              <ToggleSwitch
                :model-value="isReviewEnabled(project.review_enabled)"
                :disabled="loading"
                @change="() => toggleProjectReview(project.project_id)"
              />
            </div>

            <p class="min-h-9 text-sm text-surface-600 line-clamp-2">
              {{ project.description || '暂无项目描述' }}
            </p>

            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-surface-200/50 pt-2">
              <div class="flex items-center gap-1.5 text-xs text-surface-600">
                <GitCommit class="h-3 w-3" />
                <span>{{ project.commits_count || 0 }} commits</span>
              </div>
              <div class="flex items-center gap-1.5 text-xs text-surface-600">
                <GitPullRequest class="h-3 w-3" />
                <span>{{ project.mr_count || 0 }} MRs</span>
              </div>
              <div class="flex items-center gap-1.5 text-xs text-surface-600">
                <Users class="h-3 w-3" />
                <span>{{ project.members_count || 0 }}</span>
              </div>
            </div>

            <div class="flex items-center justify-between gap-2 pt-1">
              <div class="flex min-w-0 items-center gap-1.5 text-xs text-surface-500">
                <Clock class="h-3 w-3 flex-shrink-0" />
                <span class="truncate">{{ project.last_activity || '未知' }}</span>
              </div>
              <Tag :severity="isReviewEnabled(project.review_enabled) ? 'success' : 'secondary'" class="text-xs">
                {{ isReviewEnabled(project.review_enabled) ? '审查已开启' : '审查已关闭' }}
              </Tag>
            </div>

            <div class="flex gap-1.5 pt-1">
              <Button size="small" class="min-w-0 flex-1" :disabled="loading" @click="viewProjectDetail(project.project_id)">
                <span class="inline-flex min-w-0 items-center gap-1.5">
                  <Eye class="h-3.5 w-3.5 shrink-0" />
                  <span class="truncate">查看详情</span>
                </span>
              </Button>
              <IconButton size="small" aria-label="打开 Webhook 地址" @click="openWebhookUrl(project.webhook_url)">
                <ExternalLink class="h-3.5 w-3.5" />
              </IconButton>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <Card v-if="filteredProjects.length === 0">
      <template #content>
        <div class="py-10 text-center">
          <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-surface-100">
            <FolderKanban class="h-8 w-8 text-surface-400" />
          </div>
          <p class="mt-3 text-surface-500">暂无项目</p>
          <p class="mt-1 text-xs text-surface-400">点击上方「从 GitLab 导入」按钮接入项目</p>
        </div>
      </template>
    </Card>

    <div v-if="showImportModal" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/45 backdrop-blur-[1px]"></div>
      <div class="relative w-full max-w-4xl overflow-hidden rounded-2xl border border-surface-200/60 bg-white shadow-2xl dark:border-surface-700/60 dark:bg-surface-900">
        <div class="flex items-center justify-between border-b border-surface-200/60 px-5 py-4 dark:border-surface-700/60">
          <div>
            <h3 class="text-base font-semibold text-surface-900 dark:text-surface-0">从 GitLab 导入项目</h3>
            <p class="mt-0.5 text-xs text-surface-500 dark:text-surface-400">支持批量导入并自动注册 Webhook</p>
          </div>
          <IconButton size="small" aria-label="关闭" @click="showImportModal = false">
            <X class="h-4 w-4" />
          </IconButton>
        </div>

        <div class="space-y-4 p-5">
          <div class="flex gap-2">
            <label class="block flex-1">
              <IconField class="w-full">
                <InputIcon class="text-surface-400">
                  <Search class="h-4 w-4" />
                </InputIcon>
                <InputText
                  v-model="importSearch"
                  placeholder="搜索 GitLab 项目..."
                  class="w-full"
                  @keydown.enter="handleImportSearch"
                />
              </IconField>
            </label>
            <IconButton size="small" aria-label="刷新列表" @click="fetchGitLabProjects">
              <RefreshCw class="h-4 w-4" />
            </IconButton>
          </div>

          <div class="max-h-[45vh] overflow-auto rounded-xl border border-surface-200/60 dark:border-surface-700/60">
            <table class="w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white dark:bg-surface-900">
                <tr class="border-b border-surface-200/60">
                  <th class="w-10 py-2.5 pr-2 ps-3 text-left">
                    <Checkbox
                      binary
                      :model-value="isAllSelected"
                      :indeterminate="isPartialSelected && !isAllSelected"
                      @change="toggleSelectAll"
                    />
                  </th>
                  <th class="px-2 py-2.5 text-left font-medium text-surface-600">项目名称</th>
                  <th class="px-2 py-2.5 text-left font-medium text-surface-600">命名空间</th>
                  <th class="px-2 py-2.5 text-left font-medium text-surface-600">描述</th>
                  <th class="w-24 px-2 py-2.5 text-left font-medium text-surface-600">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in gitlabProjects"
                  :key="item.id"
                  class="border-b border-surface-100/60 transition hover:bg-surface-50/70 dark:border-surface-700/50 dark:hover:bg-surface-800/70"
                >
                  <td class="py-2 pr-2 ps-3">
                    <Checkbox
                      binary
                      :model-value="selectedIds.has(item.id)"
                      :disabled="item.imported"
                      @change="toggleSelect(item.id)"
                    />
                  </td>
                  <td class="px-2 py-2 font-medium text-surface-900 dark:text-surface-100">{{ item.name }}</td>
                  <td class="px-2 py-2 text-xs text-surface-600">{{ item.namespace }}</td>
                  <td class="max-w-[260px] truncate px-2 py-2 text-xs text-surface-500">{{ item.description || '-' }}</td>
                  <td class="px-2 py-2">
                    <Tag v-if="item.imported" severity="success">已导入</Tag>
                  </td>
                </tr>
                <tr v-if="gitlabProjects.length === 0 && !importLoading">
                  <td colspan="5" class="py-9 text-center text-surface-500">
                    {{ importSearch ? '未找到匹配项目' : '请输入关键词搜索' }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="importLoading" class="flex items-center justify-center gap-2 py-5 text-surface-500">
              <Loader2 class="h-4 w-4 animate-spin" />
              <span>加载中...</span>
            </div>
          </div>

          <div v-if="importTotal > importPerPage" class="flex items-center justify-between">
            <span class="text-xs text-surface-500">共 {{ importTotal }} 个项目</span>
            <div class="flex gap-2">
              <Button text size="small" :disabled="importPage <= 1" @click="importPage--; fetchGitLabProjects()">上一页</Button>
              <Button text size="small" :disabled="importPage * importPerPage >= importTotal" @click="importPage++; fetchGitLabProjects()">下一页</Button>
            </div>
          </div>

          <div class="flex flex-col gap-3 border-t border-surface-200/60 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <label class="inline-flex items-center gap-2 text-surface-700">
              <Checkbox v-model="autoRegisterWebhook" binary />
              自动注册 Webhook
            </label>
            <div class="flex gap-2">
              <Button outlined rounded @click="showImportModal = false">取消</Button>
              <Button
                rounded
                :loading="importing"
                :disabled="selectedIds.size === 0"
                @click="handleImport"
              >
                导入 {{ selectedIds.size }} 个项目
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  FolderKanban,
  CheckCircle2,
  Activity,
  GitPullRequest,
  GitBranch,
  GitCommit,
  Users,
  Clock,
  Eye,
  ExternalLink,
  Download,
  RefreshCw,
  Search,
  Loader2,
  X,
} from 'lucide-vue-next'
import {
  getProjects,
  getAllProjectStats,
  enableProjectReview,
  disableProjectReview,
  searchGitLabProjects,
  importGitLabProjects,
} from '@/api'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import IconButton from '@/components/ui/IconButton.vue'

const router = useRouter()
const searchQuery = ref('')
const loading = ref(false)

const stats = ref({
  totalProjects: 0,
  activeProjects: 0,
  weeklyReviews: 0,
  recentEvents: 0,
})

const projects = ref<any[]>([])

const isReviewEnabled = (value: unknown): boolean => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (!normalized) return false
    if (['true', 'yes', 'on', 'enabled', 'enable', 'active', 'open'].includes(normalized)) return true
    if (['false', 'no', 'off', 'disabled', 'disable', 'inactive', 'close', 'closed'].includes(normalized)) return false
    const numeric = Number(normalized)
    if (!Number.isNaN(numeric)) return numeric !== 0
    return true
  }
  return false
}

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  const query = searchQuery.value.toLowerCase()
  return projects.value.filter((project) =>
    project.project_name?.toLowerCase().includes(query) ||
    project.namespace?.toLowerCase().includes(query) ||
    project.description?.toLowerCase().includes(query)
  )
})

const loadProjects = async () => {
  try {
    loading.value = true
    const response = await getProjects()
    if (response && response.results) {
      projects.value = response.results.map((item: any) => ({
        ...item,
        review_enabled: isReviewEnabled(item.review_enabled),
      }))
    }
  } catch (error) {
    console.error('Failed to load projects:', error)
    toast.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await getAllProjectStats()
    if (response) {
      stats.value = {
        totalProjects: response.total_projects || 0,
        activeProjects: response.enabled_projects || 0,
        weeklyReviews: response.weekly_reviews || 0,
        recentEvents: response.recent_events || 0,
      }
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const toggleProjectReview = async (projectId: number) => {
  try {
    const project = projects.value.find((p) => p.project_id === projectId)
    if (!project) return

    const originalStatus = isReviewEnabled(project.review_enabled)
    project.review_enabled = !originalStatus

    try {
      if (project.review_enabled) {
        await enableProjectReview(projectId.toString())
        toast.success('已启用代码审查')
        stats.value.activeProjects++
      } else {
        await disableProjectReview(projectId.toString())
        toast.success('已禁用代码审查')
        stats.value.activeProjects--
      }
    } catch (apiError) {
      project.review_enabled = originalStatus
      throw apiError
    }
  } catch (error) {
    console.error('Failed to toggle project review:', error)
    toast.error('操作失败，请重试')
  }
}

const viewProjectDetail = (projectId: number) => {
  router.push(`/projects/${projectId}`)
}

const openWebhookUrl = (url: string) => {
  if (url) window.open(url, '_blank')
}

const showImportModal = ref(false)
const importSearch = ref('')
const importLoading = ref(false)
const importing = ref(false)
const gitlabProjects = ref<any[]>([])
const selectedIds = ref<Set<number>>(new Set())
const autoRegisterWebhook = ref(true)
const importPage = ref(1)
const importPerPage = 20
const importTotal = ref(0)

const openImportModal = () => {
  showImportModal.value = true
  importSearch.value = ''
  importPage.value = 1
  selectedIds.value = new Set()
  fetchGitLabProjects()
}

let searchTimer: ReturnType<typeof setTimeout> | null = null

const isAllSelected = computed(() => {
  const selectable = gitlabProjects.value.filter((p) => !p.imported)
  return selectable.length > 0 && selectable.every((p) => selectedIds.value.has(p.id))
})

const isPartialSelected = computed(() => {
  const selectable = gitlabProjects.value.filter((p) => !p.imported)
  const selected = selectable.filter((p) => selectedIds.value.has(p.id))
  return selected.length > 0 && selected.length < selectable.length
})

const toggleSelectAll = () => {
  const selectable = gitlabProjects.value.filter((p) => !p.imported)
  if (isAllSelected.value) {
    selectable.forEach((p) => selectedIds.value.delete(p.id))
  } else {
    selectable.forEach((p) => selectedIds.value.add(p.id))
  }
  selectedIds.value = new Set(selectedIds.value)
}

const toggleSelect = (id: number) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectedIds.value = new Set(selectedIds.value)
}

const fetchGitLabProjects = async () => {
  importLoading.value = true
  try {
    const res = await searchGitLabProjects({
      search: importSearch.value,
      page: importPage.value,
      per_page: importPerPage,
    })
    gitlabProjects.value = res?.results || []
    importTotal.value = res?.count || 0
  } catch (error) {
    console.error('Failed to search GitLab projects:', error)
    toast.error('搜索 GitLab 项目失败')
  } finally {
    importLoading.value = false
  }
}

const handleImportSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    importPage.value = 1
    fetchGitLabProjects()
  }, 300)
}

const handleImport = async () => {
  if (selectedIds.value.size === 0) return
  importing.value = true
  try {
    const res = await importGitLabProjects({
      project_ids: Array.from(selectedIds.value),
      auto_register_webhook: autoRegisterWebhook.value,
    })
    const importedCount = res?.imported?.length || 0
    const failedCount = res?.failed?.length || 0
    const webhookCount = (res?.imported || []).filter((i: any) => i.webhook_registered).length

    let msg = `成功导入 ${importedCount} 个项目`
    if (webhookCount > 0) msg += `，${webhookCount} 个 Webhook 注册成功`
    if (failedCount > 0) msg += `，${failedCount} 个失败`
    toast.success(msg)

    showImportModal.value = false
    selectedIds.value = new Set()
    await Promise.all([loadProjects(), loadStats()])
  } catch (error: any) {
    const detail = error?.response?.data?.detail || '导入失败'
    toast.error(detail)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  Promise.all([loadProjects(), loadStats()])
})
</script>
