import { build } from "esbuild";

// Build server.ts
await build({
  entryPoints: ["server.ts"],
  outdir: "dist",
  bundle: true,
  platform: "node",
  format: "esm",
  external: [
    "express",
    "cors",
    "@modelcontextprotocol/*",
    "zod",
    "node:*",
  ],
});

// Build main.ts
await build({
  entryPoints: ["main.ts"],
  outfile: "dist/index.js",
  bundle: true,
  platform: "node",
  format: "esm",
  external: [
    "./server.js",
    "express",
    "cors",
    "@modelcontextprotocol/*",
    "zod",
    "node:*",
  ],
  banner: { js: "#!/usr/bin/env node" },
});

console.log("Server build complete.");
