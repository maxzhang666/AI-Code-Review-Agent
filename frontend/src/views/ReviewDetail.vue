<template>
  <div class="space-y-6">
    <div>
      <Button text label="返回列表" @click="goBack">
        <template #icon><ArrowLeft class="w-4 h-4" /></template>
      </Button>
      <div class="mt-3 flex items-center gap-3">
        <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-0">审查详情 - MR !{{ review.merge_request_iid }}</h2>
        <Tag :severity="statusSeverity(review.status)">{{ statusLabel(review.status) }}</Tag>
        <Tag v-if="review.is_mock" severity="warn">Mock</Tag>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab
          v-for="tab in tabs"
          :key="tab.key"
          :value="tab.key"
        >
          {{ tab.label }}
        </Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="basic">
          <div class="relative">
            <div v-if="loading" class="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-white/70 backdrop-blur-[1px] dark:bg-surface-900/70">
              <div class="inline-flex items-center gap-2 rounded-lg border border-surface-200 bg-white px-3 py-2 text-surface-600 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
                <Loader2 class="h-4 w-4 animate-spin" />
                加载中...
              </div>
            </div>

            <Card>
              <template #content>
                <div class="space-y-4">
                  <h3 class="mb-4 text-xl font-semibold tracking-tight text-color">基本信息</h3>

                  <div class="space-y-3">
                    <div class="grid grid-cols-1 gap-6 text-xs font-medium text-surface-500 xl:grid-cols-2">
                      <div>MR 信息</div>
                      <div>审查信息</div>
                    </div>

                    <div class="space-y-0">
                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex items-center gap-2 text-xs text-surface-600">
                            <GitPullRequest class="h-4 w-4" />
                            <span>MR ID</span>
                          </div>
                          <div class="flex items-start gap-1 pt-0.5">
                            <span class="font-semibold leading-none text-surface-900 dark:text-surface-100">!{{ displayText(review.merge_request_iid) }}</span>
                            <IconButton
                              v-if="mrUrl"
                              size="small"
                              aria-label="新页面打开MR"
                              @click="openMrInNewTab"
                            >
                              <ExternalLink class="h-3.5 w-3.5" />
                            </IconButton>
                          </div>
                        </div>
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <GitBranch class="h-4 w-4" />
                            <span>源分支</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.source_branch) }}
                          </span>
                        </div>
                      </div>

                      <div class="h-px bg-surface-200/60" />

                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <FolderKanban class="h-4 w-4" />
                            <span>项目</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.project_name) }}
                          </span>
                        </div>
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <Split class="h-4 w-4" />
                            <span>目标分支</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.target_branch) }}
                          </span>
                        </div>
                      </div>

                      <div class="h-px bg-surface-200/60" />

                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <UserRound class="h-4 w-4" />
                            <span>作者</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.author_name) }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                          <div class="flex items-center gap-2 text-xs text-surface-600">
                            <Files class="h-4 w-4" />
                            <span>文件数</span>
                          </div>
                          <span class="font-semibold text-surface-900 dark:text-surface-100">{{ review.total_files || 0 }}</span>
                        </div>
                      </div>

                      <div class="h-px bg-surface-200/60" />

                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <Mail class="h-4 w-4" />
                            <span>邮箱</span>
                          </div>
                          <span class="flex-1 break-all text-right font-mono text-xs text-surface-700 dark:text-surface-300">
                            {{ displayText(review.author_email) }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                          <div class="flex items-center gap-2 text-xs text-surface-600">
                            <BadgeCheck class="h-4 w-4" />
                            <span>评分</span>
                          </div>
                          <span v-if="review.review_score != null" class="font-semibold text-surface-900 dark:text-surface-100">
                            {{ review.review_score }}<span class="text-surface-500">/100</span>
                          </span>
                          <span v-else class="text-surface-400">-</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="h-px bg-surface-200/60" />

                  <div class="space-y-3">
                    <div class="grid grid-cols-1 gap-6 text-xs font-medium text-surface-500 xl:grid-cols-2">
                      <div>模型与时间</div>
                      <div>审查时间</div>
                    </div>

                    <div class="space-y-0">
                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <Bot class="h-4 w-4" />
                            <span>LLM 供应商</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.llm_provider) }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                          <div class="flex items-center gap-2 text-xs text-surface-600">
                            <CalendarDays class="h-4 w-4" />
                            <span>创建时间</span>
                          </div>
                          <span class="text-surface-800 dark:text-surface-200">{{ formatDisplayTime(review.created_at) }}</span>
                        </div>
                      </div>

                      <div class="h-px bg-surface-200/60" />

                      <div class="grid grid-cols-1 gap-6 py-2 xl:grid-cols-2">
                        <div class="flex items-start justify-between gap-4">
                          <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                            <Sparkles class="h-4 w-4" />
                            <span>LLM 模型</span>
                          </div>
                          <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                            {{ displayText(review.llm_model) }}
                          </span>
                        </div>
                        <div class="flex items-center justify-between gap-4">
                          <div class="flex items-center gap-2 text-xs text-surface-600">
                            <Clock3 class="h-4 w-4" />
                            <span>完成时间</span>
                          </div>
                          <span class="text-surface-800 dark:text-surface-200">{{ formatDisplayTime(review.completed_at) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="h-px bg-surface-200/60" />

                  <div class="space-y-2">
                    <div class="inline-flex items-center gap-2 text-xs text-surface-600">
                      <FileText class="h-4 w-4" />
                      <span>MR 标题</span>
                    </div>
                    <p class="whitespace-pre-wrap break-words text-sm leading-6 text-surface-700 dark:text-surface-200">
                      {{ displayText(review.merge_request_title) }}
                    </p>
                  </div>

                  <div v-if="review.error_message" class="space-y-2 rounded-xl border border-red-200/80 bg-red-50/70 p-3 dark:border-red-500/40 dark:bg-red-500/10">
                    <div class="inline-flex items-center gap-2 text-xs font-medium text-red-500 dark:text-red-300">
                      <AlertTriangle class="h-4 w-4" />
                      <span>错误信息</span>
                    </div>
                    <p class="whitespace-pre-wrap break-words text-sm leading-6 text-red-600 dark:text-red-200">
                      {{ review.error_message }}
                    </p>
                  </div>
                </div>
              </template>
            </Card>
          </div>
        </TabPanel>

        <TabPanel value="summary">
          <Card>
            <template #content>
              <template v-if="hasStructuredData">
                <div class="mb-6 flex items-center gap-6 rounded-lg bg-gray-50 p-4 dark:bg-surface-800/70">
                  <div class="text-center">
                    <div class="text-3xl font-bold" :class="scoreColorClass">{{ review.review_score ?? '-' }}</div>
                    <div class="mt-1 ray-500">评分 / 100</div>
                  </div>
                  <div v-if="review.review_score != null" class="flex items-center gap-1">
                    <span v-for="i in 5" :key="i" class="text-xl" :class="i <= starCount ? 'text-yellow-400 dark:text-yellow-300' : 'text-gray-300 dark:text-surface-600'">★</span>
                  </div>
                </div>

                <div v-if="parsedSummary" class="mb-6">
                  <h3 class="mb-2 text-lg font-semibold text-surface-800">📝 审查摘要</h3>
                  <p class="leading-relaxed text-surface-700">{{ parsedSummary }}</p>
                </div>

                <div v-if="parsedHighlights.length > 0">
                  <h3 class="mb-2 text-lg font-semibold text-surface-800">✅ 代码优点</h3>
                  <ul class="space-y-2">
                    <li v-for="(h, idx) in parsedHighlights" :key="idx" class="flex items-start gap-2">
                      <span class="mt-0.5 shrink-0 text-green-500 dark:text-green-300">●</span>
                      <span class="text-surface-700">{{ h }}</span>
                    </li>
                  </ul>
                </div>

                <div v-if="!parsedSummary && parsedHighlights.length === 0" class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-6 text-center text-surface-500">
                  无摘要信息
                </div>
              </template>

              <template v-else>
                <div v-if="review.review_content" class="prose max-w-none" v-html="renderedContent"></div>
                <div v-else class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-6 text-center text-surface-500">
                  暂无审查内容
                </div>
              </template>
            </template>
          </Card>
        </TabPanel>

        <TabPanel value="issues">
          <Card>
            <template #content>
              <div v-if="issuesList.length > 0" class="mb-4 flex flex-wrap items-center gap-3">
                <Tag severity="info">{{ allFilePaths.length }} 个文件</Tag>
                <Tag v-if="criticalCount > 0" severity="danger">阻断 {{ criticalCount }}</Tag>
                <Tag v-if="highCount > 0" severity="danger">严重 {{ highCount }}</Tag>
                <Tag v-if="mediumCount > 0" severity="warn">中等 {{ mediumCount }}</Tag>
                <Tag v-if="lowCount > 0" severity="success">轻微 {{ lowCount }}</Tag>
              </div>

              <div
                v-if="structuredFindings.length > 0"
                class="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900"
              >
                <span class="text-xs text-surface-500">点击问题下方按钮写入处理动作</span>
              </div>

              <template v-if="issuesList.length > 0 || allFilePaths.length > 0">
                <div v-if="filesWithIssues.length > 0" class="space-y-2">
                  <details
                    v-for="group in filesWithIssues"
                    :key="group.file"
                    class="overflow-hidden rounded-xl border border-surface-200/70 bg-white dark:border-surface-700/70 dark:bg-surface-900"
                    :open="defaultExpandedFiles.includes(group.file)"
                  >
                    <summary class="flex cursor-pointer list-none items-center gap-2 bg-surface-50/70 px-3 py-2">
                      <span class="font-mono text-surface-800">{{ group.file }}</span>
                      <Tag :severity="group.maxSeverity === 'high' ? 'danger' : group.maxSeverity === 'medium' ? 'warn' : 'success'">
                        {{ group.issues.length }} 个问题
                      </Tag>
                    </summary>
                    <div class="space-y-4 p-3">
                      <div
                        v-for="(issue, idx) in group.issues"
                        :key="idx"
                        class="border-l-2 py-2 pl-3 transition-all duration-300"
                        :class="[
                          issueBorderClass(issue.severity),
                          isFindingRecentlyUpdated(issue.id)
                            ? 'rounded-md bg-primary-50/60 ring-1 ring-primary-300/70 dark:bg-primary-900/20 dark:ring-primary-500/40'
                            : '',
                        ]"
                      >
                        <div class="mb-1 flex items-center gap-2">
                          <Tag :severity="severityTag(issue.severity)">{{ severityLabel(issue.severity) }}</Tag>
                          <Tag severity="secondary">{{ issue.category || '质量' }}</Tag>
                          <span v-if="issue.line" class="font-mono text-xs text-gray-400 dark:text-surface-500">L{{ issue.line }}</span>
                        </div>
                        <p class="mb-1 text-surface-800">{{ issue.description }}</p>
                        <div v-if="issue.code_snippet" class="mt-2">
                          <div class="mb-1 text-xs font-medium text-surface-500">
                            问题代码
                            <span v-if="issue.line != null" class="font-mono"> (L{{ issue.line }}<template v-if="issue.line_end != null && issue.line_end !== issue.line">-L{{ issue.line_end }}</template>)</span>
                          </div>
                          <pre class="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-slate-100"><code>{{ issue.code_snippet }}</code></pre>
                        </div>
                        <div v-if="issue.suggestion" class="mt-2">
                          <pre class="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-800 p-3 text-slate-200"><code>{{ issue.suggestion }}</code></pre>
                        </div>
                        <div
                          v-if="issue.id != null"
                          class="mt-3 space-y-2 rounded-lg border border-surface-200/70 bg-surface-50 p-3 dark:border-surface-700/70 dark:bg-surface-900"
                        >
                          <InputText
                            :model-value="getActionNote(issue.id)"
                            class="h-8 w-full"
                            placeholder="处理备注（可选）"
                            @update:model-value="setActionNote(issue.id, String($event || ''))"
                          />
                          <div class="flex items-center gap-2">
                            <span class="text-xs text-surface-500">当前状态</span>
                            <Tag :severity="actionStatusSeverityByFindingId(issue.id)">
                              {{ actionStatusLabelByFindingId(issue.id) }}
                            </Tag>
                            <span v-if="lastActionMessage(issue.id)" class="text-xs text-surface-500">
                              {{ lastActionMessage(issue.id) }}
                            </span>
                          </div>
                          <div class="flex flex-wrap items-center gap-2">
                            <Button
                              v-if="canShowAction(issue.id, 'todo')"
                              size="small"
                              severity="warn"
                              outlined
                              :loading="isActionLoading(issue.id)"
                              label="待处理"
                              @click="submitFindingAction(issue.id, 'todo')"
                            />
                            <Button
                              v-if="canShowAction(issue.id, 'fixed')"
                              size="small"
                              severity="success"
                              outlined
                              :loading="isActionLoading(issue.id)"
                              label="已修复"
                              @click="submitFindingAction(issue.id, 'fixed')"
                            />
                            <Button
                              v-if="canShowAction(issue.id, 'ignored')"
                              size="small"
                              severity="secondary"
                              outlined
                              :loading="isActionLoading(issue.id)"
                              label="忽略"
                              @click="openIgnoreDialog(issue.id)"
                            />
                            <Button
                              v-if="canShowAction(issue.id, 'reopened')"
                              size="small"
                              severity="danger"
                              outlined
                              :loading="isActionLoading(issue.id)"
                              label="重新打开"
                              @click="confirmReopenAction(issue.id)"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </details>
                </div>

                <div v-if="filesWithoutIssues.length > 0" class="mt-4">
                  <div class="mb-2 text-gray-500 dark:text-surface-400">以下文件未发现问题</div>
                  <div v-for="fp in filesWithoutIssues" :key="fp" class="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-surface-800/70">
                    <span class="text-xs text-green-500 dark:text-green-300">✓</span>
                    <span class="font-mono text-surface-700">{{ fp }}</span>
                  </div>
                </div>
              </template>

              <div v-else class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-6 text-center text-surface-500">
                {{ hasStructuredData ? '未发现问题' : '暂无审查数据' }}
              </div>
            </template>
          </Card>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <Dialog
      v-model:visible="ignoreDialogVisible"
      modal
      :draggable="false"
      header="忽略原因"
      :style="{ width: '32rem', maxWidth: '95vw' }"
    >
      <div class="space-y-3">
        <div class="text-xs text-surface-500">
          当前操作将仅作用于该条问题，忽略原因必填。
        </div>
        <label class="flex flex-col gap-1">
          <span class="text-xs font-medium text-surface-600">忽略原因</span>
          <Select
            v-model="ignoreDialogReasonCode"
            :options="ignoreReasonOptions"
            option-label="label"
            option-value="value"
            placeholder="请选择忽略原因"
            class="w-full"
          />
        </label>
        <label class="flex flex-col gap-1">
          <span class="text-xs font-medium text-surface-600">
            备注
            <span v-if="isIgnoreDialogReasonNoteRequired" class="text-red-500">*</span>
          </span>
          <InputText
            v-model="ignoreDialogReasonNote"
            class="w-full"
            :placeholder="isIgnoreDialogReasonNoteRequired ? '该原因必须填写备注' : '可选备注'"
            maxlength="500"
          />
        </label>
        <div class="flex justify-end gap-2">
          <Button text label="取消" @click="closeIgnoreDialog" />
          <Button
            severity="secondary"
            label="确认忽略"
            :loading="ignoreSubmitting"
            @click="confirmIgnoreAction"
          />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  GitPullRequest,
  FolderKanban,
  UserRound,
  Mail,
  GitBranch,
  Split,
  Files,
  BadgeCheck,
  Bot,
  Sparkles,
  CalendarDays,
  Clock3,
  FileText,
  AlertTriangle,
} from 'lucide-vue-next'
import { marked } from 'marked'
import {
  createReviewFindingAction,
  getProjectDetail,
  getReviewDetail,
  getReviewFindingActions,
  getReviewFindings,
} from '@/api/index'
import { formatBackendDateTime } from '@/utils/datetime'
import { getReviewStatusMeta } from '@/utils/reviewStatus'
import { toast } from '@/utils/toast'
import IconButton from '@/components/ui/IconButton.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'

interface ReviewIssue {
  id: number | null
  severity: string
  category: string
  subcategory?: string
  file: string
  line: number | null
  line_end?: number | null
  description: string
  suggestion: string
  code_snippet: string
  owner?: string | null
}

interface StructuredFinding {
  id: number
  review_id: number
  fingerprint: string
  category: string
  subcategory: string
  severity: string
  confidence: number | null
  file_path: string
  line_start: number | null
  line_end: number | null
  message: string
  suggestion: string
  code_snippet: string
  owner: string | null
  is_blocking: boolean
  is_false_positive: boolean
}

type FindingActionType = 'fixed' | 'ignored' | 'todo' | 'reopened'
type FindingActionStatus = FindingActionType | 'unprocessed'
type IgnoreReasonCode = 'business_exception' | 'historical_debt' | 'rule_false_positive' | 'defer_fix' | 'duplicate' | 'other'

const router = useRouter()
const route = useRoute()
const activeTab = ref('basic')
const loading = ref(false)
const mrUrl = ref('')
const structuredFindings = ref<StructuredFinding[]>([])
const ignoreDialogVisible = ref(false)
const ignoreDialogFindingId = ref<number | null>(null)
const ignoreDialogReasonCode = ref<IgnoreReasonCode | ''>('')
const ignoreDialogReasonNote = ref('')
const ignoreSubmitting = ref(false)
const actionNotes = ref<Record<number, string>>({})
const actionLoadingMap = ref<Record<number, boolean>>({})
const actionMessageMap = ref<Record<number, string>>({})
const actionStatusMap = ref<Record<number, string>>({})
const recentlyUpdatedFindingId = ref<number | null>(null)
let recentlyUpdatedTimer: ReturnType<typeof setTimeout> | null = null

const tabs = [
  { key: 'basic', label: '基本信息' },
  { key: 'summary', label: '审查摘要' },
  { key: 'issues', label: '审查问题与文件' },
]

const review = ref<Record<string, any>>({
  merge_request_iid: null,
  project_name: '',
  merge_request_title: '',
  author_name: '',
  author_email: '',
  source_branch: '',
  target_branch: '',
  status: 'pending',
  review_content: '',
  review_score: null,
  review_issues: [],
  review_summary: '',
  review_highlights: [],
  files_reviewed: [],
  total_files: 0,
  llm_provider: '',
  llm_model: '',
  is_mock: false,
  created_at: '',
  completed_at: '',
  error_message: '',
})

const issuesList = computed<ReviewIssue[]>(() => {
  if (structuredFindings.value.length > 0) {
    return structuredFindings.value.map((item) => ({
      id: item.id,
      severity: item.severity,
      category: item.category,
      subcategory: item.subcategory,
      file: item.file_path,
      line: item.line_start,
      line_end: item.line_end,
      description: item.message,
      suggestion: item.suggestion,
      code_snippet: item.code_snippet || '',
      owner: item.owner,
    }))
  }
  const raw = review.value.review_issues
  if (!Array.isArray(raw)) return []
  return raw.map((item: any) => ({
    id: null,
    severity: String(item?.severity || 'medium'),
    category: String(item?.category || '质量'),
    subcategory: String(item?.subcategory || ''),
    file: String(item?.file || item?.file_path || ''),
    line: typeof item?.line === 'number' ? item.line : (typeof item?.line_start === 'number' ? item.line_start : null),
    line_end: typeof item?.line_end === 'number' ? item.line_end : null,
    description: String(item?.description || item?.message || ''),
    suggestion: String(item?.suggestion || ''),
    code_snippet: String(item?.code_snippet || item?.problematic_code || item?.problem_code || item?.code || item?.snippet || ''),
    owner: item?.owner ? String(item.owner) : null,
  }))
})

const hasStructuredData = computed(() => issuesList.value.length > 0 || parsedSummary.value || parsedHighlights.value.length > 0)

const parsedSummary = computed(() => {
  return review.value.review_summary || ''
})

const parsedHighlights = computed<string[]>(() => {
  const raw = review.value.review_highlights
  return Array.isArray(raw) ? raw : []
})

const starCount = computed(() => {
  const score = review.value.review_score
  if (score == null) return 0
  if (score >= 90) return 5
  if (score >= 75) return 4
  if (score >= 60) return 3
  if (score >= 40) return 2
  return 1
})

const scoreColorClass = computed(() => {
  const score = review.value.review_score
  if (score == null) return 'text-gray-400 dark:text-surface-500'
  if (score >= 80) return 'text-green-600 dark:text-green-300'
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-300'
  return 'text-red-600 dark:text-red-300'
})

const criticalCount = computed(() => issuesList.value.filter(i => i.severity === 'critical').length)
const highCount = computed(() => issuesList.value.filter(i => i.severity === 'high').length)
const mediumCount = computed(() => issuesList.value.filter(i => i.severity === 'medium').length)
const lowCount = computed(() => issuesList.value.filter(i => i.severity === 'low').length)

interface FileIssueGroup {
  file: string
  issues: ReviewIssue[]
  maxSeverity: string
}

interface IgnoreReasonOption {
  label: string
  value: IgnoreReasonCode
}

const allFilePaths = computed<string[]>(() => {
  const fromReview = Array.isArray(review.value.files_reviewed) ? review.value.files_reviewed as string[] : []
  const fromIssues = issuesList.value.map(i => i.file).filter(Boolean)
  const set = new Set([...fromReview, ...fromIssues])
  return [...set]
})

const issuesByFile = computed(() => {
  const map = new Map<string, ReviewIssue[]>()
  for (const issue of issuesList.value) {
    const key = issue.file || ''
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(issue)
  }
  return map
})

const severityRank = (s: string) => (s === 'critical' ? 4 : s === 'high' ? 3 : s === 'medium' ? 2 : 1)

const ignoreReasonOptions: IgnoreReasonOption[] = [
  { label: '业务特例', value: 'business_exception' },
  { label: '历史债务', value: 'historical_debt' },
  { label: '规则误报', value: 'rule_false_positive' },
  { label: '暂缓修复', value: 'defer_fix' },
  { label: '重复问题', value: 'duplicate' },
  { label: '其他', value: 'other' },
]
const isIgnoreDialogReasonNoteRequired = computed(
  () => ignoreDialogReasonCode.value === 'defer_fix' || ignoreDialogReasonCode.value === 'other'
)

const filesWithIssues = computed<FileIssueGroup[]>(() => {
  const groups: FileIssueGroup[] = []
  for (const [file, issues] of issuesByFile.value.entries()) {
    if (!file && issues.length > 0) {
      groups.push({ file: '(未知文件)', issues, maxSeverity: issues.reduce((m, i) => severityRank(i.severity) > severityRank(m) ? i.severity : m, 'low') })
      continue
    }
    if (issues.length > 0) {
      groups.push({ file, issues, maxSeverity: issues.reduce((m, i) => severityRank(i.severity) > severityRank(m) ? i.severity : m, 'low') })
    }
  }
  groups.sort((a, b) => severityRank(b.maxSeverity) - severityRank(a.maxSeverity))
  return groups
})

const filesWithoutIssues = computed<string[]>(() => {
  const hasIssuesSet = new Set(issuesByFile.value.keys())
  return allFilePaths.value.filter(fp => !hasIssuesSet.has(fp))
})

const defaultExpandedFiles = computed(() =>
  filesWithIssues.value
    .filter(g => g.maxSeverity === 'high')
    .map(g => g.file)
)

const renderedContent = computed(() => {
  if (!review.value.review_content) return ''
  return marked(review.value.review_content) as string
})

const buildMergeRequestUrl = (projectUrl: string, mrIid: number | null | undefined): string => {
  if (!projectUrl || mrIid == null) return ''
  const trimmed = projectUrl.trim()
  if (!trimmed) return ''
  const base = trimmed.replace(/\.git$/i, '').replace(/\/+$/, '')
  return `${base}/-/merge_requests/${mrIid}`
}

const fetchReview = async () => {
  const id = route.params.id as string
  if (!id) return
  loading.value = true
  try {
    const response = await getReviewDetail(id)
    if (response) {
      review.value = response
      await fetchReviewFindings(id)
      if (response.merge_request_url) {
        mrUrl.value = String(response.merge_request_url)
      } else if (response.project_id && response.merge_request_iid != null) {
        try {
          const projectDetail = await getProjectDetail(String(response.project_id))
          const projectUrl = String(projectDetail?.project_url || '')
          mrUrl.value = buildMergeRequestUrl(projectUrl, response.merge_request_iid)
        } catch (error) {
          console.error('获取项目详情失败，无法构建 MR 链接:', error)
          mrUrl.value = ''
        }
      } else {
        mrUrl.value = ''
      }
    }
  } catch (error) {
    console.error('获取审查详情失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchReviewFindings = async (id: string) => {
  try {
    const response = await getReviewFindings(id)
    const findings = Array.isArray(response?.results) ? response.results : []
    structuredFindings.value = findings
    await hydrateFindingActionState(findings)
  } catch (error) {
    console.error('获取结构化问题失败:', error)
    structuredFindings.value = []
    actionStatusMap.value = {}
    actionMessageMap.value = {}
  }
}

const getActionNote = (findingId: number | null): string => {
  if (findingId == null) return ''
  return actionNotes.value[findingId] || ''
}

const setActionNote = (findingId: number | null, value: string) => {
  if (findingId == null) return
  actionNotes.value[findingId] = value
}

const isActionLoading = (findingId: number | null): boolean => {
  if (findingId == null) return false
  return Boolean(actionLoadingMap.value[findingId])
}

const lastActionMessage = (findingId: number | null): string => {
  if (findingId == null) return ''
  return actionMessageMap.value[findingId] || ''
}

const actionTypeLabel = (actionType: FindingActionType): string => {
  if (actionType === 'fixed') return '已修复'
  if (actionType === 'todo') return '待处理'
  if (actionType === 'ignored') return '已忽略'
  if (actionType === 'reopened') return '重新打开'
  return actionType
}

const actionStatusLabel = (status: FindingActionStatus): string => {
  if (status === 'unprocessed') return '未处理'
  return actionTypeLabel(status)
}

const actionStatusSeverity = (status: FindingActionStatus): 'success' | 'warn' | 'danger' | 'info' | 'secondary' => {
  if (status === 'fixed') return 'success'
  if (status === 'todo') return 'warn'
  if (status === 'ignored') return 'danger'
  if (status === 'reopened') return 'info'
  return 'secondary'
}

const normalizeActionStatus = (value: unknown): FindingActionStatus => {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'fixed' || normalized === 'ignored' || normalized === 'todo' || normalized === 'reopened') {
    return normalized
  }
  return 'unprocessed'
}

const actionStatusByFindingId = (findingId: number | null): FindingActionStatus => {
  if (findingId == null) return 'unprocessed'
  return normalizeActionStatus(actionStatusMap.value[findingId])
}

const actionStatusLabelByFindingId = (findingId: number | null): string =>
  actionStatusLabel(actionStatusByFindingId(findingId))

const actionStatusSeverityByFindingId = (findingId: number | null): 'success' | 'warn' | 'danger' | 'info' | 'secondary' =>
  actionStatusSeverity(actionStatusByFindingId(findingId))

const canShowAction = (findingId: number | null, actionType: FindingActionType): boolean => {
  const status = actionStatusByFindingId(findingId)
  if (actionType === 'reopened') return status !== 'unprocessed' && status !== 'reopened'
  if (actionType === 'ignored') return status !== 'ignored'
  if (actionType === 'fixed') return status !== 'fixed'
  if (actionType === 'todo') return status !== 'todo'
  return true
}

const isFindingRecentlyUpdated = (findingId: number | null): boolean =>
  findingId != null && recentlyUpdatedFindingId.value === findingId

const markFindingUpdated = (findingId: number | null) => {
  if (findingId == null) return
  recentlyUpdatedFindingId.value = findingId
  if (recentlyUpdatedTimer) {
    clearTimeout(recentlyUpdatedTimer)
  }
  recentlyUpdatedTimer = setTimeout(() => {
    recentlyUpdatedFindingId.value = null
    recentlyUpdatedTimer = null
  }, 2000)
}

const hydrateFindingActionState = async (findings: StructuredFinding[]) => {
  if (!findings.length) {
    actionStatusMap.value = {}
    actionMessageMap.value = {}
    return
  }

  const statusMap: Record<number, string> = {}
  const messageMap: Record<number, string> = {}
  await Promise.all(
    findings.map(async (item) => {
      try {
        const response = await getReviewFindingActions(item.id)
        const latest = Array.isArray(response?.results) ? response.results[0] : null
        if (!latest) {
          statusMap[item.id] = 'unprocessed'
          return
        }
        const status = normalizeActionStatus(latest.action_type)
        statusMap[item.id] = status
        const actor = String(latest.actor || '').trim()
        if (status !== 'unprocessed') {
          messageMap[item.id] = actor ? `${actionStatusLabel(status)} · ${actor}` : actionStatusLabel(status)
        }
      } catch {
        statusMap[item.id] = 'unprocessed'
      }
    })
  )
  actionStatusMap.value = statusMap
  actionMessageMap.value = messageMap
}

const submitFindingAction = async (
  findingId: number | null,
  actionType: FindingActionType,
  options?: {
    ignoreReasonCode?: IgnoreReasonCode
    ignoreReasonNote?: string
  },
): Promise<boolean> => {
  if (findingId == null) return false

  const actionNote = actionType === 'ignored'
    ? String(options?.ignoreReasonNote ?? getActionNote(findingId)).trim()
    : getActionNote(findingId).trim()
  let reasonCode: IgnoreReasonCode | '' = ''
  if (actionType === 'ignored') {
    reasonCode = options?.ignoreReasonCode || ''
    if (!reasonCode) {
      toast.warning('请选择忽略原因')
      return false
    }
    if ((reasonCode === 'defer_fix' || reasonCode === 'other') && !actionNote) {
      toast.warning('当前忽略原因必须填写处理备注')
      return false
    }
  }

  actionLoadingMap.value[findingId] = true
  try {
    const payload: {
      action_type: FindingActionType
      note: string
      ignore_reason_code?: IgnoreReasonCode
      ignore_reason_note?: string
    } = {
      action_type: actionType,
      note: actionNote,
    }
    if (actionType === 'ignored' && reasonCode) {
      payload.ignore_reason_code = reasonCode
      payload.ignore_reason_note = actionNote
    }
    const resp = await createReviewFindingAction(findingId, payload)
    actionStatusMap.value[findingId] = actionType
    const actor = String(resp?.actor || '').trim()
    actionMessageMap.value[findingId] = actor
      ? `${actionStatusLabel(actionType)} · ${actor}`
      : actionStatusLabel(actionType)
    markFindingUpdated(findingId)
    actionNotes.value[findingId] = ''
    toast.success('处理动作已记录')
    return true
  } catch (error) {
    console.error('记录处理动作失败:', error)
    toast.error('记录处理动作失败')
    return false
  } finally {
    actionLoadingMap.value[findingId] = false
  }
}

const closeIgnoreDialog = () => {
  ignoreDialogVisible.value = false
  ignoreDialogFindingId.value = null
  ignoreDialogReasonCode.value = ''
  ignoreDialogReasonNote.value = ''
}

const openIgnoreDialog = (findingId: number | null) => {
  if (findingId == null) return
  ignoreDialogFindingId.value = findingId
  ignoreDialogReasonCode.value = ''
  ignoreDialogReasonNote.value = ''
  ignoreDialogVisible.value = true
}

const confirmIgnoreAction = async () => {
  const findingId = ignoreDialogFindingId.value
  if (findingId == null) return
  const reasonCode = ignoreDialogReasonCode.value
  if (!reasonCode) {
    toast.warning('请选择忽略原因')
    return
  }
  const reasonNote = ignoreDialogReasonNote.value.trim()
  if (isIgnoreDialogReasonNoteRequired.value && !reasonNote) {
    toast.warning('当前忽略原因必须填写备注')
    return
  }

  ignoreSubmitting.value = true
  try {
    const ok = await submitFindingAction(
      findingId,
      'ignored',
      {
        ignoreReasonCode: reasonCode,
        ignoreReasonNote: reasonNote,
      },
    )
    if (!ok) return
    closeIgnoreDialog()
  } finally {
    ignoreSubmitting.value = false
  }
}

const confirmReopenAction = async (findingId: number | null) => {
  if (findingId == null) return
  const confirmed = window.confirm('确认将该问题重新打开吗？')
  if (!confirmed) return
  await submitFindingAction(findingId, 'reopened')
}

onMounted(() => {
  fetchReview()
})

onBeforeUnmount(() => {
  if (recentlyUpdatedTimer) {
    clearTimeout(recentlyUpdatedTimer)
    recentlyUpdatedTimer = null
  }
})

const goBack = () => {
  router.back()
}

const openMrInNewTab = () => {
  if (!mrUrl.value) return
  window.open(mrUrl.value, '_blank', 'noopener,noreferrer')
}

const formatDisplayTime = (value: string | null | undefined): string => {
  return formatBackendDateTime(value)
}

const displayText = (value: unknown, fallback: string = '-'): string => {
  const text = String(value ?? '').trim()
  return text || fallback
}

const statusLabel = (status: string): string => {
  return getReviewStatusMeta(status).label
}

const statusSeverity = (status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' => {
  return getReviewStatusMeta(status).severity
}

const severityTag = (severity: string): 'success' | 'warn' | 'danger' | 'secondary' => {
  const map: Record<string, 'success' | 'warn' | 'danger' | 'secondary'> = {
    critical: 'danger',
    high: 'danger',
    medium: 'warn',
    low: 'success',
  }
  return map[severity] || 'secondary'
}

const severityLabel = (severity: string): string => {
  const map: Record<string, string> = { critical: '阻断', high: '严重', medium: '中等', low: '轻微' }
  return map[severity] || severity
}

const issueBorderClass = (severity: string): string => {
  const map: Record<string, string> = {
    critical: 'border-red-600 dark:border-red-400',
    high: 'border-red-400 dark:border-red-500/70',
    medium: 'border-orange-400 dark:border-orange-500/70',
    low: 'border-green-400 dark:border-green-500/70'
  }
  return map[severity] || 'border-gray-300 dark:border-surface-600'
}
</script>

<style scoped>
.prose :deep(h1) { font-size: 1.5rem; font-weight: 700; margin: 1rem 0 0.5rem; }
.prose :deep(h2) { font-size: 1.25rem; font-weight: 600; margin: 1rem 0 0.5rem; }
.prose :deep(h3) { font-size: 1.125rem; font-weight: 600; margin: 0.75rem 0 0.5rem; }
.prose :deep(h4) { font-size: 1rem; font-weight: 600; margin: 0.5rem 0 0.25rem; }
.prose :deep(p) { margin: 0.5rem 0; line-height: 1.7; }
.prose :deep(ul), .prose :deep(ol) { padding-left: 1.5rem; margin: 0.5rem 0; }
.prose :deep(li) { margin: 0.25rem 0; }
.prose :deep(pre) { background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 0.75rem; overflow-x: auto; margin: 0.75rem 0; }
.prose :deep(code) { font-size: 0.875rem; }
.prose :deep(p code) { background: #f1f5f9; padding: 0.125rem 0.375rem; border-radius: 0.25rem; color: #334155; }
.prose :deep(hr) { border: none; border-top: 1px solid #e2e8f0; margin: 1rem 0; }
.prose :deep(strong) { font-weight: 600; }
.prose :deep(blockquote) { border-left: 3px solid #cbd5e1; padding-left: 1rem; color: #64748b; margin: 0.75rem 0; }

details > summary::-webkit-details-marker { display: none; }
</style>
