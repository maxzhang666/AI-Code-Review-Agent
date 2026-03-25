export interface RuleBucket {
  rule_key: string
  ignore_count: number
}

export interface ReasonBucket {
  reason_type: string
  count: number
  ratio: number
}

export interface TeamSummary {
  total_issues: number
  ignored_count: number
  reopened_count: number
  ignore_rate: number
  feedback_actions: number
}

export interface ProjectSummary {
  project_id: number
  project_name: string
  total_issues: number
  ignored_count: number
  reopened_count: number
  ignore_rate: number
  top_ignored_rules: RuleBucket[]
  ignore_reason_distribution: ReasonBucket[]
  suggested_policy_changes: string[]
}

export interface TeamWeeklyReport {
  week_start: string
  week_end: string
  summary: TeamSummary
  top_ignored_rules: RuleBucket[]
  ignore_reason_distribution: ReasonBucket[]
  suggested_policy_changes: string[]
  projects: ProjectSummary[]
  generated_at: string
}

export interface StatsBucket {
  name: string
  value: number
}

export interface MemberSummary {
  total_findings: number
  raw_total_findings: number
  excluded_findings: number
  total_reviews: number
  ignore_actions: number
  reopen_actions: number
  ignore_rate: number
}

export interface MemberWeeklyReport {
  week_start: string
  week_end: string
  include_statuses: string[]
  owner: string | null
  owner_email: string | null
  available_owners: string[]
  summary: MemberSummary
  by_category: StatsBucket[]
  by_severity: StatsBucket[]
  top_files: StatsBucket[]
  projects: StatsBucket[]
  ai_summary: string
  gap_checklist: string[]
  generated_at: string
}

export interface MemberCard {
  owner: string
  owner_email: string | null
  total_findings: number
  raw_total_findings: number
  excluded_findings: number
  total_reviews: number
  ignore_actions: number
  reopen_actions: number
  ignore_rate: number
  top_category: string
  top_severity: string
  summary_excerpt: string
  improvement_focus: string
}

export interface MemberCardResponse {
  week_start: string
  week_end: string
  include_statuses: string[]
  count: number
  results: MemberCard[]
  generated_at: string
}

export const EMPTY_TEAM_REPORT: TeamWeeklyReport = {
  week_start: '',
  week_end: '',
  summary: {
    total_issues: 0,
    ignored_count: 0,
    reopened_count: 0,
    ignore_rate: 0,
    feedback_actions: 0
  },
  top_ignored_rules: [],
  ignore_reason_distribution: [],
  suggested_policy_changes: [],
  projects: [],
  generated_at: ''
}

export const EMPTY_MEMBER_REPORT: MemberWeeklyReport = {
  week_start: '',
  week_end: '',
  include_statuses: [],
  owner: null,
  owner_email: null,
  available_owners: [],
  summary: {
    total_findings: 0,
    raw_total_findings: 0,
    excluded_findings: 0,
    total_reviews: 0,
    ignore_actions: 0,
    reopen_actions: 0,
    ignore_rate: 0
  },
  by_category: [],
  by_severity: [],
  top_files: [],
  projects: [],
  ai_summary: '',
  gap_checklist: [],
  generated_at: ''
}

export const toInputDate = (value: Date): string => {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

export const normalizeTeamReport = (data: Partial<TeamWeeklyReport> | undefined): TeamWeeklyReport => {
  const summary: Partial<TeamSummary> = data?.summary ?? {}
  return {
    week_start: data?.week_start ?? '',
    week_end: data?.week_end ?? '',
    summary: {
      total_issues: Number(summary.total_issues ?? 0),
      ignored_count: Number(summary.ignored_count ?? 0),
      reopened_count: Number(summary.reopened_count ?? 0),
      ignore_rate: Number(summary.ignore_rate ?? 0),
      feedback_actions: Number(summary.feedback_actions ?? 0)
    },
    top_ignored_rules: Array.isArray(data?.top_ignored_rules) ? data.top_ignored_rules : [],
    ignore_reason_distribution: Array.isArray(data?.ignore_reason_distribution) ? data.ignore_reason_distribution : [],
    suggested_policy_changes: Array.isArray(data?.suggested_policy_changes) ? data.suggested_policy_changes : [],
    projects: Array.isArray(data?.projects) ? data.projects : [],
    generated_at: data?.generated_at ?? ''
  }
}

export const normalizeMemberReport = (data: Partial<MemberWeeklyReport> | undefined): MemberWeeklyReport => {
  const summary: Partial<MemberSummary> = data?.summary ?? {}
  return {
    week_start: data?.week_start ?? '',
    week_end: data?.week_end ?? '',
    include_statuses: Array.isArray(data?.include_statuses) ? data.include_statuses : [],
    owner: data?.owner ?? null,
    owner_email: data?.owner_email ?? null,
    available_owners: Array.isArray(data?.available_owners) ? data.available_owners : [],
    summary: {
      total_findings: Number(summary.total_findings ?? 0),
      raw_total_findings: Number(summary.raw_total_findings ?? summary.total_findings ?? 0),
      excluded_findings: Number(summary.excluded_findings ?? 0),
      total_reviews: Number(summary.total_reviews ?? 0),
      ignore_actions: Number(summary.ignore_actions ?? 0),
      reopen_actions: Number(summary.reopen_actions ?? 0),
      ignore_rate: Number(summary.ignore_rate ?? 0)
    },
    by_category: Array.isArray(data?.by_category) ? data.by_category : [],
    by_severity: Array.isArray(data?.by_severity) ? data.by_severity : [],
    top_files: Array.isArray(data?.top_files) ? data.top_files : [],
    projects: Array.isArray(data?.projects) ? data.projects : [],
    ai_summary: data?.ai_summary ?? '',
    gap_checklist: Array.isArray(data?.gap_checklist) ? data.gap_checklist : [],
    generated_at: data?.generated_at ?? ''
  }
}
