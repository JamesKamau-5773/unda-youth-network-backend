/**
 * Tailwind configuration exposing UNDA / UMV color tokens.
 * This file doesn't change runtime behavior by itself; run the Tailwind build
 * to generate utilities. See README below for commands.
 */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.html',
    './static/js/**/*.js',
    './static/css/**/*.css',
    './blueprints/**/*.py',
    './**/*.py'
  ],
  theme: {
    extend: {
      colors: {
        umv: {
          primary: '#0B1E3B',
          accent: '#00C2CB',
          surface: '#F8FAFC',
          dark: '#008ba3'
        },
        portal: {
          navy: '#0B1E3B',
          navyInk: '#1E293B',
          ice: '#F0F7FF',
          teal: '#00C2CB',
          tealDark: '#0090C0',
          muted: '#475569',
          subtitle: '#E0F2FE',
          surface: '#FFFFFF'
        },
        misc: {
          bodyBackground: '#F9FAFB'
        }
      },
      backgroundImage: {
        'energy-gradient': 'linear-gradient(90deg, #00C2CB 0%, #0090C0 100%)',
        'editorial-gradient': 'linear-gradient(to bottom right, #00E5FF, #00C2CB, #008ba3)'
      }
    }
  },
  plugins: []
};
