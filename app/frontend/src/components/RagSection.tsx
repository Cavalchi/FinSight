import { useState, useRef, useEffect } from 'react'
import { askAnalyst } from '../api'
import type { RagResult, RagSource } from '../api'
import type { useT } from '../i18n'
import clsx from 'clsx'

interface Props {
  ticker: string
  t: ReturnType<typeof useT>
}

// Thinking steps shown during loading
const THINKING_STEPS = [
  { id: 'understand', icon: '🧠', label: 'Entendendo sua pergunta...',       duration: 600  },
  { id: 'retrieve',  icon: '🗄️', label: 'Buscando notícias no pipeline...', duration: 1400 },
  { id: 'market',    icon: '📊', label: 'Consultando dados de mercado...',   duration: 2400 },
  { id: 'generate',  icon: '⚡', label: 'Gerando análise com Gemini...',    duration: 9999 },
]

// Suggestions per ticker
const SUGGESTIONS: Record<string, string[]> = {
  'PETR4.SA': [
    'Como foi a volatilidade da Petrobras esse mês?',
    'Quais os principais riscos da PETR4 agora?',
    'O que saiu na imprensa sobre Petrobras?',
  ],
  'VALE3.SA': [
    'Como a Vale está se saindo frente ao minério?',
    'Quais notícias afetaram a VALE3 recentemente?',
    'Compare a volatilidade da Vale com a média.',
  ],
  'ITUB4.SA': [
    'Como o Itaú se saiu nos últimos dias?',
    'Perspectivas para bancos brasileiros?',
    'O que dizem os analistas sobre o ITUB4?',
  ],
  _default: [
    'Qual ação teve melhor desempenho essa semana?',
    'Principais riscos do mercado brasileiro agora?',
    'Como o dólar impacta as ações listadas?',
  ],
}

function getSuggestions(ticker: string): string[] {
  return SUGGESTIONS[ticker] || SUGGESTIONS._default
}

function formatResponse(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="bg-white/5 px-1 rounded text-blue-300 font-mono text-xs">$1</code>')
    .replace(/\n\n/g, '</p><p class="mt-3">')
    .replace(/\n/g, '<br/>')
}

// Onboarding messages cycle
const ONBOARDING_LINES = [
  'Quer uma análise mais assertiva?',
  'Pergunte ao Analista FinSight.',
  'Powered by seus próprios dados.',
]

export default function RagSection({ ticker, t }: Props) {
  const [question, setQuestion]       = useState('')
  const [loading, setLoading]         = useState(false)
  const [result, setResult]           = useState<RagResult | null>(null)
  const [error, setError]             = useState<string | null>(null)
  const [showSources, setShowSources] = useState(false)
  const [activeStep, setActiveStep]   = useState(-1)  // current thinking step
  const [hasAsked, setHasAsked]       = useState(false) // onboarding gone after first question
  const [onbLine, setOnbLine]         = useState(0)   // which onboarding line is visible
  const inputRef   = useRef<HTMLTextAreaElement>(null)
  const resultRef  = useRef<HTMLDivElement>(null)
  const sectionRef = useRef<HTMLDivElement>(null)
  const stepTimers = useRef<ReturnType<typeof setTimeout>[]>([])

  const suggestions = getSuggestions(ticker)

  // Onboarding text cycling
  useEffect(() => {
    if (hasAsked) return
    const id = setInterval(() => setOnbLine(l => (l + 1) % ONBOARDING_LINES.length), 2800)
    return () => clearInterval(id)
  }, [hasAsked])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px'
    }
  }, [question])

  // Scroll into view when result arrives
  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [result])

  function clearStepTimers() {
    stepTimers.current.forEach(clearTimeout)
    stepTimers.current = []
  }

  function startThinkingSteps() {
    clearStepTimers()
    setActiveStep(0)
    let elapsed = 0
    THINKING_STEPS.forEach((step, i) => {
      elapsed += step.duration
      if (i < THINKING_STEPS.length - 1) {
        const t = setTimeout(() => setActiveStep(i + 1), elapsed)
        stepTimers.current.push(t)
      }
    })
  }

  async function handleSubmit(q?: string) {
    const finalQ = (q || question).trim()
    if (!finalQ || loading) return

    setQuestion(finalQ)
    setLoading(true)
    setResult(null)
    setError(null)
    setShowSources(false)
    setHasAsked(true)
    startThinkingSteps()

    // Scroll section into view
    setTimeout(() => sectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)

    try {
      const res = await askAnalyst(finalQ, ticker)
      setResult(res)
    } catch (e: any) {
      setError(e.message || 'Unknown error')
    } finally {
      setLoading(false)
      setActiveStep(-1)
      clearStepTimers()
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div
      ref={sectionRef}
      className="relative rounded-2xl overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, rgba(8,15,30,0) 0%, rgba(8,15,30,0.6) 40%, rgba(8,15,30,0.95) 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
        minHeight: '480px',
      }}
    >
      {/* Ambient glow background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-2xl">
        <div
          className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[400px] opacity-20 blur-[80px] transition-opacity duration-1000"
          style={{ background: 'radial-gradient(ellipse, #3b82f6 0%, #7c3aed 50%, transparent 70%)' }}
        />
      </div>

      <div className="relative z-10 flex flex-col h-full p-6 gap-6">

        {/* ── ONBOARDING (before first question) ── */}
        {!hasAsked && !loading && (
          <div className="flex flex-col items-center justify-center flex-1 py-8 text-center">
            {/* Icon */}
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-5 shadow-lg"
              style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', boxShadow: '0 0 40px rgba(139,92,246,0.35)' }}
            >
              ✦
            </div>

            {/* Animated cycling text */}
            <div className="h-8 overflow-hidden mb-1">
              {ONBOARDING_LINES.map((line, i) => (
                <div
                  key={i}
                  className="transition-all duration-700"
                  style={{
                    transform: `translateY(${(i - onbLine) * 100}%)`,
                    opacity: i === onbLine ? 1 : 0,
                    position: i === 0 ? 'relative' : 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                  }}
                >
                  <h3 className="text-lg font-semibold text-white">{line}</h3>
                </div>
              ))}
            </div>

            <p className="text-xs text-[#4a6282] mt-2 mb-6">
              Respostas fundamentadas nos dados do seu próprio pipeline — notícias + preços + dbt.
            </p>

            {/* Suggestion chips as main CTA */}
            <div className="flex flex-wrap gap-2 justify-center max-w-xl">
              {suggestions.map(s => (
                <button
                  key={s}
                  onClick={() => handleSubmit(s)}
                  className="text-xs px-4 py-2 rounded-xl border border-white/10 text-[#7b9bc0] hover:text-white hover:border-blue-500/40 hover:bg-blue-500/8 bg-white/[0.03] transition-all duration-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── THINKING STEPS (during loading) ── */}
        {loading && (
          <div className="flex flex-col items-center justify-center flex-1 py-8 gap-4">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center text-xl mb-2"
              style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', boxShadow: '0 0 30px rgba(139,92,246,0.3)' }}
            >
              ✦
            </div>

            {/* Question echo */}
            <p className="text-sm text-[#7b9bc0] italic max-w-md text-center">"{question}"</p>

            {/* Steps */}
            <div className="flex flex-col gap-3 mt-4 w-full max-w-xs">
              {THINKING_STEPS.map((step, i) => {
                const isDone    = activeStep > i
                const isCurrent = activeStep === i
                return (
                  <div
                    key={step.id}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-all duration-500',
                      isDone    && 'border-emerald-500/20 bg-emerald-500/5',
                      isCurrent && 'border-blue-500/30 bg-blue-500/8',
                      !isDone && !isCurrent && 'border-white/5 bg-white/[0.02] opacity-40',
                    )}
                  >
                    <span className="text-base">{step.icon}</span>
                    <span className={clsx(
                      'text-xs flex-1',
                      isDone    ? 'text-emerald-400' : isCurrent ? 'text-white' : 'text-[#2d4560]'
                    )}>
                      {step.label}
                    </span>
                    {isDone && <span className="text-emerald-400 text-xs">✓</span>}
                    {isCurrent && (
                      <span className="w-3 h-3 border border-blue-400/50 border-t-blue-400 rounded-full animate-spin flex-shrink-0" />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── ERROR ── */}
        {error && !loading && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4 text-sm text-red-400">
            ⚠️ {error}
          </div>
        )}

        {/* ── RESULT ── */}
        {result && !loading && (
          <div ref={resultRef} className="flex flex-col gap-4 animate-in fade-in duration-500">
            {/* Answer header */}
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)' }}
              >
                ✦
              </div>
              <div>
                <div className="text-sm font-semibold text-white">FinSight AI Analyst</div>
                <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Gemini · {result.chunks_used} chunks · {result.has_market_data ? '+ market data' : 'news only'}
                </div>
              </div>
              <button
                onClick={() => { setResult(null); setHasAsked(false); setQuestion('') }}
                className="ml-auto text-[10px] text-[#4a6282] hover:text-white transition-colors px-2 py-1 rounded border border-white/5 hover:border-white/10"
              >
                Nova pergunta ↺
              </button>
            </div>

            {/* Response text */}
            <div
              className="rounded-xl border border-white/6 bg-white/[0.025] p-5 text-sm text-[#cbd5e1] leading-relaxed [&_strong]:text-white [&_code]:text-blue-300"
              dangerouslySetInnerHTML={{ __html: `<p>${formatResponse(result.response)}</p>` }}
            />

            {/* Sources accordion */}
            {result.sources.length > 0 && (
              <div className="rounded-xl border border-white/6 overflow-hidden">
                <button
                  onClick={() => setShowSources(v => !v)}
                  className="w-full flex items-center justify-between px-4 py-3 text-xs text-[#64748b] hover:text-[#94a3b8] transition-colors bg-white/[0.02] hover:bg-white/[0.04]"
                >
                  <span>📰 {result.sources.length} fonte{result.sources.length > 1 ? 's' : ''} utilizadas</span>
                  <span className={clsx('transition-transform duration-200', showSources && 'rotate-180')}>▾</span>
                </button>

                {showSources && (
                  <div className="border-t border-white/4 divide-y divide-white/4">
                    {result.sources.map((s: RagSource, i: number) => (
                      <div key={i} className="px-4 py-3 flex items-start gap-3">
                        <div className={clsx(
                          'flex-shrink-0 text-[9px] font-mono px-1.5 py-0.5 rounded mt-0.5',
                          s.similarity > 0.6 ? 'bg-emerald-500/10 text-emerald-400'
                            : s.similarity > 0.4 ? 'bg-blue-500/10 text-blue-400'
                            : 'bg-white/5 text-[#4a6282]'
                        )}>
                          {(s.similarity * 100).toFixed(0)}%
                        </div>
                        <div className="flex-1 min-w-0">
                          {s.url ? (
                            <a href={s.url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-[#7b9bc0] hover:text-white transition-colors line-clamp-2 leading-relaxed">
                              {s.headline}
                            </a>
                          ) : (
                            <div className="text-xs text-[#7b9bc0] line-clamp-2 leading-relaxed">{s.headline}</div>
                          )}
                          <div className="text-[10px] text-[#2a3a52] font-mono mt-1">
                            {[s.source, s.date].filter(Boolean).join(' · ')}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── INPUT (always visible at bottom, except during loading) ── */}
        {!loading && (
          <div className="mt-auto">
            {/* Suggestions (after result, compact) */}
            {result && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => handleSubmit(s)}
                    className="text-[11px] px-3 py-1.5 rounded-lg border border-white/8 text-[#7b9bc0] hover:text-white hover:border-white/15 bg-white/[0.02] hover:bg-white/5 transition-all duration-150"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Textarea */}
            <div className={clsx(
              'rounded-xl border transition-all duration-200',
              'bg-[#080f1e]/80',
              'border-white/8 focus-within:border-blue-500/40 focus-within:shadow-[0_0_20px_rgba(59,130,246,0.12)]'
            )}>
              <textarea
                ref={inputRef}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={result ? 'Faça outra pergunta...' : t.ragExample}
                rows={2}
                className="w-full bg-transparent text-sm text-white placeholder:text-[#2d4560] px-4 pt-3 pb-2 resize-none outline-none leading-relaxed"
              />
              <div className="flex items-center justify-between px-3 pb-2.5">
                <span className="text-[10px] text-[#3a5068] font-mono">
                  Enter para enviar · Shift+Enter nova linha
                </span>
                <button
                  onClick={() => handleSubmit()}
                  disabled={!question.trim()}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all duration-150',
                    question.trim()
                      ? 'bg-blue-600 hover:bg-blue-500 text-white cursor-pointer'
                      : 'bg-white/4 text-[#2d4560] cursor-not-allowed'
                  )}
                >
                  Analisar <span className="opacity-60">↵</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
