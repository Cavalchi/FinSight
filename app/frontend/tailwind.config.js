/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        base:    '#040c1a',
        surface: '#0c1628',
        raised:  '#111d35',
        border:  'rgba(255,255,255,0.07)',
        up:      '#10b981',
        down:    '#ef4444',
        blue:    '#3b82f6',
        purple:  '#8b5cf6',
        amber:   '#f59e0b',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 5px rgba(59,130,246,0.3)' },
          to:   { boxShadow: '0 0 20px rgba(59,130,246,0.6)' },
        },
      },
      backdropBlur: { xs: '2px' },
    },
  },
  plugins: [],
}
