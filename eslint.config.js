// Minimal ESLint v9 flat config (repo is CommonJS, no TS plugin installed yet).
// `npm run lint` (eslint .) passes; extend with typescript-eslint when added.
module.exports = [
  {
    ignores: ['node_modules/**', 'dist/**', 'coverage/**'],
  },
];
