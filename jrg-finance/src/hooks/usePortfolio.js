import { useState, useCallback } from 'react'
import apiClient from '../api/client'

export function usePortfolio() {
  const [tickers, setTickers] = useState([])
  const [holdings, setHoldings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchPortfolio = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get('/api/portfolio')
      const list = data.tickers || []
      setTickers(list)

      if (list.length > 0) {
        const infos = await Promise.all(
          list.map((t) =>
            apiClient
              .get(`/api/stocks/${t}`)
              .then((r) => r.data)
              .catch(() => ({
                symbol: t,
                name: t,
                current_price: 'N/A',
                fifty_two_week_high: 'N/A',
                fifty_two_week_low: 'N/A',
              }))
          )
        )
        setHoldings(infos)
      } else {
        setHoldings([])
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load portfolio')
    } finally {
      setLoading(false)
    }
  }, [])

  const addTicker = useCallback(async (ticker) => {
    await apiClient.post('/api/portfolio/add', { ticker })
    await fetchPortfolio()
  }, [fetchPortfolio])

  const removeTicker = useCallback(async (ticker) => {
    await apiClient.delete(`/api/portfolio/${ticker}`)
    await fetchPortfolio()
  }, [fetchPortfolio])

  const clearAll = useCallback(async () => {
    await apiClient.delete('/api/portfolio')
    setTickers([])
    setHoldings([])
  }, [])

  return { tickers, holdings, loading, error, fetchPortfolio, addTicker, removeTicker, clearAll }
}
