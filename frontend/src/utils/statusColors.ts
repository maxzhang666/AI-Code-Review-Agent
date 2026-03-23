export const reviewStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    completed: 'green',
    processing: 'arcoblue',
    failed: 'red',
    pending: 'orangered',
    '已完成': 'green',
    '进行中': 'arcoblue',
    '失败': 'red',
    '等待中': 'orangered'
  }
  return map[status] || 'arcoblue'
}

export const severityColor = (severity: string): string => {
  const map: Record<string, string> = { '高': 'red', '中': 'orangered', '低': 'arcoblue' }
  return map[severity] || 'arcoblue'
}

export const logLevelColor = (level: string): string => {
  const map: Record<string, string> = { INFO: 'arcoblue', WARNING: 'orangered', ERROR: 'red' }
  return map[level] || 'arcoblue'
}
