<template>
  <PublicReportShell
    title="成员周报"
    description="按成员查看一周问题概况与 AI 提炼摘要，点击卡片进入详细总结。"
  >
    <template #actions>
      <input
        v-model="anchorDate"
        type="date"
        class="h-9 rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
      >
      <Button label="刷新" size="small" :loading="loading" @click="loadCards" />
    </template>

    <Card>
      <template #title>
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">成员卡片列表</div>
          <div class="text-xs text-surface-500">共 {{ filteredCards.length }} 位成员</div>
        </div>
      </template>
      <template #content>
        <div class="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索成员名"
            class="h-10 rounded-lg border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
          >

          <SelectButton
            v-model="severityFilter"
            :options="severityOptions"
            option-label="label"
            option-value="value"
            size="small"
          />

          <Select
            v-model="categoryFilter"
            :options="categoryOptions"
            option-label="label"
            option-value="value"
            placeholder="按问题类型筛选"
          />
        </div>

        <div v-if="filteredCards.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <button
            v-for="card in filteredCards"
            :key="card.owner"
            type="button"
            class="group rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-lg"
            :class="cardToneClass(card)"
            @click="goToDetail(card.owner)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-2.5">
                <div
                  class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-semibold"
                  :class="avatarToneClass(card)"
                >
                  {{ avatarText(card.owner) }}
                </div>
                  <div class="min-w-0">
                  <div class="truncate text-sm font-semibold text-surface-900 dark:text-surface-0">{{ card.owner }}</div>
                  <div class="mt-1 text-xs text-surface-500">{{ card.total_reviews }} 个 MR · 纳入总结 {{ card.total_findings }} 条</div>
                  <div v-if="card.excluded_findings > 0" class="mt-1 text-xs text-amber-600 dark:text-amber-300">
                    已排除 {{ card.excluded_findings }} 条 ignored 问题
                  </div>
                </div>
              </div>
              <Tag :severity="severityTag(card.top_severity)">{{ severityLabel(card.top_severity) }}</Tag>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-2 text-xs">
              <span class="rounded-md bg-surface-100 px-2 py-1 text-surface-700 dark:bg-surface-800 dark:text-surface-200">类型 {{ card.top_category }}</span>
              <span class="rounded-md bg-surface-100 px-2 py-1 text-surface-700 dark:bg-surface-800 dark:text-surface-200">忽略率 {{ Math.round((card.ignore_rate || 0) * 100) }}%</span>
              <span class="rounded-md bg-surface-100 px-2 py-1 text-surface-700 dark:bg-surface-800 dark:text-surface-200">回收 {{ card.ignore_actions }}/{{ card.reopen_actions }}</span>
            </div>

            <p class="mt-3 text-sm leading-6 text-surface-700 dark:text-surface-200">
              {{ card.summary_excerpt }}
            </p>
            <div class="mt-3 rounded-lg border border-primary-200/70 bg-primary-50 px-2.5 py-2 text-xs text-primary-800 dark:border-primary-500/30 dark:bg-primary-500/10 dark:text-primary-100">
              {{ card.improvement_focus }}
            </div>
            <div class="mt-3 text-xs font-medium text-primary-600 group-hover:text-primary-700 dark:text-primary-300">
              查看完整周总结 →
            </div>
          </button>
        </div>
        <div v-else class="py-10 text-center text-sm text-surface-500">当前筛选条件下暂无成员周报数据</div>
      </template>
    </Card>
  </PublicReportShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDeveloperWeeklyCards } from '@/api'
import PublicReportShell from '@/components/reports/PublicReportShell.vue'
import { toInputDate, type MemberCard, type MemberCardResponse } from '@/types/weekly-report'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'

type SeverityFilter = 'all' | 'high' | 'medium' | 'low'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const anchorDate = ref(toInputDate(new Date()))
const cards = ref<MemberCard[]>([])
const keyword = ref('')
const severityFilter = ref<SeverityFilter>('all')
const categoryFilter = ref('all')

const severityOptions = [
  { label: '全部风险', value: 'all' },
  { label: '高风险', value: 'high' },
  { label: '中风险', value: 'medium' },
  { label: '低风险', value: 'low' }
]

const normalizeSeverity = (value: string): Exclude<SeverityFilter, 'all'> => {
  const raw = String(value || '').toLowerCase()
  if (raw.includes('critical') || raw.includes('high') || raw.includes('阻断') || raw.includes('严重') || raw.includes('高')) {
    return 'high'
  }
  if (raw.includes('medium') || raw.includes('中')) {
    return 'medium'
  }
  return 'low'
}

const severityLabel = (value: string): string => {
  const level = normalizeSeverity(value)
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  return '低风险'
}

const severityTag = (value: string): 'danger' | 'warn' | 'success' => {
  const level = normalizeSeverity(value)
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warn'
  return 'success'
}

const avatarText = (owner: string): string => {
  const raw = String(owner || '').trim()
  if (!raw) return 'NA'
  if (/\s/.test(raw)) {
    return raw
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((item) => item[0]?.toUpperCase() || '')
      .join('') || raw.slice(0, 2).toUpperCase()
  }
  return raw.slice(0, 2).toUpperCase()
}

const avatarToneClass = (card: MemberCard): string => {
  const level = normalizeSeverity(card.top_severity)
  if (level === 'high') return 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200'
  if (level === 'medium') return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200'
  return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200'
}

const cardToneClass = (card: MemberCard): string => {
  const level = normalizeSeverity(card.top_severity)
  if (level === 'high') {
    return 'border-rose-200/80 bg-rose-50/60 hover:border-rose-300 dark:border-rose-500/30 dark:bg-rose-500/10 dark:hover:border-rose-400/60'
  }
  if (level === 'medium') {
    return 'border-amber-200/80 bg-amber-50/60 hover:border-amber-300 dark:border-amber-500/30 dark:bg-amber-500/10 dark:hover:border-amber-400/60'
  }
  return 'border-emerald-200/80 bg-emerald-50/60 hover:border-emerald-300 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:hover:border-emerald-400/60'
}

const categoryOptions = computed(() => {
  const categories = new Set<string>()
  for (const card of cards.value) {
    const category = String(card.top_category || '').trim()
    if (category) categories.add(category)
  }
  return [{ label: '全部类型', value: 'all' }, ...[...categories].sort().map((item) => ({ label: item, value: item }))]
})

const filteredCards = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const results = cards.value.filter((card) => {
    if (kw && !String(card.owner).toLowerCase().includes(kw)) return false
    if (severityFilter.value !== 'all' && normalizeSeverity(card.top_severity) !== severityFilter.value) return false
    if (categoryFilter.value !== 'all' && card.top_category !== categoryFilter.value) return false
    return true
  })

  return results.slice().sort((a, b) => {
    const levelWeight = { high: 3, medium: 2, low: 1 }
    const severityGap = levelWeight[normalizeSeverity(b.top_severity)] - levelWeight[normalizeSeverity(a.top_severity)]
    if (severityGap !== 0) return severityGap
    if (b.total_findings !== a.total_findings) return b.total_findings - a.total_findings
    return a.owner.localeCompare(b.owner)
  })
})

const loadCards = async () => {
  loading.value = true
  try {
    const response = await getDeveloperWeeklyCards({
      anchor_date: anchorDate.value || undefined,
      limit: 100
    }) as MemberCardResponse
    cards.value = Array.isArray(response?.results) ? response.results : []
  } catch (error) {
    console.error('加载成员卡片失败:', error)
    toast.error('加载成员卡片失败')
  } finally {
    loading.value = false
  }
}

const goToDetail = async (owner: string) => {
  await router.push({
    name: 'PublicWeeklyReportMemberDetail',
    params: { owner },
    query: { anchor_date: anchorDate.value }
  })
}

onMounted(() => {
  if (typeof route.query.anchor_date === 'string' && route.query.anchor_date.trim()) {
    anchorDate.value = route.query.anchor_date.trim()
  }
  loadCards()
})
</script>
