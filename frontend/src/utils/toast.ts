export type ToastType = 'success' | 'error' | 'warning' | 'info'
export interface ToastPayload {
  message: string
  type: ToastType
  duration?: number
}

type ToastHandler = (payload: ToastPayload) => void

let handler: ToastHandler | null = null

export const setToastHandler = (next: ToastHandler | null) => {
  handler = next
}

const emitToast = (payload: ToastPayload) => {
  if (handler) {
    handler(payload)
    return
  }
  const method = payload.type === 'error' ? 'error' : payload.type === 'warning' ? 'warn' : 'log'
  console[method](`[toast:${payload.type}] ${payload.message}`)
}

export function showToast({ message, type = 'info', duration = 3000 }: {
  message: string
  type?: ToastType
  duration?: number
}) {
  emitToast({ message, type, duration })
}

export const toast = {
  success: (message: string, duration?: number) => emitToast({ message, type: 'success', duration }),
  error: (message: string, duration?: number) => emitToast({ message, type: 'error', duration }),
  warning: (message: string, duration?: number) => emitToast({ message, type: 'warning', duration }),
  info: (message: string, duration?: number) => emitToast({ message, type: 'info', duration }),
}
