import { defineConfig } from "vite";
import { resolve } from "node:path";
import { readdirSync } from "node:fs";

const webRoot = resolve(__dirname, "web");

function htmlInputs() {
  const inputs = {};
  for (const name of readdirSync(webRoot)) {
    if (name.endsWith(".html")) {
      inputs[name.replace(/\.html$/, "")] = resolve(webRoot, name);
    }
  }
  return inputs;
}

export default defineConfig({
  root: "web",
  publicDir: false,
  server: {
    port: 5173,
    open: "/",
    // Allow large book PDFs to download without hanging defaults
    fs: {
      allow: [".."],
    },
  },
  preview: {
    headers: {
      "Content-Disposition": "inline",
    },
  },
  build: {
    outDir: resolve(__dirname, "dist"),
    emptyOutDir: true,
    assetsInlineLimit: 0,
    rollupOptions: {
      input: htmlInputs(),
    },
  },
  plugins: [
    {
      name: "pdf-download-headers",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && req.url.includes("/assets/pdfs/") && req.url.endsWith(".pdf")) {
            const name = decodeURIComponent(req.url.split("/").pop() || "book.pdf");
            // Let browsers download when `download` attribute is used; keep viewable too
            res.setHeader("Content-Type", "application/pdf");
            res.setHeader("Content-Disposition", `inline; filename="${name}"`);
            res.setHeader("Cache-Control", "public, max-age=3600");
          }
          next();
        });
      },
    },
  ],
});
