# @snapback/shared

Framework-agnostic code shared by the SnapBack apps. Authored as plain ESM
(`.js`) with sibling TypeScript declarations (`.d.ts`) and no build step.

- **zoom-app** imports it through the Vite/TS path alias `@snapback/shared`
  (configured in `apps/zoom-app/vite.config.ts` and `tsconfig.json`).
- **meet-extension** has no bundler, so the pure runtime modules are copied into
  `apps/meet-extension/src/shared/` by `scripts/sync-shared.mjs` (run via
  `npm run sync:shared` at the repo root) and imported with a relative path.

Keep everything here dependency-free and free of environment- or
platform-specific APIs (no Vite `import.meta.env`, no `chrome.*`).
