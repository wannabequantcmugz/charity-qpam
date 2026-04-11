/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        bg: '#0a0a0f',
        surface: '#111118',
        card: '#16161f',
        border: '#1e1e2e',
        accent: '#7c3aed',
        'accent-light': '#a855f7',
        'accent-glow': '#7c3aed33',
        green: '#22c55e',
        orange: '#f97316',
        muted: '#6b7280',
      },
      boxShadow: {
        glow: '0 0 30px #7c3aed44',
        'glow-sm': '0 0 15px #7c3aed33',
        card: '0 4px 24px #00000066',
      },
    },
  },
  plugins: [],
}
