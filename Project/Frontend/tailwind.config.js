/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#188a8d', // Use your primary color from Figma
        background: '#f4f4f9',
        // Add any other colors from your Figma design here.
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        // Add any other font families as needed.
      },
      spacing: {
        // Define spacing units if your design calls for custom ones.
        '72': '18rem',
        '84': '21rem',
        '96': '24rem',
      },
    },
  },
  plugins: [],
};

