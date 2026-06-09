/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm "newsprint" paper palette (Alpha Arena aesthetic)
        paper: '#f4f1e9',
        panel: '#faf8f2',
        ink: '#1a1916',
        faint: '#6b6658',
        line: '#d8d2c4',
        rule: '#1a1916',
        gain: '#1f8a4c',
        loss: '#c0392b',
        long: '#1f8a4c',
        short: '#c0392b',
        highlight: '#e9dca8',
        link: '#1a1916',
        // pastel model/pod avatar tints
        p1: '#f2c9d4',
        p2: '#cfe8d6',
        p3: '#cfe0f2',
        p4: '#e7d6f2',
        p5: '#f2e2c2',
        p6: '#c9ecec',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'SF Mono', 'Menlo', 'Consolas', 'Liberation Mono', 'monospace'],
        serif: ['"Times New Roman"', 'Times', 'Georgia', 'serif'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '0.9rem' }],
      },
      keyframes: {
        ticker: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      },
      animation: {
        ticker: 'ticker 60s linear infinite',
      },
    },
  },
  plugins: [],
}
