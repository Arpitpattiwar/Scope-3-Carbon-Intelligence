/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#edfaf4',
          100: '#d0f5e3',
          200: '#a5eacb',
          300: '#6dd9ad',
          400: '#38c28d',
          500: '#1aa876',
          600: '#0f8660',
          700: '#0d6b4e',
          800: '#0d553f',
          900: '#0c4534',
        }
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    }
  },
  plugins: []
}
