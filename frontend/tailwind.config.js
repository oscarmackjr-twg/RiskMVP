/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brutal: {
          black: '#000000',
          white: '#FFFFFF',
          yellow: '#FFE500',
          pink: '#FF6B9D',
          blue: '#00D4FF',
          green: '#00FF94',
          orange: '#FF9500',
          red: '#FF3B3B',
          purple: '#B84DFF',
          lime: '#C8FF00',
        }
      },
      boxShadow: {
        'brutal': '4px 4px 0px 0px #000000',
        'brutal-md': '6px 6px 0px 0px #000000',
        'brutal-lg': '8px 8px 0px 0px #000000',
        'brutal-xl': '12px 12px 0px 0px #000000',
        'brutal-hover': '2px 2px 0px 0px #000000',
        'brutal-active': '0px 0px 0px 0px #000000',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderWidth: {
        '3': '3px',
      },
    },
  },
  plugins: [],
}
