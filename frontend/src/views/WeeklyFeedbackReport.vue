<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h2 class="text-2xl font-bold tracking-tight text-surface-900 dark:text-surface-0">周总结看板</h2>
        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">
          团队策略沉淀 + 成员 AI 总结，用于查漏补缺，不做个人排名
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <SelectButton
          v-model="viewMode"
          :options="viewModeOptions"
          option-label="label"
          option-value="value"
          size="small"
        />

        <input
          v-model="anchorDate"
          type="date"
          class="h-9 rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
        >

        <Select
          v-if="viewMode === 'team'"
          v-model="selectedProjectId"
          :options="projectFilterOptions"
          option-label="label"
          option-value="value"
          class="w-[220px]"
          placeholder="项目筛选（可选）"
        />

        <Button label="刷新" size="small" :loading="loading" @click="loadReport" />
      </div>
    </div>

    <div v-if="viewMode === 'team'" class="space-y-6">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">问题总数</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ teamReport.summary.total_issues }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略总数</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ teamReport.summary.ignored_count }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">恢复跟踪</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ teamReport.summary.reopened_count }}</div>
          </template>
        </Card>
        <Card>
          <template #content>
            <div class="text-xs uppercase tracking-wide text-surface-500">忽略率</div>
            <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ teamIgnoreRatePercent }}%</div>
            <div class="mt-1 text-xs text-surface-500">统计周期 {{ teamReport.week_start }} ~ {{ teamReport.week_end }}</div>
          </template>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <template #title>
            <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">高频忽略规则 TOP</div>
          </template>
          <template #content>
            <div v-if="teamReport.top_ignored_rules.length" class="space-y-3">
              <div
                v-for="item in teamReport.top_ignored_rules"
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
                v-for="item in teamReport.ignore_reason_distribution"
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
              v-for="(item, index) in teamReport.suggested_policy_changes"
              :key="`team-suggestion-${index}`"
              class="rounded-lg border border-primary-200/70 bg-primary-50 px-3 py-2 text-sm text-primary-800 dark:border-primary-500/30 dark:bg-primary-500/10 dark:text-primary-200"
            >
              {{ item }}
            </li>
          </ul>
        </template>
      </Card>

      <div class="space-y-4">
        <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">项目差异</h3>
        <div v-if="teamReport.projects.length" class="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Card v-for="project in teamReport.projects" :key="project.project_id">
            <template #title>
              <div class="flex items-center justify-between gap-3">
                <div class="truncate text-sm font-semibold text-surface-800 dark:text-surface-100">
                  {{ project.project_name }}
                </div>
                <Tag severity="info">ID {{ project.project_id }}</Tag>
              </div>
            </template>
            <template #content>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div class="rounded-lg bg-surface-50 p-3 dark:bg-surface-900">
                  <div class="text-surface-500">问题总数</div>
                  <div class="mt-1 text-lg font-semibold text-surface-900 dark:text-surface-100">{{ project.total_issues }}</div>
                </div>
                <div class="rounded-lg bg-surface-50 p-3 dark:bg-surface-900">
                  <div class="text-surface-500">忽略 / 恢复</div>
                  <div class="mt-1 text-lg font-semibold text-surface-900 dark:text-surface-100">
                    {{ project.ignored_count }} / {{ project.reopened_count }}
                  </div>
                </div>
              </div>

              <div class="mt-4 space-y-2">
                <div class="text-xs uppercase tracking-wide text-surface-500">项目建议</div>
                <ul class="space-y-2">
                  <li
                    v-for="(item, index) in project.suggested_policy_changes"
                    :key="`project-${project.project_id}-suggestion-${index}`"
                    class="rounded-md border border-surface-200/70 bg-surface-50 px-3 py-2 text-sm text-surface-700 dark:border-surface-700/70 dark:bg-surface-900 dark:text-surface-200"
                  >
                    {{ item }}
                  </li>
                </ul>
              </div>
            </template>
          </Card>
        </div>
        <Card v-else>
          <template #content>
            <div class="py-8 text-center text-sm text-surface-500">当前周期没有可展示的项目回收数据</div>
          </template>
        </Card>
      </div>
    </div>

    <div v-else class="space-y-6">
      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">成员周总结卡片</div>
        </template>
        <template #content>
          <div v-if="memberCards.length" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <button
              v-for="card in memberCards"
              :key="card.owner"
              type="button"
              class="rounded-xl border px-4 py-3 text-left transition-all"
              :class="selectedOwner === card.owner
                ? 'border-primary-400 bg-primary-50 shadow-sm dark:border-primary-400/60 dark:bg-primary-500/10'
                : 'border-surface-200 bg-surface-0 hover:border-primary-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:hover:border-primary-500/40'"
              @click="handleSelectMember(card.owner)"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="truncate text-sm font-semibold text-surface-900 dark:text-surface-0">{{ card.owner }}</div>
                <Tag severity="secondary">{{ card.total_findings }} 条</Tag>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-surface-500">
                <span>MR {{ card.total_reviews }}</span>
                <span>类型 {{ card.top_category }}</span>
                <span>严重度 {{ card.top_severity }}</span>
              </div>
              <p class="mt-2 line-clamp-2 text-xs text-surface-600 dark:text-surface-300">{{ card.summary_excerpt }}</p>
              <p class="mt-2 line-clamp-1 text-xs text-primary-700 dark:text-primary-300">{{ card.improvement_focus }}</p>
            </button>
          </div>
          <div v-else class="py-8 text-center text-sm text-surface-500">当前周期暂无成员周总结卡片</div>
        </template>
      </Card>

      <Card v-if="selectedOwner">
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">
            {{ selectedOwner }} 的详细周总结
          </div>
        </template>
        <template #content>
          <div class="space-y-6">
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div class="rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900">
                <div class="text-xs uppercase tracking-wide text-surface-500">问题总数</div>
                <div class="mt-1 text-2xl font-bold text-surface-900 dark:text-surface-0">{{ memberReport.summary.total_findings }}</div>
              </div>
              <div class="rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900">
                <div class="text-xs uppercase tracking-wide text-surface-500">关联 MR</div>
                <div class="mt-1 text-2xl font-bold text-surface-900 dark:text-surface-0">{{ memberReport.summary.total_reviews }}</div>
              </div>
              <div class="rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900">
                <div class="text-xs uppercase tracking-wide text-surface-500">忽略 / 恢复</div>
                <div class="mt-1 text-2xl font-bold text-surface-900 dark:text-surface-0">
                  {{ memberReport.summary.ignore_actions }} / {{ memberReport.summary.reopen_actions }}
                </div>
              </div>
              <div class="rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900">
                <div class="text-xs uppercase tracking-wide text-surface-500">忽略率</div>
                <div class="mt-1 text-2xl font-bold text-surface-900 dark:text-surface-0">{{ memberIgnoreRatePercent }}%</div>
              </div>
            </div>

            <div class="rounded-lg border border-primary-200/70 bg-primary-50 px-4 py-3 text-sm leading-6 text-primary-900 dark:border-primary-500/30 dark:bg-primary-500/10 dark:text-primary-100">
              {{ memberReport.ai_summary || '本周暂无可生成的成员总结。' }}
            </div>

            <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div>
                <div class="mb-2 text-xs uppercase tracking-wide text-surface-500">问题类型分布</div>
                <div class="space-y-2">
                  <div
                    v-for="item in memberReport.by_category"
                    :key="`member-category-${item.name}`"
                    class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
                  >
                    <span class="text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                    <Tag severity="secondary">{{ item.value }} 次</Tag>
                  </div>
                  <div v-if="memberReport.by_category.length === 0" class="py-4 text-sm text-surface-500">暂无类型数据</div>
                </div>
              </div>

              <div>
                <div class="mb-2 text-xs uppercase tracking-wide text-surface-500">改进方向</div>
                <ul class="space-y-2">
                  <li
                    v-for="(item, index) in memberReport.gap_checklist"
                    :key="`member-gap-${index}`"
                    class="rounded-md border border-surface-200/70 bg-surface-50 px-3 py-2 text-sm text-surface-700 dark:border-surface-700/70 dark:bg-surface-900 dark:text-surface-200"
                  >
                    {{ item }}
                  </li>
                </ul>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div>
                <div class="mb-2 text-xs uppercase tracking-wide text-surface-500">高频文件</div>
                <div class="space-y-2">
                  <div
                    v-for="item in memberReport.top_files"
                    :key="`member-file-${item.name}`"
                    class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
                  >
                    <span class="truncate text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                    <Tag severity="info">{{ item.value }} 次</Tag>
                  </div>
                  <div v-if="memberReport.top_files.length === 0" class="py-4 text-sm text-surface-500">暂无文件数据</div>
                </div>
              </div>

              <div>
                <div class="mb-2 text-xs uppercase tracking-wide text-surface-500">项目分布</div>
                <div class="space-y-2">
                  <div
                    v-for="item in memberReport.projects"
                    :key="`member-project-${item.name}`"
                    class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
                  >
                    <span class="truncate text-sm text-surface-700 dark:text-surface-200">{{ item.name }}</span>
                    <Tag severity="help">{{ item.value }} 条</Tag>
                  </div>
                  <div v-if="memberReport.projects.length === 0" class="py-4 text-sm text-surface-500">暂无项目数据</div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card v-else>
        <template #content>
          <div class="py-8 text-center text-sm text-surface-500">请先从成员卡片中选择一位查看详细周总结</div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getDeveloperWeeklyCards, getDeveloperWeeklyReport, getMRFeedbackWeeklyReport } from '@/api'
import { useRoute } from 'vue-router'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'

interface RuleBucket {
  rule_key: string
  ignore_count: number
}

interface ReasonBucket {
  reason_type: string
  count: number
  ratio: number
}

interface TeamSummary {
  total_issues: number
  ignored_count: number
  reopened_count: number
  ignore_rate: number
  feedback_actions: number
}

interface ProjectSummary {
  project_id: number
  project_name: string
  total_issues: number
  ignored_count: number
  reopened_count: number
  ignore_rate: number
  top_ignored_rules: RuleBucket[]
  ignore_reason_distribution: ReasonBucket[]
  suggested_policy_changes: string[]
}

interface TeamWeeklyReport {
  week_start: string
  week_end: string
  summary: TeamSummary
  top_ignored_rules: RuleBucket[]
  ignore_reason_distribution: ReasonBucket[]
  suggested_policy_changes: string[]
  projects: ProjectSummary[]
  generated_at: string
}

interface StatsBucket {
  name: string
  value: number
}

interface MemberSummary {
  total_findings: number
  total_reviews: number
  ignore_actions: number
  reopen_actions: number
  ignore_rate: number
}

interface MemberWeeklyReport {
  week_start: string
  week_end: string
  owner: string | null
  owner_email: string | null
  available_owners: string[]
  summary: MemberSummary
  by_category: StatsBucket[]
  by_severity: StatsBucket[]
  top_files: StatsBucket[]
  projects: StatsBucket[]
  ai_summary: string
  gap_checklist: string[]
  generated_at: string
}

interface MemberCard {
  owner: string
  owner_email: string | null
  total_findings: number
  total_reviews: number
  ignore_actions: number
  reopen_actions: number
  ignore_rate: number
  top_category: string
  top_severity: string
  summary_excerpt: string
  improvement_focus: string
}

interface MemberCardResponse {
  week_start: string
  week_end: string
  count: number
  results: MemberCard[]
  generated_at: string
}

type ViewMode = 'team' | 'member'

const route = useRoute()
const loading = ref(false)
const defaultViewMode = route.query.view === 'team' ? 'team' : 'member'
const viewMode = ref<ViewMode>(defaultViewMode)
const viewModeOptions = [
  { label: '团队总结', value: 'team' },
  { label: '成员总结', value: 'member' }
]

const selectedProjectId = ref<number | null>(null)
const selectedOwner = ref('')
const memberCards = ref<MemberCard[]>([])

const toInputDate = (value: Date): string => {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const anchorDate = ref(toInputDate(new Date()))

const teamReport = ref<TeamWeeklyReport>({
  week_start: '',
  week_end: '',
  summary: {
    total_issues: 0,
    ignored_count: 0,
    reopened_count: 0,
    ignore_rate: 0,
    feedback_actions: 0
  },
  top_ignored_rules: [],
  ignore_reason_distribution: [],
  suggested_policy_changes: [],
  projects: [],
  generated_at: ''
})

const memberReport = ref<MemberWeeklyReport>({
  week_start: '',
  week_end: '',
  owner: null,
  owner_email: null,
  available_owners: [],
  summary: {
    total_findings: 0,
    total_reviews: 0,
    ignore_actions: 0,
    reopen_actions: 0,
    ignore_rate: 0
  },
  by_category: [],
  by_severity: [],
  top_files: [],
  projects: [],
  ai_summary: '',
  gap_checklist: [],
  generated_at: ''
})

const projectFilterOptions = computed(() => {
  const options = teamReport.value.projects.map((item) => ({
    label: item.project_name,
    value: item.project_id
  }))
  return [{ label: '全部项目', value: null }, ...options]
})

const teamIgnoreRatePercent = computed(() => Math.round((teamReport.value.summary.ignore_rate || 0) * 100))
const memberIgnoreRatePercent = computed(() => Math.round((memberReport.value.summary.ignore_rate || 0) * 100))

const normalizeTeamReport = (data: Partial<TeamWeeklyReport> | undefined): TeamWeeklyReport => {
  const summary: Partial<TeamSummary> = data?.summary ?? {}
  return {
    week_start: data?.week_start ?? '',
    week_end: data?.week_end ?? '',
    summary: {
      total_issues: Number(summary.total_issues ?? 0),
      ignored_count: Number(summary.ignored_count ?? 0),
      reopened_count: Number(summary.reopened_count ?? 0),
      ignore_rate: Number(summary.ignore_rate ?? 0),
      feedback_actions: Number(summary.feedback_actions ?? 0)
    },
    top_ignored_rules: Array.isArray(data?.top_ignored_rules) ? data.top_ignored_rules : [],
    ignore_reason_distribution: Array.isArray(data?.ignore_reason_distribution) ? data.ignore_reason_distribution : [],
    suggested_policy_changes: Array.isArray(data?.suggested_policy_changes) ? data.suggested_policy_changes : [],
    projects: Array.isArray(data?.projects) ? data.projects : [],
    generated_at: data?.generated_at ?? ''
  }
}

const normalizeMemberReport = (data: Partial<MemberWeeklyReport> | undefined): MemberWeeklyReport => {
  const summary: Partial<MemberSummary> = data?.summary ?? {}
  return {
    week_start: data?.week_start ?? '',
    week_end: data?.week_end ?? '',
    owner: data?.owner ?? null,
    owner_email: data?.owner_email ?? null,
    available_owners: Array.isArray(data?.available_owners) ? data.available_owners : [],
    summary: {
      total_findings: Number(summary.total_findings ?? 0),
      total_reviews: Number(summary.total_reviews ?? 0),
      ignore_actions: Number(summary.ignore_actions ?? 0),
      reopen_actions: Number(summary.reopen_actions ?? 0),
      ignore_rate: Number(summary.ignore_rate ?? 0)
    },
    by_category: Array.isArray(data?.by_category) ? data.by_category : [],
    by_severity: Array.isArray(data?.by_severity) ? data.by_severity : [],
    top_files: Array.isArray(data?.top_files) ? data.top_files : [],
    projects: Array.isArray(data?.projects) ? data.projects : [],
    ai_summary: data?.ai_summary ?? '',
    gap_checklist: Array.isArray(data?.gap_checklist) ? data.gap_checklist : [],
    generated_at: data?.generated_at ?? ''
  }
}

const loadTeamReport = async () => {
  const response = await getMRFeedbackWeeklyReport({
    project_id: selectedProjectId.value ?? undefined,
    anchor_date: anchorDate.value || undefined
  })
  teamReport.value = normalizeTeamReport(response)
}

const loadMemberCards = async () => {
  const response = await getDeveloperWeeklyCards({
    anchor_date: anchorDate.value || undefined,
    limit: 100
  }) as MemberCardResponse

  memberCards.value = Array.isArray(response?.results) ? response.results : []

  const queryOwner = typeof route.query.owner === 'string' ? route.query.owner.trim() : ''
  if (!selectedOwner.value && queryOwner) {
    selectedOwner.value = queryOwner
  }
  if (!selectedOwner.value && memberCards.value.length > 0) {
    selectedOwner.value = memberCards.value[0].owner
  }
  if (selectedOwner.value && !memberCards.value.some((item) => item.owner === selectedOwner.value)) {
    selectedOwner.value = memberCards.value[0]?.owner || ''
  }
}

const loadMemberDetail = async (owner: string) => {
  if (!owner) {
    memberReport.value = normalizeMemberReport(undefined)
    return
  }
  const response = await getDeveloperWeeklyReport({
    owner,
    anchor_date: anchorDate.value || undefined
  })
  memberReport.value = normalizeMemberReport(response)
}

const loadReport = async () => {
  loading.value = true
  try {
    await Promise.all([loadTeamReport(), loadMemberCards()])
    await loadMemberDetail(selectedOwner.value)
  } catch (error) {
    console.error('加载周总结失败:', error)
    toast.error('加载周总结失败')
  } finally {
    loading.value = false
  }
}

const handleSelectMember = async (owner: string) => {
  if (!owner || owner === selectedOwner.value) return
  selectedOwner.value = owner
  loading.value = true
  try {
    await loadMemberDetail(owner)
  } catch (error) {
    console.error('加载成员周总结详情失败:', error)
    toast.error('加载成员周总结详情失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReport()
})
</script>
