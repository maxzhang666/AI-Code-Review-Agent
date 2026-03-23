export type ReviewStatusSeverity = 'success' | 'info' | 'danger' | 'warn' | 'secondary'

interface ReviewStatusMeta {
  label: string
  severity: ReviewStatusSeverity
}

const normalizeStatus = (status: string): string => {
  return status.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

const STATUS_MAP: Record<string, ReviewStatusMeta> = {
  completed: { label: '已完成', severity: 'success' },
  success: { label: '已完成', severity: 'success' },
  succeeded: { label: '已完成', severity: 'success' },
  done: { label: '已完成', severity: 'success' },
  finished: { label: '已完成', severity: 'success' },
  '已完成': { label: '已完成', severity: 'success' },
  完成: { label: '已完成', severity: 'success' },
  成功: { label: '已完成', severity: 'success' },
  通过: { label: '已完成', severity: 'success' },

  processing: { label: '进行中', severity: 'info' },
  in_progress: { label: '进行中', severity: 'info' },
  running: { label: '进行中', severity: 'info' },
  reviewing: { label: '进行中', severity: 'info' },
  '进行中': { label: '进行中', severity: 'info' },
  处理中: { label: '进行中', severity: 'info' },
  审查中: { label: '进行中', severity: 'info' },

  failed: { label: '失败', severity: 'danger' },
  error: { label: '失败', severity: 'danger' },
  errored: { label: '失败', severity: 'danger' },
  rejected: { label: '失败', severity: 'danger' },
  失败: { label: '失败', severity: 'danger' },
  异常: { label: '失败', severity: 'danger' },

  pending: { label: '等待中', severity: 'warn' },
  waiting: { label: '等待中', severity: 'warn' },
  queued: { label: '等待中', severity: 'warn' },
  '等待中': { label: '等待中', severity: 'warn' },
  待处理: { label: '等待中', severity: 'warn' },
  排队中: { label: '等待中', severity: 'warn' },
}

export const getReviewStatusMeta = (status: string | null | undefined): ReviewStatusMeta => {
  const raw = String(status ?? '').trim()
  if (!raw) {
    return { label: '未知', severity: 'secondary' }
  }

  const key = normalizeStatus(raw)
  return STATUS_MAP[key] ?? { label: raw, severity: 'secondary' }
}

