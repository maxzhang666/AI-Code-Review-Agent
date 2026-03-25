/**
 * API配置文件
 * 统一管理所有接口地址
 */

// API基础配置
export const API_CONFIG = {
  // 从环境变量获取基础URL
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api',

  // 超时时间
  TIMEOUT: 30000,

  // 请求头
  HEADERS: {
    'Content-Type': 'application/json'
  }
}

// 具体接口地址
export const API_ENDPOINTS = {
  // 统计数据
  STATISTICS: '/statistics',

  // 认证
  AUTH_LOGIN: '/auth/login',
  AUTH_LOGOUT: '/auth/logout',
  AUTH_ME: '/auth/me',
  AUTH_CHANGE_PASSWORD: '/auth/change-password',
  AUTH_USERS: '/auth/users/',
  AUTH_USER_STATUS: (id: string | number) => `/auth/users/${id}/status`,
  AUTH_USER_PASSWORD: (id: string | number) => `/auth/users/${id}/password`,

  // 审查记录
  REVIEWS: '/webhook/reviews/',
  REVIEW_DETAIL: (id: string) => `/webhook/reviews/${id}/`,
  REVIEW_FINDINGS: (id: string | number) => `/webhook/reviews/${id}/findings/`,
  REVIEW_FINDING_ACTIONS: (id: string | number) => `/webhook/review-findings/${id}/actions/`,
  REVIEW_FINDINGS_STATS: '/webhook/review-findings/stats/',
  MR_FEEDBACK_WEEKLY_REPORT: '/webhook/reports/mr-feedback/weekly/',
  DEVELOPER_WEEKLY_REPORT: '/webhook/reports/developers/weekly/',
  DEVELOPER_WEEKLY_CARDS: '/webhook/reports/developers/weekly/cards/',

  // 配置管理
  CONFIG: '/config/',
  CONFIG_SUMMARY: '/configs/summary/',
  CONFIG_BATCH_UPDATE: '/configs/batch_update/',
  NOTIFICATION_CHANNELS: '/notification-channels/',
  NOTIFICATION_CHANNEL_DETAIL: (id: string | number) => `/notification-channels/${id}/`,

  // 日志管理
  LOGS: '/webhook/logs/',

  // 系统信息
  SYSTEM_INFO: '/system/info',

  // 仪表盘
  DASHBOARD_STATS: '/webhook/dashboard/stats/',
  DASHBOARD_CHARTS: '/webhook/dashboard/charts/',

  // Webhook测试
  WEBHOOK_TEST: '/test/webhook',

  // 项目管理
  PROJECTS: '/webhook/projects/',
  PROJECT_DETAIL: (id: string | number) => `/webhook/projects/${id}/`,
  PROJECT_ENABLE: (id: string | number) => `/webhook/projects/${id}/enable/`,
  PROJECT_DISABLE: (id: string | number) => `/webhook/projects/${id}/disable/`,
  PROJECT_UPDATE: (id: string | number) => `/webhook/projects/${id}/update/`,
  PROJECT_STATS: '/webhook/projects/stats/',
  PROJECT_WEBHOOK_LOGS: (id: string | number) => `/webhook/projects/${id}/webhook-logs/`,
  PROJECT_REVIEW_HISTORY: (id: string | number) => `/webhook/projects/${id}/review-history/`,
  PROJECT_STATS_DETAIL: (id: string | number) => `/webhook/projects/${id}/stats/`,
  PROJECT_NOTIFICATIONS: (id: string | number) => `/webhook/projects/${id}/notifications/`,
  PROJECT_NOTIFICATIONS_UPDATE: (id: string | number) => `/webhook/projects/${id}/notifications/update/`,

  // GitLab Webhook
  GITLAB_WEBHOOK: '/webhook/gitlab/',

  // LLM Provider
  LLM_PROVIDERS: '/llm-configs/',
  LLM_PROVIDER_DETAIL: (id: string | number) => `/llm-configs/${id}/`,
  LLM_PROVIDER_ACTIVATE: (id: string | number) => `/llm-configs/${id}/activate/`,
  LLM_PROVIDER_FETCH_MODELS: '/llm-configs/fetch-models/',
  LLM_PROVIDER_TEST_CONNECTION: '/llm-configs/test-connection/',

  // GitLab Project Import
  GITLAB_PROJECT_SEARCH: '/webhook/projects/gitlab-search/',
  PROJECTS_IMPORT: '/webhook/projects/import/',

  // System Configs
  SYSTEM_CONFIGS: '/system/configs/',
}

// 完整URL生成函数
export const getApiUrl = (endpoint: string): string => {
  if (/^https?:\/\//.test(endpoint)) {
    return endpoint
  }

  const baseUrl = (API_CONFIG.BASE_URL || '').replace(/\/+$/, '')
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  if (!baseUrl) {
    return normalizedEndpoint
  }

  return `${baseUrl}${normalizedEndpoint}`
}

// 通用API URL集合（包含完整路径）
export const API_URLS = {
  STATISTICS: getApiUrl(API_ENDPOINTS.STATISTICS),
  REVIEWS: getApiUrl(API_ENDPOINTS.REVIEWS),
  CONFIG: getApiUrl(API_ENDPOINTS.CONFIG),
  LOGS: getApiUrl(API_ENDPOINTS.LOGS),
  SYSTEM_INFO: getApiUrl(API_ENDPOINTS.SYSTEM_INFO),
  WEBHOOK_TEST: getApiUrl(API_ENDPOINTS.WEBHOOK_TEST),
  PROJECTS: getApiUrl(API_ENDPOINTS.PROJECTS),
  PROJECT_STATS: getApiUrl(API_ENDPOINTS.PROJECT_STATS),
  GITLAB_WEBHOOK: getApiUrl(API_ENDPOINTS.GITLAB_WEBHOOK)
}
