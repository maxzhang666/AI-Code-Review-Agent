<template>
  <div class="min-h-screen bg-surface-50 dark:bg-surface-950">
    <!-- Sidebar - Desktop -->
    <aside
      class="hidden lg:block fixed top-0 start-0 bottom-0 z-[60] bg-white/80 backdrop-blur-2xl border-r border-surface-200/50 transition-all duration-300 ease-in-out dark:bg-surface-900/88 dark:border-surface-600/65"
      :class="sidebarCollapsed ? 'w-16' : 'w-72'"
    >
      <SidebarContent :collapsed="sidebarCollapsed" />
    </aside>

    <!-- Sidebar - Mobile Drawer -->
    <Drawer
      v-model:visible="mobileMenuVisible"
      position="left"
      :modal="true"
      :dismissable="true"
      :block-scroll="true"
      :show-close-icon="false"
      class="lg:hidden"
      :pt="{
        root: { class: 'w-72 max-w-[90vw] border-r border-surface-200/50 bg-white/95 backdrop-blur-xl dark:border-surface-600/65 dark:bg-surface-900/95' },
        content: { class: 'p-0' },
        mask: { class: 'bg-slate-900/25 backdrop-blur-[1px]' }
      }"
    >
      <SidebarContent @navigate="mobileMenuVisible = false" />
    </Drawer>

    <!-- Content -->
    <div
      class="transition-all duration-300 ease-in-out min-h-screen"
      :class="sidebarCollapsed ? 'lg:ps-16' : 'lg:ps-72'"
    >
      <!-- Header -->
      <header class="sticky top-0 z-40 bg-white/80 backdrop-blur-2xl border-b border-surface-200/50 dark:bg-surface-900/88 dark:border-surface-600/65">
        <div class="flex items-center justify-between h-16 px-6">
          <div class="flex items-center gap-4">
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-surface-500 transition-colors duration-200 hover:bg-surface-100 hover:text-surface-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-surface-0"
              aria-label="切换侧边栏"
              @click="toggleSidebar"
            >
              <component :is="sidebarIcon" class="h-5 w-5" />
            </button>

            <div class="flex flex-col justify-center">
              <h1 class="text-lg font-semibold text-surface-900 tracking-tight leading-tight dark:text-surface-0">{{ currentTitle }}</h1>
              <p class="text-2xs text-surface-500 leading-tight dark:text-surface-400">{{ currentTime }}</p>
            </div>
          </div>

          <div class="flex items-center gap-1">
            <span
              v-tooltip.bottom="{
                value: isDarkMode ? '切换到浅色模式' : '切换到深色模式',
                class: 'dashboard-compact-tooltip'
              }"
              class="inline-flex"
            >
              <button
                type="button"
                class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-surface-500 transition-colors duration-200 hover:bg-surface-100 hover:text-surface-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-surface-0"
                aria-label="切换主题"
                @click="toggleTheme"
              >
                <Moon v-if="!isDarkMode" class="h-5 w-5" />
                <Sun v-else class="h-5 w-5" />
              </button>
            </span>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-surface-500 transition-colors duration-200 hover:bg-surface-100 hover:text-surface-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-surface-0"
              aria-label="刷新页面"
              @click="handleRefresh"
            >
              <RefreshCw class="h-5 w-5" />
            </button>
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-surface-500 transition-colors duration-200 hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-400 focus-visible:outline-offset-2 dark:text-surface-300 dark:hover:bg-red-500/15 dark:hover:text-red-300"
              aria-label="退出登录"
              @click="handleLogout"
            >
              <LogOut class="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <main class="p-6 lg:p-8">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="viewKey" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Tooltip from 'primevue/tooltip'
import { LogOut, Menu as MenuIcon, RefreshCw, PanelLeftClose, PanelLeftOpen, Sun, Moon } from 'lucide-vue-next'
import SidebarContent from '@/components/SidebarContent.vue'
import Drawer from 'primevue/drawer'
import { useAuthStore } from '@/stores/auth'

type ThemeMode = 'light' | 'dark'
const THEME_STORAGE_KEY = 'ui-theme-mode'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const vTooltip = Tooltip
const mobileMenuVisible = ref(false)
const sidebarCollapsed = ref(false)
const viewKey = ref(0)
const isMobile = ref(false)
const isDarkMode = ref(false)

const updateIsMobile = () => {
  isMobile.value = window.innerWidth < 1024
}

const sidebarIcon = computed(() => {
  if (isMobile.value) return MenuIcon
  return sidebarCollapsed.value ? PanelLeftOpen : PanelLeftClose
})

const currentTitle = computed(() => {
  return route.meta.title || '项目管理'
})

const formatTime = () => {
  return new Date().toLocaleString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const currentTime = ref(formatTime())
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  const storedMode = localStorage.getItem(THEME_STORAGE_KEY)
  if (storedMode === 'light' || storedMode === 'dark') {
    applyThemeMode(storedMode)
  } else {
    const preferredMode: ThemeMode = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    applyThemeMode(preferredMode)
  }
  timer = setInterval(() => {
    currentTime.value = formatTime()
  }, 60_000)
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', updateIsMobile)
})

const toggleSidebar = () => {
  if (window.innerWidth >= 1024) {
    sidebarCollapsed.value = !sidebarCollapsed.value
  } else {
    mobileMenuVisible.value = true
  }
}

const handleRefresh = () => {
  viewKey.value++
}

const handleLogout = async () => {
  auth.logout()
  await router.push('/login')
}

const applyThemeMode = (mode: ThemeMode) => {
  const isDark = mode === 'dark'
  isDarkMode.value = isDark
  document.documentElement.classList.toggle('dark', isDark)
}

const toggleTheme = () => {
  const nextMode: ThemeMode = isDarkMode.value ? 'light' : 'dark'
  applyThemeMode(nextMode)
  localStorage.setItem(THEME_STORAGE_KEY, nextMode)
}

watch(() => route.path, () => {
  mobileMenuVisible.value = false
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
