import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { getActivePinia } from 'pinia'
import { API_CONFIG } from '@/config/api'
import router from '@/router'
import { clearPersistedSession, useAuthStore } from '@/stores/auth'
import { toast } from './toast'

const service: AxiosInstance = axios.create({
  timeout: API_CONFIG.TIMEOUT,
  headers: API_CONFIG.HEADERS
})

let handlingUnauthorized = false

const resolveRedirectPath = (): string => {
  const { fullPath } = router.currentRoute.value
  if (typeof fullPath !== 'string' || !fullPath.startsWith('/') || fullPath.startsWith('//')) {
    return '/dashboard'
  }
  return fullPath
}

const handleUnauthorized = async (): Promise<void> => {
  if (handlingUnauthorized) return
  handlingUnauthorized = true

  try {
    clearPersistedSession()
    const pinia = getActivePinia()
    if (pinia) {
      const auth = useAuthStore(pinia)
      auth.logout()
    }

    if (router.currentRoute.value.path !== '/login') {
      await router.push({
        path: '/login',
        query: { redirect: resolveRedirectPath() }
      })
    }
  } catch (error) {
    console.error('Unauthorized handler error:', error)
  } finally {
    // 稍作延迟，避免并发 401 触发重复跳转
    window.setTimeout(() => {
      handlingUnauthorized = false
    }, 300)
  }
}

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const pinia = getActivePinia()
    if (pinia) {
      const auth = useAuthStore(pinia)
      if (auth.token) {
        config.headers = config.headers ?? {}
        if (!config.headers.Authorization) {
          config.headers.Authorization = `Bearer ${auth.token}`
        }
      }
    }
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data, status } = response

    // 2xx 状态码都认为是成功
    if (status >= 200 && status < 300) {
      return data
    }

    toast.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message || 'Error'))
  },
  (error) => {
    console.error('Response error:', error)

    if (error.response) {
      const { status } = error.response
      switch (status) {
        case 401:
          if (!handlingUnauthorized) {
            toast.error('登录状态已失效，请重新登录')
          }
          void handleUnauthorized()
          break
        case 403:
          toast.error('拒绝访问')
          break
        case 404:
          toast.warning('请求地址不存在')
          break
        case 500:
          toast.error('服务器内部错误')
          break
        default:
          toast.error(error.response.data?.message || '请求失败')
      }
    } else {
      toast.error('网络连接失败')
    }

    return Promise.reject(error)
  }
)

const request = <T = any>(config: AxiosRequestConfig): Promise<T> => {
  return service.request<any, T>(config)
}

export default request
