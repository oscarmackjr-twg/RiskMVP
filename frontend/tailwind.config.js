/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        twg: {
          navy: '#1B2A4A',
          'navy-light': '#2C3E5A',
          'tech-white': '#F5F7FA',
          accent: '#2563EB',
          'accent-light': '#3B82F6',
          success: '#16A34A',
          warning: '#D97706',
          error: '#DC2626',
          muted: '#64748B',
        }
      },
      fontFamily: {
        sans: ["'Gotham'", "'Helvetica Neue'", 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)',
        'card-hover': '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)',
        'elevated': '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [],
}
