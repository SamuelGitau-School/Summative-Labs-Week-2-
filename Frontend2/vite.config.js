import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The browser only talks to Vite; Vite forwards these paths to Flask. Everything stays
// on one origin, so the session cookie works and no CORS setup is needed.
const flask = "http://localhost:5000";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/inventory": flask, "/auth": flask } },
  test: { environment: "jsdom", globals: true, setupFiles: "./src/test/setup.js" },
});
