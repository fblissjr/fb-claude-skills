import { build } from "esbuild";
import fs from "node:fs/promises";
import module from "node:module";
import { stampLine } from "./build-stamp.mjs";

// Get all Node.js builtin module names (both bare and node: prefixed)
const builtins = module.builtinModules.flatMap((m) => [m, `node:${m}`]);

// Single fully-bundled build: main.ts imports server.ts, all npm deps inlined.
// Only Node.js builtins are external. No node_modules needed at runtime.
// Uses CJS format because Express and MCP SDK deps use CommonJS internally.
// Minified because the bundle is committed: it is what a marketplace install runs.
const mode = process.env.NODE_ENV === "development" ? "development" : "production";
await build({
  entryPoints: ["main.ts"],
  outfile: "dist/index.cjs",
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node20",
  external: builtins,
  minify: mode === "production",
  banner: { js: `#!/usr/bin/env node\n${stampLine(mode)}` },
  define: {
    "import.meta.dirname": "__dirname",
    "import.meta.filename": "__filename",
  },
});

// Also emit server.d.ts for TypeScript consumers
await fs.writeFile(
  "dist/server.d.ts",
  'export { createServer } from "../server.js";\n',
);

console.log("Server build complete (fully bundled, node builtins external).");
