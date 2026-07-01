// Shared TypeScript types

export interface DayMetric {
  trade_date: string
  open_price: number
  high_price: number
  low_price: number
  close_price: number
  adj_close_price: number
  volume: number
  daily_return_simple: number | null
  sma_7d: number | null
  sma_30d: number | null
  volatility_30d_pct: number | null
  relative_volume: number | null
  price_vs_sma30: number | null
}

export interface NewsItem {
  headline: string
  source: string | null
  url: string | null
  published_at: string | null
  category: string | null
  api_source: string
  related_tickers: string[]
}

export type Lang = 'EN' | 'PT' | 'ES'
export type Period = '7D' | '1M' | '3M' | 'ALL'

export const TICKER_INFO: Record<string, { name: string; flag: string; sector: string }> = {
  'PETR4.SA': { name: 'Petrobras',       flag: '🇧🇷', sector: 'Energy · B3'       },
  'VALE3.SA': { name: 'Vale S.A.',        flag: '🇧🇷', sector: 'Materials · B3'    },
  'ITUB4.SA': { name: 'Itaú Unibanco',   flag: '🇧🇷', sector: 'Finance · B3'      },
  'BBAS3.SA': { name: 'Banco do Brasil', flag: '🇧🇷', sector: 'Finance · B3'      },
  'VIVT3.SA': { name: 'Telefônica/Vivo', flag: '🇧🇷', sector: 'Telecom · B3'      },
  'NU':       { name: 'Nubank',           flag: '🇺🇸', sector: 'Fintech · NYSE'    },
  'NKE':      { name: 'Nike Inc.',        flag: '🇺🇸', sector: 'Consumer · NYSE'   },
  'ADDYY':    { name: 'Adidas AG',        flag: '🇩🇪', sector: 'Consumer · OTC'    },
}
