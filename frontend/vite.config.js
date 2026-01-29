import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import { loadFrontendConfig } from "./config.js";

const frontendConfig = loadFrontendConfig();

export default defineConfig({
  plugins: [react()],
  define: {
    __KACHNA_API_URL__: JSON.stringify(frontendConfig.apiUrl ?? null),
  },
  server: {
    port: 5173,
    allowedHosts: ["kachna.hobrasoft.cz"],
  },
});
