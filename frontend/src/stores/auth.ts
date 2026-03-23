import { defineStore } from 'pinia'
import axios from 'axios'
import { API_ENDPOINTS, getApiUrl } from '@/config/api'

export const AUTH_LOCAL_STORAGE_KEY = 'crg_auth_local_session'
export const AUTH_SESSION_STORAGE_KEY = 'crg_auth_session'

interface AuthSessionSnapshot {
  username: string
  token: string
  remember: boolean
  logged_in_at: string
}

interface LoginPayload {
  username: string
  password: string
  remember: boolean
}

interface LoginResult {
  ok: boolean
  message?: string
}

interface LoginApiResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: {
    id: number
    username: string
    is_admin: boolean
    is_active: boolean
  }
}

function canUseStorage() {
  return typeof window !== 'undefined'
}

function parseSessionSnapshot(raw: string | null): AuthSessionSnapshot | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Partial<AuthSessionSnapshot>
    if (typeof parsed.username !== 'string' || !parsed.username.trim()) return null
    if (typeof parsed.token !== 'string' || !parsed.token.trim()) return null
    return {
      username: parsed.username.trim(),
      token: parsed.token.trim(),
      remember: Boolean(parsed.remember),
      logged_in_at: typeof parsed.logged_in_at === 'string' ? parsed.logged_in_at : new Date().toISOString()
    }
  } catch (error) {
    return null
  }
}

function readPersistedSession(): AuthSessionSnapshot | null {
  if (!canUseStorage()) return null
  const local = parseSessionSnapshot(localStorage.getItem(AUTH_LOCAL_STORAGE_KEY))
  if (local) return local
  return parseSessionSnapshot(sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY))
}

export function clearPersistedSession() {
  if (!canUseStorage()) return
  localStorage.removeItem(AUTH_LOCAL_STORAGE_KEY)
  sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY)
}

function writePersistedSession(snapshot: AuthSessionSnapshot) {
  if (!canUseStorage()) return
  clearPersistedSession()
  if (snapshot.remember) {
    localStorage.setItem(AUTH_LOCAL_STORAGE_KEY, JSON.stringify(snapshot))
    return
  }
  sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(snapshot))
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    username: null as string | null,
    token: null as string | null,
    remember: false,
    hydrated: false
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.username && state.token)
  },
  actions: {
    hydrate() {
      if (this.hydrated) return
      const session = readPersistedSession()
      if (session) {
        this.username = session.username
        this.token = session.token
        this.remember = session.remember
      }
      this.hydrated = true
    },
    async login(payload: LoginPayload): Promise<LoginResult> {
      const username = payload.username.trim()
      const password = payload.password.trim()
      if (!username) return { ok: false, message: '请输入账号' }
      if (!password) return { ok: false, message: '请输入密码' }

      try {
        const response = await axios.post<LoginApiResponse>(
          getApiUrl(API_ENDPOINTS.AUTH_LOGIN),
          { username, password },
          { timeout: 15000 }
        )
        const data = response.data
        if (!data?.access_token || !data?.user?.username) {
          return { ok: false, message: '登录响应异常，请稍后重试' }
        }

        const snapshot: AuthSessionSnapshot = {
          username: data.user.username,
          token: data.access_token,
          remember: payload.remember,
          logged_in_at: new Date().toISOString()
        }
        this.username = snapshot.username
        this.token = snapshot.token
        this.remember = snapshot.remember
        writePersistedSession(snapshot)
        return { ok: true }
      } catch (error: any) {
        const message = error?.response?.data?.detail || error?.response?.data?.message || '登录失败，请检查账号或密码'
        return { ok: false, message }
      }
    },
    logout() {
      this.username = null
      this.token = null
      this.remember = false
      clearPersistedSession()
    }
  }
})
