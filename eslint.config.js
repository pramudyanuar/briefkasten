import typescriptParser from "@typescript-eslint/parser"
import svelteParser from "svelte-eslint-parser"

export default [
  {
    ignores: [
      "**/.svelte-kit/**",
      "**/build/**",
      "**/coverage/**",
      "**/dist/**",
      "**/generated/**",
      "**/prisma-client/**",
      "**/prisma-zod-generator/**",
    ],
  },
  {
    files: ["**/*.{js,mjs,cjs,ts,svelte}"],
    rules: {
      "no-debugger": "error",
      "no-dupe-else-if": "error",
      "no-unreachable": "error",
      "no-unsafe-finally": "error",
    },
  },
  {
    files: ["**/*.ts"],
    languageOptions: { parser: typescriptParser },
  },
  {
    files: ["**/*.svelte"],
    languageOptions: {
      parser: svelteParser,
      parserOptions: { parser: typescriptParser },
    },
  },
]
