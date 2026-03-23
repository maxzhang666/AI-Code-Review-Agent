const HAS_EXPLICIT_TIMEZONE_RE = /(Z|[+-]\d{2}:\d{2}|[+-]\d{4})$/i

const normalizeBackendDateInput = (value: string): string => {
  let normalized = value.trim()
  if (!normalized) return normalized

  if (normalized.includes(' ') && !normalized.includes('T')) {
    normalized = normalized.replace(' ', 'T')
  }

  const hasTime = /\d{2}:\d{2}/.test(normalized)
  if (hasTime && !HAS_EXPLICIT_TIMEZONE_RE.test(normalized)) {
    normalized = `${normalized}Z`
  }

  return normalized
}

export const parseBackendDate = (value: string | null | undefined): Date | null => {
  if (!value) return null
  const normalized = normalizeBackendDateInput(String(value))
  if (!normalized) return null
  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

export const formatBackendDateTime = (
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
): string => {
  if (!value) return '-'
  const parsed = parseBackendDate(value)
  if (!parsed) return String(value).replace('T', ' ').replace('Z', '')
  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    ...options,
  }).replace(/\//g, '-')
}

export const formatBackendDate = (
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
): string => {
  if (!value) return '-'
  const parsed = parseBackendDate(value)
  if (!parsed) return String(value)
  return parsed.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...options,
  }).replace(/\//g, '-')
}

export const formatBackendTime = (
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
): string => {
  if (!value) return '-'
  const parsed = parseBackendDate(value)
  if (!parsed) return String(value)
  return parsed.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    ...options,
  })
}
