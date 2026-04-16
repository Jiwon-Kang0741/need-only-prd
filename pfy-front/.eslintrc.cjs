module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'airbnb-base',
    'airbnb-typescript/base',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:prettier/recommended',
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    project: ['./tsconfig.json'],
    extraFileExtensions: ['.vue'],
    ecmaVersion: 2024,
    sourceType: 'module',
  },
  plugins: ['vue', '@typescript-eslint', 'prettier', 'simple-import-sort'],
  ignorePatterns: [
    '**/*.md',
    'dist',
    'node_modules',
    '.eslintrc.cjs',
    'vite.config.ts',
  ],
  rules: {
    semi: ['error', 'always'],
    'linebreak-style': ['error', 'unix'], // 또는 "windows"
    'no-var': 'error',
    'prefer-const': ['error', { destructuring: 'all' }],
    indent: ['error', 2, { SwitchCase: 1 }],
    quotes: [
      'error',
      'single',
      { allowTemplateLiterals: true, avoidEscape: true },
    ],
    camelcase: ['error', { properties: 'always' }],
    'import/extensions': [
      'error',
      'ignorePackages',
      { js: 'never', ts: 'never', vue: 'never' },
    ],
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-proto': 'error',
    'prettier/prettier': [
      'error',
      {
        singleQuote: true,
      },
    ],
    'no-useless-escape': 'off',
    'simple-import-sort/imports': 'error',
    'simple-import-sort/exports': 'error',

    // 문제된 룰들 명시
    '@typescript-eslint/lines-between-class-members': 'off',
    '@typescript-eslint/no-throw-literal': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
    'import/prefer-default-export': 'off',
    'vue/attribute-hyphenation': 'off',
    'vue/multi-word-component-names': 'off',
    'no-console': 'off',
  },
  settings: {
    'import/resolver': {
      typescript: {},
    },
  },
  overrides: [
    {
      files: ['**/src/mocks/**'],
      rules: {
        'import/no-extraneous-dependencies': 'off',
      },
    },
  ],
};
