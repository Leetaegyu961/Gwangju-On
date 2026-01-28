/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./screens/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                'trust-blue': {
                    DEFAULT: '#0066FF',
                    light: '#E6F0FF',
                    dark: '#0052CC',
                }
            },
            boxShadow: {
                'premium': '0 20px 50px rgba(0, 0, 0, 0.05)',
            }
        },
    },
    plugins: [],
}
