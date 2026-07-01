import type { useT } from '../i18n'

export default function RagSection({ t }: { t: ReturnType<typeof useT> }) {
  return (
    <div className="rounded-xl border rag-glow p-8 text-center relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.06), rgba(59,130,246,0.06))' }}>
      {/* Glowing orb */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-64 h-64 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #8b5cf6 0%, transparent 70%)' }} />
      </div>
      <div className="relative z-10">
        <div className="text-4xl mb-4">🤖</div>
        <div className="text-base font-semibold text-purple-300 mb-2">{t.ragTitle}</div>
        <div className="text-sm text-[#4a6282] max-w-lg mx-auto mb-4 leading-relaxed">{t.ragSub}</div>
        <div className="inline-block bg-purple/10 border border-purple/20 rounded-lg px-4 py-2 text-xs text-purple-300 italic font-mono">
          {t.ragExample}
        </div>
      </div>
    </div>
  )
}
