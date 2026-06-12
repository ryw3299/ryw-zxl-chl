const readPositiveNumber = (value, fallback) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export const API_TIMEOUT_MS = readPositiveNumber(import.meta.env.VITE_API_TIMEOUT_MS, 30000)
export const TASK_POLL_TIMEOUT_MS = readPositiveNumber(import.meta.env.VITE_TASK_POLL_TIMEOUT_MS, 600000)
export const TASK_POLL_INTERVAL_MS = readPositiveNumber(import.meta.env.VITE_TASK_POLL_INTERVAL_MS, 1500)
