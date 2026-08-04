import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

const INPUT = process.env.INPUT;
if (!INPUT) {
  throw new Error("INPUT environment variable is not set");
}

// The version the app reports to its MCP host is DERIVED, never authored here.
// It used to be a literal in mcp-app-wrapper.tsx, which drifted to five minors
// behind plugin.json while nothing noticed -- the host was told 0.1.0 by an app
// installs resolved as 0.6.1. plugin.json is what the version cascade bumps, so
// it is the one source; a build that cannot read it fails loudly rather than
// shipping a guess.
const pluginManifest = new URL(
  "../.claude-plugin/plugin.json",
  import.meta.url,
);
const APP_VERSION: string = JSON.parse(
  readFileSync(pluginManifest, "utf-8"),
).version;
if (!APP_VERSION) {
  throw new Error(`no version in ${pluginManifest.pathname}`);
}

const isDevelopment = process.env.NODE_ENV === "development";

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
  plugins: [react(), viteSingleFile()],
  build: {
    sourcemap: isDevelopment ? "inline" : undefined,
    cssMinify: !isDevelopment,
    minify: !isDevelopment,

    rollupOptions: {
      input: INPUT,
    },
    outDir: "dist",
    emptyOutDir: false,
  },
});
