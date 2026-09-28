// Google TypeScript style via gts, plus React Native specifics.
// `require('gts')` is the shared flat config (as written by `gts init`).
const gts = require('gts');
const globals = require('globals');

module.exports = [
  ...gts,
  {
    ignores: [
      'node_modules/',
      '.expo/',
      'ios/',
      'android/',
      'src/api/generated/',
      'src/theme/generated/',
      '.rnstorybook/storybook.requires.ts',
      'expo-env.d.ts',
    ],
  },
  {
    // Node-side config files and scripts.
    files: ['*.js', '*.mjs', 'scripts/**/*.mjs', '.prettierrc.js'],
    languageOptions: {globals: globals.node},
    rules: {'@typescript-eslint/no-require-imports': 'off'},
  },
];
