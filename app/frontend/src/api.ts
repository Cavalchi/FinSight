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

export interface RagSource {
  headline:   string
  source:     string | null
  url:        string | null
  date:       string | null
  similarity: number
}

export interface RagResult {
  response:        string
  sources:         RagSource[]
  chunks_used:     number
  has_market_data: boolean
  error:           string | null
}

export async function askAnalyst(question: string, ticker?: string): Promise<RagResult> {
  const res = await fetch(`${BASE}/rag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, ticker: ticker || null }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail?.detail || 'Failed to get AI response')
  }
  return res.json()
}
