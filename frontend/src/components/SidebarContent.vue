<template>
  <div class="flex flex-col h-full overflow-hidden sidebar-shell">
    <Card class="sidebar-card logo-card" :pt="{ body: { class: 'p-0' }, content: { class: 'p-0' } }">
      <template #content>
        <div class="border-b border-surface-200/50 dark:border-surface-600/65">
          <div
            class="flex h-16 items-center transition-all duration-300"
            :class="collapsed ? 'px-2 justify-center' : 'px-6'"
          >
            <div class="flex items-center gap-3" :class="collapsed ? 'gap-0' : ''">
              <div class="review-logo-avatar">
                <img :src="reviewLogo" alt="AI CodeReview Logo" class="review-logo-image">
              </div>
              <div v-if="!collapsed" class="transition-opacity duration-200">
                <div class="text-base font-semibold text-surface-900 tracking-tight whitespace-nowrap dark:text-surface-0">AI CodeReview</div>
                <div class="text-2xs text-surface-500 whitespace-nowrap dark:text-surface-400">AI-Powered</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <div class="flex-1 py-6 overflow-y-auto transition-all duration-300" :class="collapsed ? 'px-1.5' : 'px-4'">
      <nav class="flex flex-col gap-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.route"
          :to="item.route"
          custom
          v-slot="{ href, navigate }"
        >
          <a
            :href="href"
            v-tooltip.right="{ value: item.label, disabled: !collapsed, class: 'dashboard-compact-tooltip' }"
            class="group flex items-center w-full rounded-xl font-medium transition-all duration-200 sidebar-menu-item"
            :class="[
              collapsed ? 'justify-center py-3 px-2' : 'gap-3 px-4 py-3',
              isActive(item.route)
                ? '!bg-primary !text-white shadow-lg shadow-primary/30'
                : '!text-surface-600 hover:!bg-surface-100 hover:!text-surface-900 dark:!text-surface-300 dark:hover:!bg-surface-800 dark:hover:!text-surface-0'
            ]"
            @click="handleNavigate($event, navigate)"
          >
            <component
              :is="item.iconComponent"
              class="w-5 h-5 flex-shrink-0 transition-transform duration-200"
              :class="isActive(item.route) ? '' : 'group-hover:scale-110'"
            />
            <span v-if="!collapsed" class="whitespace-nowrap">{{ item.label }}</span>
          </a>
        </RouterLink>
      </nav>
    </div>

    <Card class="sidebar-card status-card" :pt="{ body: { class: 'p-0' }, content: { class: 'p-0' } }">
      <template #content>
        <div class="border-t border-surface-200/50 transition-all duration-300" :class="collapsed ? 'p-2' : 'p-4'">
          <div
            class="flex items-center rounded-xl bg-green-50 transition-all duration-300 dark:bg-green-500/12"
            :class="collapsed ? 'justify-center px-2 py-3' : 'gap-3 px-4 py-3'"
          >
            <Tag severity="success" rounded class="status-tag">运行中</Tag>
            <div v-if="!collapsed" class="flex-1 transition-opacity duration-200">
              <div class="text-xs font-medium text-green-700 whitespace-nowrap dark:text-green-300">系统运行中</div>
              <div class="text-2xs text-green-600 whitespace-nowrap dark:text-green-400">All systems operational</div>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import Tooltip from 'primevue/tooltip'
import {
  LayoutDashboard,
  FileText,
  Settings,
  ScrollText,
  FolderKanban,
  BarChart3,
} from 'lucide-vue-next'
import reviewLogo from '@/assets/icons/review-logo.webp'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

defineProps<{ collapsed?: boolean }>()
const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const vTooltip = Tooltip

interface SidebarMenuItem {
  route: string
  label: string
  iconComponent: any
}

const navItems: SidebarMenuItem[] = [
  { route: '/dashboard', label: '仪表盘', iconComponent: LayoutDashboard },
  { route: '/projects', label: '项目管理', iconComponent: FolderKanban },
  { route: '/reviews', label: '审查记录', iconComponent: FileText },
  { route: '/review-insights', label: '问题分析', iconComponent: BarChart3 },
  { route: '/config', label: '配置管理', iconComponent: Settings },
  { route: '/logs', label: '日志监控', iconComponent: ScrollText },
]

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')

const handleNavigate = (
  event: Event,
  navigate: (event?: MouseEvent) => void | Promise<unknown>
) => {
  navigate(event as MouseEvent)
  emit('navigate')
}
</script>

<style scoped>
.sidebar-card {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}

.logo-card,
.status-card {
  flex-shrink: 0;
}

.review-logo-avatar {
  width: 2.5rem;
  height: 2.5rem;
  display: inline-flex;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: 1rem;
  box-shadow: 0 8px 18px rgba(0, 122, 255, 0.2);
}

.review-logo-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sidebar-menu-item {
  text-decoration: none !important;
}

.status-tag {
  font-size: 10px;
  padding: 0.2rem 0.45rem;
}
</style>
