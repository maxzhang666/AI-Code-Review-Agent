<template>
  <PublicReportShell
    :title="`${ownerLabel} 的周总结`"
    description="查看该成员一周问题分布、AI 总结和改进方向。"
  >
    <template #actions>
      <input
        v-model="anchorDate"
        type="date"
        class="h-9 rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
        @change="loadDetail"
      >
      <Button label="刷新" size="small" :loading="loading" @click="loadDetail" />
      <Button label="返回列表" severity="secondary" size="small" @click="goBackToList" />
    </template>

    <div class="space-y-6">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">纳入总结问题</div>
            <div class="mt-2 text-3xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.total_findings }}</div>
            <div v-if="report.summary.excluded_findings > 0" class="mt-1 text-xs text-amber-600 dark:text-amber-300">
              原始 {{ report.summary.raw_total_findings }} 条，排除 {{ report.summary.excluded_findings }} 条 ignored
            </div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">关联 MR</div>
            <div class="mt-2 text-3xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.total_reviews }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略 / 恢复</div>
            <div class="mt-2 text-3xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.ignore_actions }} / {{ report.summary.reopen_actions }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略率</div>
            <div class="mt-2 text-3xl font-bold text-surface-900 dark:text-surface-0">{{ ignoreRatePercent }}%</div>
            <div class="mt-1 text-xs text-surface-500">{{ report.week_start }} ~ {{ report.week_end }}</div>
            <div class="mt-1 text-xs text-surface-500">状态口径：{{ summaryStatusScope }}</div>
          </template>
        </Card>
      </div>

      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">AI 一周总结</div>
        </template>
        <template #content>
          <div class="rounded-lg border border-primary-200/70 bg-primary-50 px-4 py-3 text-sm leading-6 text-primary-900 dark:border-primary-500/30 dark:bg-primary-500/10 dark:text-primary-100">
            {{ report.ai_summary || '本周暂无可生成的成员总结。' }}
          </div>
        </template>
      </Card>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">问题类型分布</div>
          </template>
          <template #content>
            <div class="space-y-2">
              <div
                v-for="item in report.by_category"
                :key="`category-${item.name}`"
                class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
              >
                <span class="text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                <Tag severity="secondary">{{ item.value }} 次</Tag>
              </div>
              <div v-if="report.by_category.length === 0" class="py-4 text-sm text-surface-500">暂无类型数据</div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">改进方向</div>
          </template>
          <template #content>
            <ul class="space-y-2">
              <li
                v-for="(item, index) in report.gap_checklist"
                :key="`gap-${index}`"
                class="rounded-md border border-surface-200/70 bg-surface-50 px-3 py-2 text-sm text-surface-700 dark:border-surface-700/70 dark:bg-surface-900 dark:text-surface-200"
              >
                {{ item }}
              </li>
            </ul>
          </template>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">高频文件</div>
          </template>
          <template #content>
            <div class="space-y-2">
              <div
                v-for="item in report.top_files"
                :key="`file-${item.name}`"
                class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
              >
                <span class="truncate text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                <Tag severity="info">{{ item.value }} 次</Tag>
              </div>
              <div v-if="report.top_files.length === 0" class="py-4 text-sm text-surface-500">暂无文件数据</div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">项目分布</div>
          </template>
          <template #content>
            <div class="space-y-2">
              <div
                v-for="item in report.projects"
                :key="`project-${item.name}`"
                class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
              >
                <span class="truncate text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                <Tag severity="help">{{ item.value }} 条</Tag>
              </div>
              <div v-if="report.projects.length === 0" class="py-4 text-sm text-surface-500">暂无项目数据</div>
            </div>
          </template>
        </Card>
      </div>
    </div>
  </PublicReportShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDeveloperWeeklyReport } from '@/api'
import PublicReportShell from '@/components/reports/PublicReportShell.vue'
import { EMPTY_MEMBER_REPORT, normalizeMemberReport, toInputDate, type MemberWeeklyReport } from '@/types/weekly-report'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const report = ref<MemberWeeklyReport>(EMPTY_MEMBER_REPORT)
const anchorDate = ref(toInputDate(new Date()))

const ownerLabel = computed(() => {
  const owner = route.params.owner
  return typeof owner === 'string' && owner.trim() ? owner.trim() : '成员'
})

const ignoreRatePercent = computed(() => Math.round((report.value.summary.ignore_rate || 0) * 100))
const summaryStatusScope = computed(() => {
  const statuses = Array.isArray(report.value.include_statuses) ? report.value.include_statuses : []
  return statuses.length ? statuses.join(' / ') : 'open / reopened'
})

const loadDetail = async () => {
  const owner = ownerLabel.value
  if (!owner || owner === '成员') return

  loading.value = true
  try {
    const response = await getDeveloperWeeklyReport({
      owner,
      anchor_date: anchorDate.value || undefined
    })
    report.value = normalizeMemberReport(response)
  } catch (error) {
    console.error('加载成员周报详情失败:', error)
    toast.error('加载成员周报详情失败')
  } finally {
    loading.value = false
  }
}

const goBackToList = async () => {
  await router.push({
    name: 'PublicWeeklyReportMembers',
    query: { anchor_date: anchorDate.value }
  })
}

onMounted(() => {
  if (typeof route.query.anchor_date === 'string' && route.query.anchor_date.trim()) {
    anchorDate.value = route.query.anchor_date.trim()
  }
  loadDetail()
})
</script>
