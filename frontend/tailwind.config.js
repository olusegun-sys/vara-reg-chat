/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Lora', 'serif'],
      },
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6', 
          600: '#2563eb', 
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        luxury: {
          DEFAULT: '#0F172A', // Deep Midnight Navy (Sidebar)
          light: '#1E293B',   // Lighter navy for the main chat background
          accent: '#38BDF8',  // Sky Blue highlight
        },
      },
      boxShadow: {
        'premium': '0 4px 20px -2px rgba(15, 23, 42, 0.2)',
        'glow': '0 0 15px -3px rgba(56, 189, 248, 0.3)',
      }
    },
  },
  plugins: [],
};