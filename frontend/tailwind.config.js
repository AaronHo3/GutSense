/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Instrument Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        mono: ['Spline Sans Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        // Editorial paper + ink
        paper: '#F4F1EA',     // warm newsprint background
        surface: '#FCFBF8',   // card / panel
        ink: '#1B1A17',       // near-black warm
        muted: '#56524A',     // secondary text
        faint: '#8C8779',     // tertiary / labels
        line: '#E4DFD3',      // hairline
        line2: '#D2CCBD',     // stronger hairline
        // Clinical signal palette (reserved for risk only)
        low: '#2F6B4F',       // forest — low risk
        elevated: '#9A7A24',  // ochre — elevated
        high: '#B35C33',      // terracotta — high
        critical: '#9E2B25',  // brick — critical
      },
      letterSpacing: {
        eyebrow: '0.18em',
      },
    },
  },
  plugins: [],
}
