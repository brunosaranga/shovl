import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
    globalIgnores(["dist"]),
    {
        files: ["**/*.{js,jsx}"],
        extends: [js.configs.recommended, reactHooks.configs.flat.recommended, reactRefresh.configs.vite],
        languageOptions: {
            globals: globals.browser,
            parserOptions: { ecmaFeatures: { jsx: true } },
        },
        rules: {
            "no-unused-vars": ["error", { varsIgnorePattern: "^React$" }],
        },
    },
    {
        // Providers export their hook next to the component, and routes.jsx exports config.
        files: ["src/context/**", "src/routes.jsx", "src/components/layout/NavCenter/**"],
        rules: {
            "react-refresh/only-export-components": "off",
        },
    },
]);
