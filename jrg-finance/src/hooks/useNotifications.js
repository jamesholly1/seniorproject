import { useState, useCallback } from 'react'
import {
  getNotificationThresholds,
  addNotificationThreshold,
  deleteNotificationThreshold,
  updateThresholdStatus,
  resetThresholdTrigger,
} from '../api/client'

/**
 * Derives a display status from the raw threshold fields.
 *   triggered  → 'triggered'
 *   is_active  → 'active'
 *   otherwise  → 'inactive'
 */
export function deriveStatus(threshold) {
  if (threshold.triggered) return 'triggered'
  if (threshold.is_active) return 'active'
  return 'inactive'
}

export function useNotifications() {
  const [thresholds, setThresholds] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchThresholds = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getNotificationThresholds()
      setThresholds(data ?? [])
    } catch (err) {
      // Swallow 404 gracefully — endpoint may not be deployed yet
      if (err.response?.status === 404) {
        setThresholds([])
      } else {
        setError(err.response?.data?.detail || 'Failed to load alerts')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const addThreshold = useCallback(
    async (ticker, price, direction) => {
      await addNotificationThreshold(ticker, price, direction)
      await fetchThresholds()
    },
    [fetchThresholds]
  )

  const removeThreshold = useCallback(
    async (id) => {
      await deleteNotificationThreshold(id)
      setThresholds((prev) => prev.filter((t) => t.id !== id))
    },
    []
  )

  const toggleStatus = useCallback(
    async (id, currentIsActive) => {
      await updateThresholdStatus(id, !currentIsActive)
      setThresholds((prev) =>
        prev.map((t) =>
          t.id === id ? { ...t, is_active: !currentIsActive, triggered: false } : t
        )
      )
    },
    []
  )

  const resetTrigger = useCallback(async (id) => {
    await resetThresholdTrigger(id)
    setThresholds((prev) =>
      prev.map((t) => (t.id === id ? { ...t, triggered: false, is_active: true } : t))
    )
  }, [])

  return {
    thresholds,
    loading,
    error,
    fetchThresholds,
    addThreshold,
    removeThreshold,
    toggleStatus,
    resetTrigger,
  }
}
