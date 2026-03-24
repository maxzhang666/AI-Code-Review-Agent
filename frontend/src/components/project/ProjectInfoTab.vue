<template>
  <Card>
    <template #content>
      <div class="space-y-4">
        <h3 class="mb-4 text-xl font-semibold tracking-tight text-color">项目信息</h3>

        <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div class="space-y-3">
            <div class="text-xs font-medium text-surface-500">基础信息</div>

            <div class="flex items-start justify-between gap-4">
              <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                <FolderKanban class="w-4 h-4" />
                <span>项目名称</span>
              </div>
              <span class="flex-1 break-all text-right font-semibold text-surface-900 dark:text-surface-100">
                {{ displayText(project?.project_name) }}
              </span>
            </div>

            <div class="h-px bg-surface-200/60" />

            <div class="flex items-start justify-between gap-4">
              <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                <Boxes class="w-4 h-4" />
                <span>命名空间</span>
              </div>
              <span class="flex-1 break-all text-right text-surface-800 dark:text-surface-200">
                {{ displayText(project?.namespace) }}
              </span>
            </div>

            <div class="h-px bg-surface-200/60" />

            <div class="flex items-start justify-between gap-4">
              <div class="flex shrink-0 items-center gap-2 text-xs text-surface-600">
                <Link2 class="w-4 h-4" />
                <span>项目地址</span>
              </div>
              <div class="flex flex-1 min-w-0 items-center justify-end gap-1">
                <span class="truncate text-right font-mono text-xs text-surface-800 dark:text-surface-200">
                  {{ displayText(project?.project_url) }}
                </span>
                <IconButton
                  size="small"
                  :disabled="!project?.project_url"
                  aria-label="打开项目地址"
                  @click="openUrl(project?.project_url)"
                >
                  <ExternalLink class="w-4 h-4" />
                </IconButton>
              </div>
            </div>
          </div>

          <div class="space-y-3">
            <div class="text-xs font-medium text-surface-500">活动与成员</div>

            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <CalendarDays class="w-4 h-4" />
                <span>创建时间</span>
              </div>
              <span class="text-surface-800 dark:text-surface-200">
                {{ project?.created_at ? formatBackendDate(project.created_at) : '未知' }}
              </span>
            </div>

            <div class="h-px bg-surface-200/60" />

            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <Clock3 class="w-4 h-4" />
                <span>最后活动</span>
              </div>
              <span class="text-surface-800 dark:text-surface-200">
                {{ displayText(project?.last_activity, '未知') }}
              </span>
            </div>

            <div class="h-px bg-surface-200/60" />

            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <Users class="w-4 h-4" />
                <span>团队成员</span>
              </div>
              <span class="font-semibold text-surface-900 dark:text-surface-100">
                {{ project?.members_count || 0 }} 成员
              </span>
            </div>
          </div>
        </div>

        <div class="h-px bg-surface-200/60" />

        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 text-xs text-surface-600">
            <FileText class="h-4 w-4" />
            <span>项目描述</span>
          </div>
          <p class="text-sm leading-6 text-surface-700 dark:text-surface-200 whitespace-pre-wrap break-words">
            {{ displayText(project?.description, '暂无项目描述') }}
          </p>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import {
  ExternalLink,
  Users,
  CalendarDays,
  Clock3,
  Link2,
  FolderKanban,
  Boxes,
  FileText,
} from 'lucide-vue-next'
import { formatBackendDate } from '@/utils/datetime'
import IconButton from '@/components/ui/IconButton.vue'
import Card from 'primevue/card'

defineProps<{ project: any }>()

const openUrl = (url?: string) => {
  if (url) window.open(url, '_blank')
}

const displayText = (value: unknown, fallback: string = '-') => {
  const text = String(value ?? '').trim()
  return text || fallback
}
</script>
