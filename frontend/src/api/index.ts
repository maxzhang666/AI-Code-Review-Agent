import request from '@/utils/request'
import { API_ENDPOINTS, getApiUrl } from '@/config/api'

// 统计数据
export const getStatistics = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.STATISTICS),
    method: 'get'
  })
}

export const getDashboardStats = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.DASHBOARD_STATS),
    method: 'get'
  })
}

export const getDashboardCharts = (days: number = 7) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.DASHBOARD_CHARTS),
    method: 'get',
    params: { days }
  })
}

// 审查记录列表
export const getReviews = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEWS),
    method: 'get',
    params
  })
}

// 审查详情
export const getReviewDetail = (id: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_DETAIL(id)),
    method: 'get'
  })
}

export const getReviewFindings = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDINGS(id)),
    method: 'get'
  })
}

export const getReviewFindingsList = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDINGS_LIST),
    method: 'get',
    params
  })
}

export const createReviewFindingAction = (
  id: string | number,
  data: {
    action_type: 'fixed' | 'ignored' | 'todo' | 'reopened'
    actor?: string
    note?: string
    ignore_reason_code?: 'business_exception' | 'historical_debt' | 'rule_false_positive' | 'defer_fix' | 'duplicate' | 'other'
    ignore_reason_note?: string
  }
) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDING_ACTIONS(id)),
    method: 'post',
    data
  })
}

export const createReviewFindingActionsBatch = (data: {
  finding_ids: number[]
  action_type: 'fixed' | 'ignored' | 'todo' | 'reopened'
  actor?: string
  note?: string
  ignore_reason_code?: 'business_exception' | 'historical_debt' | 'rule_false_positive' | 'defer_fix' | 'duplicate' | 'other'
  ignore_reason_note?: string
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDING_ACTIONS_BATCH),
    method: 'post',
    data
  })
}

export const getReviewFindingActions = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDING_ACTIONS(id)),
    method: 'get'
  })
}

export const getReviewFindingsStats = (params?: {
  days?: number
  project_id?: number
  owner?: string
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.REVIEW_FINDINGS_STATS),
    method: 'get',
    params
  })
}

export const getMRFeedbackWeeklyReport = (params?: {
  project_id?: number
  anchor_date?: string
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.MR_FEEDBACK_WEEKLY_REPORT),
    method: 'get',
    params
  })
}

export const getDeveloperWeeklyReport = (params?: {
  owner?: string
  owner_email?: string
  anchor_date?: string
  include_statuses?: string[]
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.DEVELOPER_WEEKLY_REPORT),
    method: 'get',
    params
  })
}

export const getDeveloperWeeklyCards = (params?: {
  anchor_date?: string
  limit?: number
  include_statuses?: string[]
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.DEVELOPER_WEEKLY_CARDS),
    method: 'get',
    params
  })
}

export const getProjectIgnoreStrategies = (params: {
  project_id: number | string
  statuses?: string[]
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.IGNORE_STRATEGIES),
    method: 'get',
    params
  })
}

export const disableProjectIgnoreStrategy = (
  strategyId: number | string,
  data?: {
    reason?: string
  }
) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.IGNORE_STRATEGY_DISABLE(strategyId)),
    method: 'patch',
    data
  })
}

export const disableAllProjectIgnoreStrategies = (data: {
  project_id: number | string
  reason?: string
}) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.IGNORE_STRATEGIES_DISABLE_ALL),
    method: 'post',
    data
  })
}

// 配置信息
export const getConfig = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.CONFIG),
    method: 'get'
  })
}

// 更新配置
export const updateConfig = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.CONFIG),
    method: 'post',
    data
  })
}

// 获取配置摘要
export const getConfigSummary = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.CONFIG_SUMMARY),
    method: 'get'
  })
}

// 批量更新配置
export const batchUpdateConfig = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.CONFIG_BATCH_UPDATE),
    method: 'post',
    data
  })
}

// 账号管理 - 获取用户列表（管理员）
export const getAuthUsers = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.AUTH_USERS),
    method: 'get'
  })
}

// 账号管理 - 创建用户（管理员）
export const createAuthUser = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.AUTH_USERS),
    method: 'post',
    data
  })
}

// 账号管理 - 更新用户启用状态（管理员）
export const updateAuthUserStatus = (id: string | number, isActive: boolean) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.AUTH_USER_STATUS(id)),
    method: 'patch',
    data: { is_active: isActive }
  })
}

// 账号管理 - 重置用户密码（管理员）
export const resetAuthUserPassword = (id: string | number, newPassword: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.AUTH_USER_PASSWORD(id)),
    method: 'patch',
    data: { new_password: newPassword }
  })
}

// 账号管理 - 当前用户修改密码
export const changeMyPassword = (oldPassword: string, newPassword: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.AUTH_CHANGE_PASSWORD),
    method: 'post',
    data: { old_password: oldPassword, new_password: newPassword }
  })
}

// 通知通道列表
export const getNotificationChannels = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.NOTIFICATION_CHANNELS),
    method: 'get',
    params
  })
}

// 创建通知通道
export const createNotificationChannel = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.NOTIFICATION_CHANNELS),
    method: 'post',
    data
  })
}

// 更新通知通道
export const updateNotificationChannel = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.NOTIFICATION_CHANNEL_DETAIL(id)),
    method: 'patch',
    data
  })
}

// 删除通知通道
export const deleteNotificationChannel = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.NOTIFICATION_CHANNEL_DETAIL(id)),
    method: 'delete'
  })
}

// 测试通知渠道
export const testNotificationChannel = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.NOTIFICATION_CHANNEL_DETAIL(id) + 'test/'),
    method: 'post'
  })
}

// 日志列表
export const getLogs = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LOGS),
    method: 'get',
    params
  })
}

// 系统日志文件列表
export const getSystemLogFiles = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_LOG_FILES),
    method: 'get',
  })
}

// 系统日志文件内容
export const getSystemLogFileContent = (filename: string, lines: number = 300) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_LOG_FILE_CONTENT),
    method: 'get',
    params: { filename, lines },
  })
}

// 系统信息
export const getSystemInfo = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_INFO),
    method: 'get'
  })
}

export type SystemTaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'retrying' | string

export interface SystemTaskSummaryResponse {
  queue_backend?: string
  is_persistent?: boolean
  observability_persistent?: boolean | null
  by_status?: Record<string, number>
  by_task_type?: Record<string, number>
}

export interface SystemTaskObservationItem {
  task_id: string
  run_id?: string | null
  task_type?: string
  status?: SystemTaskStatus
  priority?: string
  retry_count?: number
  max_retries?: number
  payload?: Record<string, any> | null
  result?: Record<string, any> | null
  error_message?: string | null
  created_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  updated_at?: string | null
  duration_ms?: number | null
}

export interface SystemTaskListParams {
  page?: number
  limit?: number
  status?: string
  task_type?: string
  task_id?: string
  run_id?: string
  created_from?: string
  created_to?: string
}

export interface SystemTaskListResponse {
  count: number
  results: SystemTaskObservationItem[]
}

export interface SystemTaskEventItem {
  id?: number
  task_id?: string
  run_id?: string | null
  event_type?: string
  status_after?: SystemTaskStatus
  attempt_no?: number
  message?: string | null
  event_payload?: Record<string, any> | null
  created_at?: string | null
}

export interface SystemTaskDetailResponse extends SystemTaskObservationItem {
  events?: SystemTaskEventItem[]
}

export interface WeeklySchedulerLogItem {
  id: number
  status: 'queued' | 'skipped' | 'error' | string
  reason?: string | null
  run_id?: string | null
  task_id?: string | null
  ignore_strategy_task_id?: string | null
  week_start?: string | null
  reference_date?: string | null
  poll_seconds?: number | null
  trigger_weekday?: number | null
  trigger_hour?: number | null
  use_llm?: boolean | null
  ignore_strategy_enabled?: boolean | null
  ignore_strategy_apply?: boolean | null
  details?: Record<string, any> | null
  created_at?: string | null
}

export interface WeeklySchedulerLogListResponse {
  count: number
  results: WeeklySchedulerLogItem[]
}

export interface MaintenanceCleanupResponse {
  resource: string
  retention_days: number
  dry_run: boolean
  cutoff: string
  stale_count: number
  deleted_count: number
}

export const getSystemTaskSummary = () => {
  return request<SystemTaskSummaryResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_TASKS_SUMMARY),
    method: 'get'
  })
}

export const getSystemTasks = (params?: SystemTaskListParams) => {
  return request<SystemTaskListResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_TASKS),
    method: 'get',
    params
  })
}

export const getSystemTaskDetail = (taskId: string) => {
  return request<SystemTaskDetailResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_TASK_DETAIL(taskId)),
    method: 'get'
  })
}

export const getSystemTaskEvents = (taskId: string, params?: { limit?: number }) => {
  return request<SystemTaskEventItem[]>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_TASK_EVENTS(taskId)),
    method: 'get',
    params
  })
}

export const getWeeklySchedulerLogs = (params?: {
  page?: number
  limit?: number
  status?: string
  reason?: string
  run_id?: string
}) => {
  return request<WeeklySchedulerLogListResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_WEEKLY_SCHEDULER_LOGS),
    method: 'get',
    params
  })
}

export const cleanupTaskEventsMaintenance = (data?: {
  retention_days?: number
  dry_run?: boolean
}) => {
  return request<MaintenanceCleanupResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_MAINTENANCE_CLEANUP_TASK_EVENTS),
    method: 'post',
    data,
  })
}

export const cleanupWeeklySchedulerLogsMaintenance = (data?: {
  retention_days?: number
  dry_run?: boolean
}) => {
  return request<MaintenanceCleanupResponse>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_MAINTENANCE_CLEANUP_WEEKLY_SCHEDULER_LOGS),
    method: 'post',
    data,
  })
}

// Webhook 测试
export const testWebhook = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.WEBHOOK_TEST),
    method: 'post',
    data
  })
}

// 项目管理 - 获取项目列表
export const getProjects = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECTS),
    method: 'get',
    params
  })
}

// 项目管理 - 获取项目详情
export const getProjectDetail = (id: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_DETAIL(id)),
    method: 'get'
  })
}

// 项目管理 - 启用项目审查
export const enableProjectReview = (id: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_ENABLE(id)),
    method: 'post'
  })
}

// 项目管理 - 禁用项目审查
export const disableProjectReview = (id: string) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_DISABLE(id)),
    method: 'post'
  })
}

// 项目管理 - 更新项目设置
export const updateProject = (id: string, data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_UPDATE(id)),
    method: 'post',
    data
  })
}

// 项目管理 - 获取项目webhook日志
export const getProjectWebhookLogs = (id: string, params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_WEBHOOK_LOGS(id)),
    method: 'get',
    params
  })
}

// 项目管理 - 获取项目审查历史
export const getProjectReviewHistory = (id: string, params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_REVIEW_HISTORY(id)),
    method: 'get',
    params
  })
}

export const getProjectStatsDetail = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_STATS_DETAIL(id)),
    method: 'get'
  })
}

// 项目通知 - 获取
export const getProjectNotifications = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_NOTIFICATIONS(id)),
    method: 'get'
  })
}

// 项目通知 - 更新
export const updateProjectNotifications = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_NOTIFICATIONS_UPDATE(id)),
    method: 'post',
    data
  })
}

// 项目 Webhook 事件 - 获取
export const getProjectWebhookEvents = (id: string | number) => {
  return request({
    url: getApiUrl(`/webhook/projects/${id}/webhook-events/`),
    method: 'get'
  })
}

// 项目 Webhook 事件 - 更新
export const updateProjectWebhookEvents = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(`/webhook/projects/${id}/webhook-events/update/`),
    method: 'post',
    data
  })
}

// 项目 Webhook 事件 Prompt - 获取
export const getProjectWebhookEventPrompts = (id: string | number) => {
  return request({
    url: getApiUrl(`/webhook/projects/${id}/webhook-event-prompts/`),
    method: 'get'
  })
}

// 项目 Webhook 事件 Prompt - 更新
export const updateProjectWebhookEventPrompt = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(`/webhook/projects/${id}/webhook-event-prompts/update/`),
    method: 'post',
    data
  })
}

// 项目管理 - 获取所有项目的统计数据
export const getAllProjectStats = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECT_STATS),
    method: 'get'
  })
}

// Webhook事件规则 - 获取列表
export const getWebhookEventRules = (params?: any) => {
  return request({
    url: getApiUrl('/webhook-event-rules/'),
    method: 'get',
    params
  })
}

// Webhook事件规则 - 获取详情
export const getWebhookEventRule = (id: string | number) => {
  return request({
    url: getApiUrl(`/webhook-event-rules/${id}/`),
    method: 'get'
  })
}

// Webhook事件规则 - 创建
export const createWebhookEventRule = (data: any) => {
  return request({
    url: getApiUrl('/webhook-event-rules/'),
    method: 'post',
    data
  })
}

// Webhook事件规则 - 更新
export const updateWebhookEventRule = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(`/webhook-event-rules/${id}/`),
    method: 'patch',
    data
  })
}

// Webhook事件规则 - 删除
export const deleteWebhookEventRule = (id: string | number) => {
  return request({
    url: getApiUrl(`/webhook-event-rules/${id}/`),
    method: 'delete'
  })
}

// Webhook事件规则 - 测试规则
export const testWebhookEventRule = (id: string | number, payload: any) => {
  return request({
    url: getApiUrl(`/webhook-event-rules/${id}/test_rule/`),
    method: 'post',
    data: { payload }
  })
}

// Webhook事件规则 - 验证payload
export const validateWebhookPayload = (payload: any) => {
  return request({
    url: getApiUrl('/webhook-event-rules/validate_payload/'),
    method: 'post',
    data: { payload }
  })
}

// Webhook事件规则 - 初始化默认规则
export const initializeDefaultWebhookEventRules = () => {
  return request({
    url: getApiUrl('/webhook-event-rules/initialize_defaults/'),
    method: 'post'
  })
}

// 获取 Webhook URL
export const getWebhookUrl = () => {
  return request({
    url: getApiUrl('/webhook/webhook-url/'),
    method: 'get'
  })
}

// 测试 Claude CLI 配置
export const testClaudeCliConfigApi = (data: any) => {
  return request({
    url: getApiUrl('/configs/test-claude-cli/'),
    method: 'post',
    data,
    timeout: 90000
  })
}

// LLM Provider CRUD
export const getLLMProviders = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDERS),
    method: 'get',
    params
  })
}

export const createLLMProvider = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDERS),
    method: 'post',
    data
  })
}

export const getLLMProvider = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_DETAIL(id)),
    method: 'get'
  })
}

export const updateLLMProvider = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_DETAIL(id)),
    method: 'put',
    data
  })
}

export const patchLLMProvider = (id: string | number, data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_DETAIL(id)),
    method: 'patch',
    data
  })
}

export const deleteLLMProvider = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_DETAIL(id)),
    method: 'delete'
  })
}

export const activateLLMProvider = (id: string | number) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_ACTIVATE(id)),
    method: 'post'
  })
}

export const fetchLLMModels = (data: { api_base: string; api_key?: string }) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_FETCH_MODELS),
    method: 'post',
    data,
    timeout: 20000
  })
}

export const testLLMProviderConnection = (data: { protocol: string; config_data: Record<string, any> }) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.LLM_PROVIDER_TEST_CONNECTION),
    method: 'post',
    data,
    timeout: 45000
  })
}

// GitLab Project Import
export const searchGitLabProjects = (params?: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.GITLAB_PROJECT_SEARCH),
    method: 'get',
    params
  })
}

export const importGitLabProjects = (data: any) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.PROJECTS_IMPORT),
    method: 'post',
    data
  })
}

// System Configs
export const getSystemConfigs = () => {
  return request({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_CONFIGS),
    method: 'get'
  })
}

export const updateSystemConfigs = (data: { configs: Record<string, string> }) => {
  return request({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_CONFIGS),
    method: 'put',
    data
  })
}

export const triggerDeveloperWeeklyLastWeekSummary = (data?: {
  reference_date?: string
  include_statuses?: string[]
  use_llm?: boolean
}) => {
  return request<{ code?: number; message?: string; task_id?: string; run_id?: string }>({
    url: getApiUrl(API_ENDPOINTS.SYSTEM_REPORTS_DEVELOPER_WEEKLY_GENERATE_LAST_WEEK),
    method: 'post',
    data
  })
}
