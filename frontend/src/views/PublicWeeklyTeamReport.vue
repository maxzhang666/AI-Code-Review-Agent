<template>
  <PublicReportShell
    title="团队周报"
    description="汇总团队一周的回收动作、忽略原因和项目策略建议，用于下周规则迭代。"
  >
    <template #actions>
      <input
        v-model="anchorDate"
        type="date"
        class="h-9 rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
      >
      <Select
        v-model="selectedProjectId"
        :options="projectFilterOptions"
        option-label="label"
        option-value="value"
        class="w-[220px]"
        placeholder="项目筛选（可选）"
      />
      <Button label="刷新" size="small" :loading="loading" @click="loadReport" />
    </template>

    <div class="space-y-6">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">问题总数</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.total_issues }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略总数</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.ignored_count }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">恢复跟踪</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ report.summary.reopened_count }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略率</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ ignoreRatePercent }}%</div>
            <div class="mt-1 text-xs text-surface-500">{{ report.week_start }} ~ {{ report.week_end }}</div>
          </template>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">高频忽略规则 TOP</div>
          </template>
          <template #content>
            <div v-if="report.top_ignored_rules.length" class="space-y-3">
              <div
                v-for="item in report.top_ignored_rules"
                :key="item.rule_key"
                class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
              >
                <span class="truncate text-sm text-surface-700 dark:text-surface-200">{{ item.rule_key }}</span>
                <Tag severity="warn">{{ item.ignore_count }} 次</Tag>
              </div>
            </div>
            <div v-else class="py-6 text-center text-sm text-surface-500">本周暂无忽略记录</div>
          </template>
        </Card>

        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">忽略原因分布</div>
          </template>
          <template #content>
            <div class="space-y-3">
              <div
                v-for="item in report.ignore_reason_distribution"
                :key="item.reason_type"
                class="space-y-1"
              >
                <div class="flex items-center justify-between text-sm">
                  <span class="text-surface-700 dark:text-surface-200">{{ item.reason_type }}</span>
                  <span class="text-surface-500">{{ item.count }} 次</span>
                </div>
                <ProgressBar :value="Math.round(item.ratio * 100)" :show-value="false" style="height: 8px" />
              </div>
            </div>
          </template>
        </Card>
      </div>

      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">团队策略建议</div>
        </template>
        <template #content>
          <ul class="space-y-2">
            <li
              v-for="(item, index) in report.suggested_policy_changes"
              :key="`team-suggestion-${index}`"
              class="rounded-lg border border-primary-200/70 bg-primary-50 px-3 py-2 text-sm text-primary-800 dark:border-primary-500/30 dark:bg-primary-500/10 dark:text-primary-200"
            >
              {{ item }}
            </li>
          </ul>
        </template>
      </Card>

      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">项目差异</div>
        </template>
        <template #content>
          <div v-if="report.projects.length" class="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div
              v-for="project in report.projects"
              :key="project.project_id"
              class="rounded-xl border border-surface-200/70 bg-surface-50 p-4 dark:border-surface-700/70 dark:bg-surface-900"
            >
              <div class="flex items-center justify-between">
                <div class="truncate text-sm font-semibold text-surface-900 dark:text-surface-0">{{ project.project_name }}</div>
                <Tag severity="info">ID {{ project.project_id }}</Tag>
              </div>
              <div class="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div class="text-surface-500">问题总数</div>
                  <div class="mt-1 text-lg font-semibold text-surface-900 dark:text-surface-100">{{ project.total_issues }}</div>
                </div>
                <div>
                  <div class="text-surface-500">忽略 / 恢复</div>
                  <div class="mt-1 text-lg font-semibold text-surface-900 dark:text-surface-100">{{ project.ignored_count }} / {{ project.reopened_count }}</div>
                </div>
              </div>
              <ul class="mt-3 space-y-2">
                <li
                  v-for="(item, index) in project.suggested_policy_changes"
                  :key="`project-${project.project_id}-${index}`"
                  class="rounded-md border border-surface-200/70 bg-surface-0 px-3 py-2 text-sm text-surface-700 dark:border-surface-700/70 dark:bg-surface-950 dark:text-surface-200"
                >
                  {{ item }}
                </li>
              </ul>
            </div>
          </div>
          <div v-else class="py-8 text-center text-sm text-surface-500">当前周期没有可展示的项目回收数据</div>
        </template>
      </Card>
    </div>
  </PublicReportShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getMRFeedbackWeeklyReport } from '@/api'
import PublicReportShell from '@/components/reports/PublicReportShell.vue'
import {
  EMPTY_TEAM_REPORT,
  normalizeTeamReport,
  toInputDate,
  type TeamWeeklyReport,
} from '@/types/weekly-report'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const loading = ref(false)
const selectedProjectId = ref<number | null>(null)
const anchorDate = ref(toInputDate(new Date()))
const report = ref<TeamWeeklyReport>(EMPTY_TEAM_REPORT)

const projectFilterOptions = computed(() => {
  const options = report.value.projects.map((item) => ({
    label: item.project_name,
    value: item.project_id
  }))
  return [{ label: '全部项目', value: null }, ...options]
})

const ignoreRatePercent = computed(() => Math.round((report.value.summary.ignore_rate || 0) * 100))

const loadReport = async () => {
  loading.value = true
  try {
    const response = await getMRFeedbackWeeklyReport({
      project_id: selectedProjectId.value ?? undefined,
      anchor_date: anchorDate.value || undefined
    })
    report.value = normalizeTeamReport(response)
  } catch (error) {
    console.error('加载团队周报失败:', error)
    toast.error('加载团队周报失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReport()
})
</script>

