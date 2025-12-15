/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'chat-bg': '#212121',
        'chat-sidebar': '#171717',
        'chat-input': '#2f2f2f',
        'chat-user': '#2f2f2f',
        'chat-assistant': '#212121',
        'chat-border': '#303030',
        'chat-text': '#ececf1',
        'chat-text-secondary': '#919191',
        'chat-hover': '#2f2f2f',
      },
    },
  },
  plugins: [],
}
