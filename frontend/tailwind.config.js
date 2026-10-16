/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'Inter', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'Inter Tight', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        dark: {
          950: '#06070b',
          900: '#0a0c11',
          850: '#0d1017',
          800: '#10131b',
          700: '#151a24',
          600: '#1c222e',
          500: '#262e3c',
          400: '#3a4254',
        },
        accent: {
          green: '#35d99a',
          red: '#f4586f',
          blue: '#5b9dff',
          yellow: '#eeb144',
          purple: '#9d7bfa',
          gold: '#d9a84e',
        },
        text: {
          primary: '#e9ecf4',
          secondary: '#9aa3b8',
          muted: '#5d6779',
        },
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        },
      },
    },
  },
  plugins: [],
};
