/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
  border: 'hsl(var(--border))',
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
        zinc: {
          950: '#09090b',
        },
      },
    },
  },
  plugins: [],
}