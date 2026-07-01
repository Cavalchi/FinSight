import type { DayMetric, NewsItem } from './types'

const BASE = '/api'

export async function fetchTickers(): Promise<string[]> {
  const res = await fetch(`${BASE}/tickers`)
  if (!res.ok) throw new Error('Failed to fetch tickers')
  return res.json()
}

export async function fetchMetrics(ticker: string): Promise<DayMetric[]> {
  const res = await fetch(`${BASE}/metrics/${encodeURIComponent(ticker)}`)
  if (!res.ok) throw new Error(`Failed to fetch metrics for ${ticker}`)
  return res.json()
}

export async function fetchNews(): Promise<NewsItem[]> {
  const res = await fetch(`${BASE}/news?limit=30`)
  if (!res.ok) throw new Error('Failed to fetch news')
  return res.json()
}
