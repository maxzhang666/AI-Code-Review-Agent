<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
          <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">最近事件</h3>
        </div>

        <div class="space-y-4">
          <div
            v-for="(event, index) in events"
            :key="index"
            class="flex gap-4 p-4 rounded-xl bg-surface-50 hover:bg-surface-100 transition-colors duration-200 dark:bg-surface-800/70 dark:hover:bg-surface-800"
          >
            <div class="flex-shrink-0">
              <div :class="['w-10 h-10 rounded-xl flex items-center justify-center', getEventBgColor(event.type)]">
                <component :is="getEventIcon(event.type)" class="w-5 h-5 text-white" />
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1">
                  <h4 class="font-semibold text-surface-900 dark:text-surface-100">{{ event.title }}</h4>
                  <p class="text-xs text-surface-600 mt-0.5 dark:text-surface-300">{{ event.description }}</p>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <IconButton
                    v-if="getGitLabEventUrl(event)"
                    size="small"
                    aria-label="打开事件详情"
                    @click="openUrl(getGitLabEventUrl(event))"
                  >
                    <ExternalLink class="w-4 h-4" />
                  </IconButton>
                  <span class="text-2xs text-surface-500 dark:text-surface-400">{{ event.time }}</span>
                </div>
              </div>
              <div class="flex items-center gap-3 mt-2">
                <div class="flex items-center gap-1.5 text-2xs text-surface-600 dark:text-surface-300">
                  <User class="w-3 h-3" />
                  <span>{{ event.author }}</span>
                </div>
                <div class="flex items-center gap-1.5 text-2xs text-surface-600 dark:text-surface-300">
                  <GitBranch class="w-3 h-3" />
                  <span>{{ event.branch }}</span>
                </div>
                <Tag :severity="getEventTagSeverity(event.status)">{{ event.status }}</Tag>
              </div>
            </div>
          </div>

          <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-4">
            <Button text size="small" :disabled="currentPage === 1" @click="$emit('page-change', currentPage - 1)">上一页</Button>
            <div class="flex items-center gap-1">
              <Button v-if="currentPage > 3" text size="small" @click="$emit('page-change', 1)">1</Button>
              <span v-if="currentPage > 4" class="px-2 text-surface-400">...</span>
              <Button
                v-for="page in visiblePages"
                :key="page"
                text
                size="small"
                :class="currentPage === page ? '!bg-primary !text-white hover:!bg-primary' : ''"
                @click="$emit('page-change', page)"
              >{{ page }}</Button>
              <span v-if="currentPage < totalPages - 3" class="px-2 text-surface-400">...</span>
              <Button v-if="currentPage < totalPages - 2" text size="small" @click="$emit('page-change', totalPages)">{{ totalPages }}</Button>
            </div>
            <Button text size="small" :disabled="currentPage === totalPages" @click="$emit('page-change', currentPage + 1)">下一页</Button>
          </div>

          <div v-if="events.length === 0" class="p-8 text-center">
            <div class="text-surface-400">暂无事件记录</div>
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ExternalLink, User, GitBranch, GitCommit, GitMerge,
  AlertTriangle, MessageSquare,
  Tag as TagIcon, Play, Hammer, BookOpen, Rocket, Package
} from 'lucide-vue-next'
import IconButton from '@/components/ui/IconButton.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

const props = defineProps<{
  events: any[]
  currentPage: number
  totalEvents: number
  pageSize: number
  projectUrl?: string
}>()

defineEmits<{ 'page-change': [page: number] }>()

const totalPages = computed(() => Math.ceil(props.totalEvents / props.pageSize))

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, props.currentPage - 2)
  const end = Math.min(totalPages.value, props.currentPage + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const getEventIcon = (type: string) => {
  const map: Record<string, any> = {
    merge_request: GitMerge, push: GitCommit, note: MessageSquare,
    issue: AlertTriangle, tag_push: TagIcon, pipeline: Play,
    build: Hammer, wiki: BookOpen, deployment: Rocket, release: Package,
  }
  return map[type] || GitCommit
}

const getEventBgColor = (type: string) => {
  const map: Record<string, string> = {
    merge_request: 'bg-green-500', push: 'bg-blue-500', note: 'bg-indigo-500',
    issue: 'bg-orange-500', tag_push: 'bg-teal-500', pipeline: 'bg-purple-500',
    build: 'bg-amber-500', wiki: 'bg-cyan-500', deployment: 'bg-emerald-500', release: 'bg-pink-500',
  }
  return map[type] || 'bg-surface-400'
}

const getEventTagSeverity = (status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' => {
  const positiveStatuses = ['已审查', '已推送', '已评论', '已记录', '已处理', '成功', '通过', '已合并', '已批准']
  if (positiveStatuses.includes(status)) return 'success'
  if (status === '处理中') return 'info'
  if (status === '已关闭') return 'danger'
  if (status === '警告') return 'warn'
  if (status === '失败') return 'danger'
  return 'secondary'
}

const getGitLabEventUrl = (event: any) => {
  if (!props.projectUrl) return null
  const baseUrl = props.projectUrl.replace(/\.git$/, '')
  switch (event.type) {
    case 'merge_request':
      return event.merge_request_iid ? `${baseUrl}/-/merge_requests/${event.merge_request_iid}` : baseUrl
    case 'push':
      return event.source_branch ? `${baseUrl}/-/commits/${event.source_branch}` : baseUrl
    case 'note':
      if (event.merge_request_iid && event.note_id) return `${baseUrl}/-/merge_requests/${event.merge_request_iid}#note_${event.note_id}`
      if (event.issue_iid && event.note_id) return `${baseUrl}/-/issues/${event.issue_iid}#note_${event.note_id}`
      return baseUrl
    case 'issue':
      return event.issue_iid ? `${baseUrl}/-/issues/${event.issue_iid}` : baseUrl
    case 'tag_push':
      return event.tag_name ? `${baseUrl}/-/tags/${event.tag_name}` : baseUrl
    case 'pipeline':
      return event.pipeline_id ? `${baseUrl}/-/pipelines/${event.pipeline_id}` : baseUrl
    case 'wiki':
      return event.wiki_slug ? `${baseUrl}/-/wikis/${event.wiki_slug}` : baseUrl
    case 'release':
      return event.release_tag ? `${baseUrl}/-/releases/${event.release_tag}` : baseUrl
    case 'deployment':
      return `${baseUrl}/-/environments`
    default:
      return baseUrl
  }
}

const openUrl = (url?: string | null) => {
  if (url) window.open(url, '_blank')
}
</script>
