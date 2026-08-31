import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        // Mirrors the Caddyfile's reverse proxy for `yarn start` outside
        // Docker (no Caddy in front) - same default port compose
        // publishes `server` on. Override via VITE_API_URL if that's
        // remapped locally, same as the production build.
        proxy: {
            '/api': 'http://localhost:8000',
            '/dj-rest-auth': 'http://localhost:8000',
        },
    },
    build: {
        outDir: 'build',
        // MUI (~530kB) is the one dependency cleanly separable from the rest
        // of the bundle - splitting it into its own cacheable chunk lets the
        // browser fetch it in parallel and cache it independently of app
        // code. react-admin's Material-UI layer (ra-ui-materialui) imports
        // MUI components directly, so trying to *also* split react-admin out
        // produces a circular chunk (Rollup warning, worse load behavior,
        // tried and reverted) - they're architecturally coupled, not
        // separable further without route-level lazy-loading of each
        // <Resource>, a much larger change than this warning warrants.
        // 750kB reflects that realistic floor rather than the unreachable
        // default 500kB - the remaining chunk is react/react-admin/emotion/
        // react-query/app code, which splits no further without circularity.
        chunkSizeWarningLimit: 750,
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (id.includes('node_modules') && /[\\/]@mui[\\/]/.test(id)) {
                        return 'vendor-mui';
                    }
                },
            },
        },
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./src/setupTests.js'],
        // ra-ui-materialui's compiled output does `import ... from
        // '@mui/material/styles'` (a directory import, no explicit
        // index.js/exports map entry). Vite's real dev/build pipeline
        // resolves that fine via esbuild/rollup, but Vitest's default SSR
        // module runner uses Node's strict ESM resolver for externalized
        // deps, which rejects bare directory imports. Inlining these deps
        // routes them through Vite's transform pipeline instead.
        server: {
            deps: {
                inline: [/@mui\//, /ra-ui-materialui/, /react-admin/],
            },
        },
    },
});
