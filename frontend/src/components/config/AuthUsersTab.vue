<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">账号管理</h3>
              <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">管理员可创建用户、启停账号并重置密码。</p>
            </div>
            <Button text size="small" :loading="loadingUsers" @click="loadUsers">
              刷新
            </Button>
          </div>

          <div
            v-if="forbidden"
            class="rounded-xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/45 dark:bg-amber-500/10 dark:text-amber-200"
          >
            当前账号不是管理员，无法管理其他用户。
          </div>

          <div
            v-else-if="users.length === 0"
            class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-6 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/50 dark:text-surface-400"
          >
            还没有可管理的账号。
          </div>

          <div v-else class="overflow-x-auto rounded-xl border border-surface-200 dark:border-surface-700">
            <table class="min-w-full divide-y divide-surface-200 text-sm dark:divide-surface-700">
              <thead class="bg-surface-50 text-left text-xs uppercase tracking-wide text-surface-500 dark:bg-surface-800/60 dark:text-surface-400">
                <tr>
                  <th class="px-4 py-3">用户名</th>
                  <th class="px-4 py-3">角色</th>
                  <th class="px-4 py-3">状态</th>
                  <th class="px-4 py-3">最近登录</th>
                  <th class="px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-surface-100 bg-white dark:divide-surface-800 dark:bg-surface-900/40">
                <tr v-for="user in users" :key="user.id">
                  <td class="px-4 py-3 font-medium text-surface-900 dark:text-surface-100">
                    <div class="flex items-center gap-2">
                      <span>{{ user.username }}</span>
                      <Tag v-if="isCurrentUser(user)" severity="info">当前</Tag>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-surface-600 dark:text-surface-300">
                    <Tag :severity="user.is_admin ? 'success' : 'secondary'">
                      {{ user.is_admin ? '管理员' : '普通用户' }}
                    </Tag>
                  </td>
                  <td class="px-4 py-3 text-surface-600 dark:text-surface-300">
                    <Tag :severity="user.is_active ? 'success' : 'danger'">
                      {{ user.is_active ? '启用' : '禁用' }}
                    </Tag>
                  </td>
                  <td class="px-4 py-3 text-surface-500 dark:text-surface-400">
                    {{ formatDateTime(user.last_login_at) }}
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap items-center gap-2">
                      <Button severity="danger"
                        v-if="user.is_active"
                        size="small"
                        text
                        :loading="statusUpdatingUserId === user.id"
                        @click="toggleUserStatus(user)"
                      >
                        禁用
                      </Button>
                      <Button
                        v-else
                        size="small"
                        text
                        :loading="statusUpdatingUserId === user.id"
                        @click="toggleUserStatus(user)"
                      >
                        启用
                      </Button>
                      <Button
                        size="small"
                        outlined
                        :loading="passwordResettingUserId === user.id"
                        @click="openResetPasswordPrompt(user)"
                      >
                        重置密码
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="!forbidden" class="rounded-xl border border-surface-200 bg-surface-50/60 p-4 dark:border-surface-700 dark:bg-surface-800/40">
            <h4 class="mb-3 text-sm font-semibold text-surface-900 dark:text-surface-100">创建账号</h4>
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <InputText v-model="createForm.username" placeholder="用户名" />
              <InputText
                v-model="createForm.password"
                type="password"
                autocomplete="new-password"
                placeholder="初始密码（至少8位）"
              />
              <label class="inline-flex items-center gap-2 text-sm text-surface-700 dark:text-surface-200">
                <Checkbox v-model="createForm.is_admin" binary />
                管理员账号
              </label>
              <label class="inline-flex items-center gap-2 text-sm text-surface-700 dark:text-surface-200">
                <Checkbox v-model="createForm.is_active" binary />
                创建后立即启用
              </label>
            </div>
            <div class="mt-4">
              <Button :loading="creatingUser" @click="createUser" size="small">创建账号</Button>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">修改我的密码</h3>
            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">修改后请使用新密码重新登录。</p>
          </div>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
            <InputText
              v-model="changePasswordForm.oldPassword"
              type="password"
              autocomplete="current-password"
              placeholder="当前密码"
            />
            <InputText
              v-model="changePasswordForm.newPassword"
              type="password"
              autocomplete="new-password"
              placeholder="新密码（至少8位）"
            />
            <InputText
              v-model="changePasswordForm.confirmPassword"
              type="password"
              autocomplete="new-password"
              placeholder="确认新密码"
            />
          </div>
          <div>
            <Button :loading="changingPassword" @click="changeMyPassword" size="small">
              修改密码
            </Button>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  changeMyPassword as changeMyPasswordApi,
  createAuthUser,
  getAuthUsers,
  resetAuthUserPassword,
  updateAuthUserStatus
} from '@/api'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

interface AuthUserItem {
  id: number
  username: string
  is_admin: boolean
  is_active: boolean
  last_login_at: string | null
}

const router = useRouter()
const auth = useAuthStore()
const users = ref<AuthUserItem[]>([])
const loadingUsers = ref(false)
const forbidden = ref(false)
const creatingUser = ref(false)
const statusUpdatingUserId = ref<number | null>(null)
const passwordResettingUserId = ref<number | null>(null)
const changingPassword = ref(false)

const createForm = ref({
  username: '',
  password: '',
  is_admin: false,
  is_active: true
})

const changePasswordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const isCurrentUser = (user: AuthUserItem) => user.username === auth.username

const formatDateTime = (raw: string | null) => {
  if (!raw) return '从未登录'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  return parsed.toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const response = await getAuthUsers()
    users.value = Array.isArray(response) ? response : []
    forbidden.value = false
  } catch (error: any) {
    if (error?.response?.status === 403) {
      forbidden.value = true
      users.value = []
      return
    }
    toast.error(error?.response?.data?.detail || '加载账号列表失败')
  } finally {
    loadingUsers.value = false
  }
}

const createUser = async () => {
  const username = createForm.value.username.trim()
  const password = createForm.value.password.trim()
  if (!username) {
    toast.warning('请输入用户名')
    return
  }
  if (password.length < 8) {
    toast.warning('密码长度至少为 8 位')
    return
  }

  creatingUser.value = true
  try {
    await createAuthUser({
      username,
      password,
      is_admin: createForm.value.is_admin,
      is_active: createForm.value.is_active
    })
    toast.success('账号创建成功')
    createForm.value = { username: '', password: '', is_admin: false, is_active: true }
    await loadUsers()
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '创建账号失败')
  } finally {
    creatingUser.value = false
  }
}

const toggleUserStatus = async (user: AuthUserItem) => {
  statusUpdatingUserId.value = user.id
  try {
    await updateAuthUserStatus(user.id, !user.is_active)
    toast.success(!user.is_active ? '账号已启用' : '账号已禁用')
    await loadUsers()
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '更新账号状态失败')
  } finally {
    statusUpdatingUserId.value = null
  }
}

const openResetPasswordPrompt = async (user: AuthUserItem) => {
  const nextPassword = window.prompt(`请为账号「${user.username}」设置新密码（至少8位）`, '')
  if (!nextPassword) return
  if (nextPassword.trim().length < 8) {
    toast.warning('密码长度至少为 8 位')
    return
  }

  passwordResettingUserId.value = user.id
  try {
    await resetAuthUserPassword(user.id, nextPassword.trim())
    toast.success('密码重置成功')
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '密码重置失败')
  } finally {
    passwordResettingUserId.value = null
  }
}

const changeMyPassword = async () => {
  const { oldPassword, newPassword, confirmPassword } = changePasswordForm.value
  if (!oldPassword.trim() || !newPassword.trim()) {
    toast.warning('请填写完整的密码信息')
    return
  }
  if (newPassword.trim().length < 8) {
    toast.warning('新密码长度至少为 8 位')
    return
  }
  if (newPassword !== confirmPassword) {
    toast.warning('两次输入的新密码不一致')
    return
  }

  changingPassword.value = true
  try {
    await changeMyPasswordApi(oldPassword.trim(), newPassword.trim())
    toast.success('密码修改成功，请重新登录')
    changePasswordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    auth.logout()
    await router.push('/login')
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '修改密码失败')
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  void loadUsers()
})
</script>
