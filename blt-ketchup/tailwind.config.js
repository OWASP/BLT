/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: ['./*.html'],
    theme: {
      extend: {
        colors: {
          brand: {
            DEFAULT: '#E10101',
            hover:   '#B91C1C',
            light:   '#feeae9',
          },
        },
      },
    },
    plugins: [],
    // Safelist brand tokens and dynamic utility classes used via inline styles
    safelist: [
      'text-[#E10101]',
      'bg-[#E10101]',
      'border-[#E10101]',
      'bg-[#feeae9]',
      'bg-[#111827]',
      'bg-[#1F2937]',
      'dark:bg-[#111827]',
      'dark:bg-[#1F2937]',
      'border-[#E5E5E5]',
      'focus:border-red-600',
      'focus:ring-red-600',
      'hover:bg-red-700',
      'animate-pulse',
      'cursor-blink',
    ],
  };