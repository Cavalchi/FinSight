import type { Lang } from './types'

type Strings = {
  lastClose: string; dailyReturn: string; vol30d: string; sma7: string; relVol: string
  priceChart: string; volatility: string; dailyRet: string; news: string
  langLabel: string; period: string; allPeriods: string; sma7Label: string; sma30Label: string
  ohlc: string; annualized: string; vs30dAvg: string
  ragTitle: string; ragSub: string; ragExample: string
  noData: string; loading: string; sector: string
  p7d: string; p1m: string; p3m: string; pAll: string
  volHigh: string; volMid: string; volLow: string
  volElevated: string; volNormal: string; volMuted: string
  smaAbove: string; smaBelow: string
}

const T: Record<Lang, Strings> = {
  EN: {
    lastClose:'Last Close', dailyReturn:'Daily Return', vol30d:'Volatility 30d', sma7:'SMA 7d', relVol:'Rel. Volume',
    priceChart:'Price & Moving Averages', volatility:'30d Volatility', dailyRet:'Daily Return',
    news:'Market News', langLabel:'Language', period:'Period', allPeriods:'All',
    sma7Label:'SMA 7d', sma30Label:'SMA 30d', ohlc:'OHLC', annualized:'annualized', vs30dAvg:'vs 30d avg',
    ragTitle:'FinSight AI Analyst',
    ragSub:'Ask questions grounded in your own pipeline data.',
    ragExample:'How was PETR4 volatility this week and what news drove it?',
    noData:'No data yet. Run the Airflow DAG first.', loading:'Loading…', sector:'Sector',
    p7d:'7D', p1m:'1M', p3m:'3M', pAll:'ALL',
    volHigh:'High', volMid:'Moderate', volLow:'Low',
    volElevated:'Elevated', volNormal:'Normal', volMuted:'Muted',
    smaAbove:'above avg', smaBelow:'below avg',
  },
  PT: {
    lastClose:'Último Fechamento', dailyReturn:'Retorno Diário', vol30d:'Volatilidade 30d', sma7:'MM 7d', relVol:'Vol. Relativo',
    priceChart:'Preço & Médias Móveis', volatility:'Volatilidade 30d', dailyRet:'Retorno Diário',
    news:'Notícias do Mercado', langLabel:'Idioma', period:'Período', allPeriods:'Tudo',
    sma7Label:'MM 7d', sma30Label:'MM 30d', ohlc:'OHLC', annualized:'anualizada', vs30dAvg:'vs média 30d',
    ragTitle:'Analista IA FinSight',
    ragSub:'Faça perguntas baseadas nos seus próprios dados.',
    ragExample:'Como foi a volatilidade da PETR4 essa semana?',
    noData:'Sem dados ainda. Dispare a DAG no Airflow primeiro.', loading:'Carregando…', sector:'Setor',
    p7d:'7D', p1m:'1M', p3m:'3M', pAll:'TUDO',
    volHigh:'Alta', volMid:'Moderada', volLow:'Baixa',
    volElevated:'Elevado', volNormal:'Normal', volMuted:'Reduzido',
    smaAbove:'acima da média', smaBelow:'abaixo da média',
  },
  ES: {
    lastClose:'Último Cierre', dailyReturn:'Retorno Diario', vol30d:'Volatilidad 30d', sma7:'MM 7d', relVol:'Vol. Relativo',
    priceChart:'Precio & Medias Móviles', volatility:'Volatilidad 30d', dailyRet:'Retorno Diario',
    news:'Noticias del Mercado', langLabel:'Idioma', period:'Período', allPeriods:'Todo',
    sma7Label:'MM 7d', sma30Label:'MM 30d', ohlc:'OHLC', annualized:'anualizada', vs30dAvg:'vs prom 30d',
    ragTitle:'Analista IA FinSight',
    ragSub:'Haz preguntas basadas en tus propios datos.',
    ragExample:'¿Cómo fue la volatilidad de PETR4 esta semana?',
    noData:'Sin datos aún. Primero dispara el DAG en Airflow.', loading:'Cargando…', sector:'Sector',
    p7d:'7D', p1m:'1M', p3m:'3M', pAll:'TODO',
    volHigh:'Alta', volMid:'Moderada', volLow:'Baja',
    volElevated:'Elevado', volNormal:'Normal', volMuted:'Reducido',
    smaAbove:'sobre el promedio', smaBelow:'bajo el promedio',
  },
}

export const useT = (lang: Lang) => T[lang]
