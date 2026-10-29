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
        // Brand = the accent blue used for user bubbles + send button.
        // Darkened from electric blue (#2563eb) to deep cobalt (#1d4ed8) so the
        // user bubble reads as "my message" without lighting up the whole screen.
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#1e40af',   // hover state — deep cobalt
          600: '#1d4ed8',   // user bubble + send button — deep navy cobalt
          700: '#1e3a8a',   // pressed state
          900: '#172554',   // darkest shade, unused but kept for future
        },
        // Luxury = the near-black base surfaces.
        // Tightened the gap between DEFAULT and light so the whole app reads as
        // one dark surface (DeepSeek style). Previously #0F172A -> #1E293B was too
        // big a jump and made the chat area feel "bright" inside a dark room.
        luxury: {
          DEFAULT: '#080B12', // near-black navy (sidebar)
          light: '#0F1218',   // main chat background — only ~7% lighter than sidebar
          accent: '#5EAAFF',  // muted blue highlight (was sky #38BDF8)
        },
      },
      boxShadow: {
        'premium': '0 4px 20px -2px rgba(0, 0, 0, 0.4)',
        'glow': '0 0 15px -3px rgba(94, 170, 255, 0.25)',
      }
    },
  },
  plugins: [],
};