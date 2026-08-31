// Base URL for the Django server's API. Defaults to '' (same-origin,
// relative requests) since the production build is served behind Caddy,
// which reverse-proxies /api and /dj-rest-auth to the server container
// internally (see Caddyfile) - the browser never needs to know which host
// port `server` is published on. Override with VITE_API_URL for local
// `yarn start` dev (no Caddy in front) or any setup where the API lives on
// a different origin.
export const API_URL = import.meta.env.VITE_API_URL || '';
