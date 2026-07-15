import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// the repo root: src/rk-tokens.css imports the design kit from /design-system,
// which sits outside this package, so the dev server has to be allowed to read it
const repoRoot = fileURLToPath(new URL("../..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    fs: { allow: [repoRoot] },
    proxy: {
      "/api": "http://127.0.0.1:8300",
      "/output": "http://127.0.0.1:8300",
    },
  },
});
