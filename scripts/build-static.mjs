/**
 * Copy the static site into dist/ for Cloudflare Pages / any static host.
 * Vite is kept for local `npm run dev` only — production must preserve plain
 * HTML/CSS/JS/PDF paths (no hashed assets, no module bundling of jQuery).
 */
import { cpSync, rmSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const src = resolve(root, "web");
const dest = resolve(root, "dist");

if (!existsSync(src)) {
  console.error("Missing web/ directory");
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });
console.log(`Copied web/ → dist/`);
