<template>
  <div class="flex h-full flex-col overflow-hidden sidebar-shell">
    <div class="h-16 border-b border-surface-200/50 dark:border-surface-600/65">
      <div
        class="flex h-full items-center transition-all duration-300"
        :class="collapsed ? 'justify-center px-2' : 'px-6'"
      >
        <div class="flex items-center gap-3" :class="collapsed ? 'gap-0' : ''">
          <div class="review-logo-avatar">
            <img :src="reviewLogo" alt="AI CodeReview Logo" class="review-logo-image">
          </div>
          <div v-if="!collapsed" class="transition-opacity duration-200">
            <div class="whitespace-nowrap text-base font-semibold tracking-tight text-surface-900 dark:text-surface-0">AI CodeReview</div>
            <div class="whitespace-nowrap text-2xs text-surface-500 dark:text-surface-400">AI-Powered</div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto py-6 transition-all duration-300" :class="collapsed ? 'px-1.5' : 'px-4'">
      <Menu
        :model="groupedNavItems"
        :class="['sidebar-prime-menu', { 'is-collapsed': collapsed }]"
      >
        <template #submenuheader="{ item }">
          <div class="menu-group-label">
            <span class="menu-group-label-text">{{ item.label }}</span>
          </div>
        </template>
        <template #item="{ item }">
          <RouterLink :to="item.route as string" custom v-slot="{ href, navigate }">
            <a
              :href="href"
              v-tooltip.right="{ value: item.label, disabled: !collapsed, class: 'dashboard-compact-tooltip' }"
              class="group flex w-full items-center rounded-xl font-medium transition-all duration-200 sidebar-menu-item"
              :class="[
                collapsed ? 'justify-center px-2 py-3' : 'gap-3 px-4 py-3',
                isActive(item.route as string)
                  ? '!bg-primary !text-white shadow-lg shadow-primary/30'
                  : '!text-surface-600 hover:!bg-surface-100 hover:!text-surface-900 dark:!text-surface-300 dark:hover:!bg-surface-800 dark:hover:!text-surface-0'
              ]"
              @click="handleNavigate($event, navigate)"
              @keydown.enter.prevent="handleNavigate($event, navigate)"
              @keydown.space.prevent="handleNavigate($event, navigate)"
            >
              <component
                :is="item.iconComponent as unknown"
                class="h-5 w-5 flex-shrink-0 transition-transform duration-200"
                :class="isActive(item.route as string) ? '' : 'group-hover:scale-110'"
              />
              <span v-if="!collapsed" class="whitespace-nowrap">{{ item.label }}</span>
            </a>
          </RouterLink>
        </template>
      </Menu>
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
              <div class="whitespace-nowrap text-xs font-medium text-green-700 dark:text-green-300">系统运行中</div>
              <div class="whitespace-nowrap text-2xs text-green-600 dark:text-green-400">All systems operational</div>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import type { MenuItem } from 'primevue/menuitem'
import Tooltip from 'primevue/tooltip'
import Menu from 'primevue/menu'
import {
  LayoutDashboard,
  FileText,
  Settings,
  ScrollText,
  FolderKanban,
  BarChart3,
  CalendarRange,
  ListTodo,
} from 'lucide-vue-next'
import reviewLogo from '@/assets/icons/review-logo.webp'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

defineProps<{ collapsed?: boolean }>()
const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const vTooltip = Tooltip

interface SidebarMenuItem extends MenuItem {
  route: string
  label: string
  iconComponent: unknown
}

interface SidebarMenuGroup extends MenuItem {
  label: string
  items: SidebarMenuItem[]
}

const groupedNavItems: SidebarMenuGroup[] = [
  {
    label: '总览',
    items: [
      { route: '/dashboard', label: '仪表盘', iconComponent: LayoutDashboard },
    ],
  },
  {
    label: '代码审查',
    items: [
      { route: '/projects', label: '项目管理', iconComponent: FolderKanban },
      { route: '/reviews', label: '审查记录', iconComponent: FileText },
      { route: '/review-insights', label: '问题分析', iconComponent: BarChart3 },
      { route: '/issue-workbench', label: 'Issue 工作台', iconComponent: ListTodo },
      { route: '/weekly-feedback-report', label: '团队周报', iconComponent: CalendarRange },
    ],
  },
  {
    label: '系统',
    items: [
      { route: '/config', label: '配置管理', iconComponent: Settings },
      { route: '/logs', label: '日志监控', iconComponent: ScrollText },
    ],
  },
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
  display: flex;
  width: 100%;
  text-decoration: none !important;
}

.sidebar-prime-menu {
  border: 0 !important;
  background: transparent !important;
}

:deep(.sidebar-prime-menu.p-menu) {
  width: 100%;
  border: 0 !important;
  background: transparent !important;
  padding: 0 !important;
}

:deep(.sidebar-prime-menu .p-menu-list) {
  margin: 0;
  padding: 0;
  list-style: none;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

:deep(.sidebar-prime-menu .p-menu-submenu-label) {
  margin: 0;
  padding: 0;
}

:deep(.sidebar-prime-menu .p-menu-submenu-label:not(:first-child)) {
  margin-top: 0.875rem;
}

:deep(.sidebar-prime-menu.is-collapsed .p-menu-submenu-label) {
  display: none;
}

:deep(.sidebar-prime-menu.is-collapsed .p-menu-list) {
  gap: 0.25rem;
}

:deep(.sidebar-prime-menu .p-menu-item) {
  margin: 0;
  padding: 0;
}

:deep(.sidebar-prime-menu .p-menu-item-content) {
  border-radius: 0.75rem;
  background: transparent !important;
}

:deep(.sidebar-prime-menu .p-menu-item-content:hover) {
  background: transparent !important;
}

:deep(.sidebar-prime-menu .p-menu-item-link) {
  display: block;
  width: 100%;
  margin: 0;
  padding: 0;
  text-decoration: none;
  color: inherit;
}

:deep(.sidebar-prime-menu .p-menu-item-link:focus-visible) {
  outline: none;
}

.menu-group-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
  padding: 0 0.5rem;
}

.menu-group-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(148, 163, 184, 0.35);
}

.menu-group-label-text {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.375rem;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 1;
  color: var(--p-primary-color);
}

.dark .menu-group-label::after {
  background: rgba(100, 116, 139, 0.45);
}

.dark .menu-group-label-text {
  background: rgba(100, 116, 139, 0.2);
  color: var(--p-primary-color);
}

.status-tag {
  font-size: 10px;
  padding: 0.2rem 0.45rem;
}
</style>
