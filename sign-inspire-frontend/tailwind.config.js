/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        elegant: ['Cormorant Garamond', 'Georgia', 'serif'],
        body: ['Lora', 'Georgia', 'serif'],
      },
      colors: {
        cream: { 50: '#FDFCFA', 100: '#FAF8F4', 200: '#F5F2EB', 300: '#EDE9E1' },
        stone: { 400: '#B8A99A', 500: '#9A8B7A', 600: '#7D6F5F', 700: '#5C5248' },
        ink: { 600: '#4A4541', 700: '#3D3935', 800: '#2D2A26', 900: '#1F1D1A' },
        accent: { 400: '#C4A77D', 500: '#B8956A', 600: '#9A7B52' },
      },
      boxShadow: {
        'soft': '0 2px 20px -2px rgba(45, 42, 38, 0.06)',
        'elegant': '0 4px 30px -4px rgba(45, 42, 38, 0.08)',
      },
    },
  },
  plugins: [],
}