<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 class="text-xl font-semibold text-surface-900 dark:text-surface-0">审查记录</h2>
          <label class="relative block w-full sm:w-80">
            <Search class="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
            <InputText
              v-model="searchText"
              placeholder="搜索 MR ID 或项目名"
              class="ps-9 pe-3"
              @keydown.enter="handleSearch"
            />
          </label>
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="relative overflow-x-auto">
          <table class="w-full min-w-[920px] text-sm text-surface-800 dark:text-surface-100">
            <thead>
              <tr class="border-b border-surface-200/70 text-left text-xs font-semibold uppercase tracking-wide text-surface-600 dark:border-surface-600/70 dark:bg-surface-800/40 dark:text-surface-200">
                <th class="px-3 py-3">ID</th>
                <th class="px-3 py-3">MR</th>
                <th class="px-3 py-3">项目</th>
                <th class="px-3 py-3">标题</th>
                <th class="px-3 py-3">作者</th>
                <th class="px-3 py-3">状态</th>
                <th class="px-3 py-3">时间</th>
                <th class="px-3 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in filteredReviews"
                :key="record.id"
                class="border-b border-surface-100/80 transition hover:bg-surface-50/70 dark:border-surface-700/70 dark:hover:bg-surface-700/55"
              >
                <td class="px-3 py-3 text-surface-700 dark:text-surface-200">{{ record.id }}</td>
                <td class="px-3 py-3">
                  <Tag severity="info">
                    <span class="inline-flex items-center gap-1.5">
                      <span>!{{ record.merge_request_iid }}</span>
                      <button
                        type="button"
                        class="inline-flex h-4 w-4 items-center justify-center rounded-sm opacity-80 transition hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-40"
                        :disabled="!canOpenMr(record)"
                        aria-label="新窗口打开MR"
                        @click.stop="openMrInNewTab(record)"
                      >
                        <ExternalLink class="h-3.5 w-3.5" />
                      </button>
                    </span>
                  </Tag>
                </td>
                <td class="px-3 py-3 text-surface-800 dark:text-surface-100">{{ record.project_name }}</td>
                <td class="max-w-[320px] px-3 py-3">
                  <span class="block truncate text-surface-800 dark:text-surface-100">{{ record.merge_request_title }}</span>
                </td>
                <td class="px-3 py-3 text-surface-700 dark:text-surface-200">{{ record.author_name }}</td>
                <td class="px-3 py-3">
                  <Tag :severity="statusSeverity(record.status)">{{ statusLabel(record.status) }}</Tag>
                </td>
                <td class="px-3 py-3 text-surface-600 dark:text-surface-300">{{ formatReviewTime(record.created_at) }}</td>
                <td class="px-3 py-3 text-right">
                  <Button size="small" @click="goToDetail(record.id)">查看详情</Button>
                </td>
              </tr>
              <tr v-if="!loading && filteredReviews.length === 0">
                <td colspan="8" class="px-3 py-10 text-center text-surface-500 dark:text-surface-400">暂无审查记录</td>
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
          <span class="text-xs text-surface-500 dark:text-surface-400">共 {{ totalReviews }} 条记录</span>
          <div class="flex items-center gap-2">
            <Button text size="small" :disabled="currentPage <= 1 || loading" @click="handlePageChange(currentPage - 1)">上一页</Button>
            <span class="text-xs text-surface-600 dark:text-surface-300">第 {{ currentPage }} / {{ totalPages }} 页</span>
            <Button text size="small" :disabled="currentPage >= totalPages || loading" @click="handlePageChange(currentPage + 1)">下一页</Button>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Loader2, ExternalLink } from 'lucide-vue-next'
import { getProjectDetail, getReviews } from '@/api/index'
import { formatBackendDateTime } from '@/utils/datetime'
import { getReviewStatusMeta } from '@/utils/reviewStatus'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

const router = useRouter()
const searchText = ref('')
const loading = ref(false)
const totalReviews = ref(0)
const reviewsList = ref<any[]>([])
const projectUrlCache = ref<Record<number, string>>({})

const currentPage = ref(1)
const pageSize = ref(20)

const filteredReviews = computed(() => reviewsList.value)

const totalPages = computed(() => {
  const total = Math.ceil(totalReviews.value / pageSize.value)
  return Math.max(total, 1)
})

const fetchReviews = async () => {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const params = {
      limit: pageSize.value,
      offset,
      search: searchText.value || undefined,
    }

    const response = await getReviews(params)
    if (response && response.results) {
      reviewsList.value = response.results
      totalReviews.value = response.total || response.count || 0
    }
  } catch (error) {
    console.error('获取审核记录失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchReviews()
}

onMounted(() => {
  fetchReviews()
})

const statusLabel = (status: string): string => {
  return getReviewStatusMeta(status).label
}

const statusSeverity = (status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' => {
  return getReviewStatusMeta(status).severity
}

const handleSearch = () => {
  currentPage.value = 1
  fetchReviews()
}

const goToDetail = (id: number) => {
  router.push(`/reviews/${id}`)
}

const formatReviewTime = (value: string | null | undefined): string => {
  return formatBackendDateTime(value)
}

const canOpenMr = (record: any): boolean => {
  return Boolean(record?.merge_request_url || (record?.project_id && record?.merge_request_iid != null))
}

const buildMergeRequestUrl = (projectUrl: string, mrIid: number | null | undefined): string => {
  if (!projectUrl || mrIid == null) return ''
  const trimmed = projectUrl.trim()
  if (!trimmed) return ''
  const base = trimmed.replace(/\.git$/i, '').replace(/\/+$/, '')
  return `${base}/-/merge_requests/${mrIid}`
}

const resolveMrUrl = async (record: any): Promise<string> => {
  if (record?.merge_request_url) return String(record.merge_request_url)
  const projectId = Number(record?.project_id)
  if (!projectId || record?.merge_request_iid == null) return ''

  if (!projectUrlCache.value[projectId]) {
    try {
      const detail = await getProjectDetail(String(projectId))
      projectUrlCache.value[projectId] = String(detail?.project_url || '')
    } catch (error) {
      console.error('获取项目详情失败，无法构建 MR 链接:', error)
      return ''
    }
  }

  return buildMergeRequestUrl(projectUrlCache.value[projectId], record.merge_request_iid)
}

const openMrInNewTab = async (record: any) => {
  const url = await resolveMrUrl(record)
  if (!url) {
    toast.warning('未能获取 MR 地址')
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>
