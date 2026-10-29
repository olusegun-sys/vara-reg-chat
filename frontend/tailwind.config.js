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
        // Brand = accent blue for user bubbles + buttons.
        // Shifted from electric blue to deep midnight cobalt: both darker AND
        // desaturated so the user bubble reads as "my message" in a dark theme,
        // not as a bright highlight. Hue also shifted toward navy (cooler).
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#1A2E5C',   // hover state — very dark navy
          600: '#1E3A6E',   // user bubble + New Session button + send button
          700: '#152849',   // pressed state — almost black-navy
          900: '#0F1A30',   // unused, kept for future
        },
        // Luxury = base surfaces. Near-black navy throughout.
        luxury: {
          DEFAULT: '#080B12', // sidebar
          light: '#0F1218',   // main chat background
          accent: '#3B6DB8',  // muted steel blue (was #5EAAFF)
        },
      },
      boxShadow: {
        'premium': '0 4px 20px -2px rgba(0, 0, 0, 0.4)',
        'glow': '0 0 15px -3px rgba(59, 109, 184, 0.25)',  // matches new accent
      }
    },
  },
  plugins: [],
};