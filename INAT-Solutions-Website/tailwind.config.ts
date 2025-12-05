import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4a6fa5',
          50: '#f0f4fb',
          100: '#dce5f5',
          200: '#c1d0ed',
          300: '#97b3e0',
          400: '#6690d0',
          500: '#4a6fa5',
          600: '#3b5b85',
          700: '#34506f',
          800: '#2f445c',
          900: '#2b3c4f',
        },
        secondary: {
          DEFAULT: '#3b5b85',
          dark: '#2d4a6f',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
export default config
