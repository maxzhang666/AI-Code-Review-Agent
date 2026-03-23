<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <div class="flex items-center gap-3">
          <div class="w-2 h-2 bg-primary rounded-full"></div>
          <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">项目信息</h3>
        </div>

        <dl class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">项目名称</dt>
            <dd class="mt-1 edium text-surface-900 dark:text-surface-100 break-all">{{ project?.project_name || '-' }}</dd>
          </div>
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">命名空间</dt>
            <dd class="mt-1 text-surface-800 dark:text-surface-200 break-all">{{ project?.namespace || '-' }}</dd>
          </div>
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 md:col-span-2 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">项目地址</dt>
            <dd class="mt-1 flex items-center gap-2">
              <span class="flex-1 truncate rimary-600">{{ project?.project_url || '-' }}</span>
              <IconButton size="small" aria-label="打开项目地址" @click="openUrl(project?.project_url)">
                <ExternalLink class="w-4 h-4" />
              </IconButton>
            </dd>
          </div>
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">创建时间</dt>
            <dd class="mt-1 text-surface-800 dark:text-surface-200">{{ project?.created_at ? formatBackendDate(project.created_at) : '未知' }}</dd>
          </div>
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">最后活动</dt>
            <dd class="mt-1 text-surface-800 dark:text-surface-200">{{ project?.last_activity || '未知' }}</dd>
          </div>
          <div class="rounded-xl border border-surface-200/60 bg-surface-50/40 p-3 md:col-span-2 dark:border-surface-700/60 dark:bg-surface-800/40">
            <dt class="text-xs font-medium uppercase tracking-wide text-surface-500">团队成员</dt>
            <dd class="mt-1 inline-flex items-center gap-2 text-surface-800 dark:text-surface-200">
              <Users class="w-4 h-4 text-surface-600 dark:text-surface-400" />
              <span>{{ project?.members_count || 0 }} 成员</span>
            </dd>
          </div>
        </dl>

        <div class="border-t border-surface-200/50 pt-6 dark:border-surface-700/60">
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-surface-600 dark:text-surface-300">项目描述</div>
          <p class="text-surface-700 dark:text-surface-200">{{ project?.description || '暂无项目描述' }}</p>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ExternalLink, Users } from 'lucide-vue-next'
import { formatBackendDate } from '@/utils/datetime'
import IconButton from '@/components/ui/IconButton.vue'
import Card from 'primevue/card'

defineProps<{ project: any }>()

const openUrl = (url?: string) => {
  if (url) window.open(url, '_blank')
}
</script>
