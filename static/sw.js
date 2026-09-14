/* SkillPilot Service Worker
 * Strategy:
 *   - HTML & API requests: NETWORK-ONLY (never cached). This avoids leaking
 *     authenticated/admin pages on shared devices after logout, and ensures
 *     CSRF tokens / role-based UIs are always fresh.
 *   - /static/* and image/font/css/js assets: cache-first (safe — public).
 * The SW still gives us installability + faster static loads.
 * Versioned cache name — bump CACHE_VERSION whenever the shell changes.
 */
const CACHE_VERSION = 'skp-v5';
const STATIC_CACHE  = `skp-static-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  '/static/manifest.json',
  '/static/css/design-system.css',
  '/static/js/skp-safe.js',
  '/static/images/aiac-logo.png',
  '/static/images/SkillPilot.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      cache.addAll(PRECACHE_URLS).catch(() => null)
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function isHtmlRequest(req) {
  return req.mode === 'navigate' ||
         (req.headers.get('accept') || '').includes('text/html');
}

function isApiRequest(url) {
  return url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/api/');
}

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/') ||
         /\.(css|js|woff2?|ttf|svg|png|jpe?g|webp|ico)$/i.test(url.pathname);
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Never cache or intercept auth-sensitive flows
  if (url.pathname.startsWith('/admin/login') ||
      url.pathname.startsWith('/api/auth/') ||
      url.pathname.startsWith('/reset-password')) {
    return;
  }

  if (isApiRequest(url) || isHtmlRequest(req)) {
    // Network-only. We deliberately do NOT cache or fall back to a stale
    // copy — authenticated pages must never be served after logout, and
    // API responses must always reflect current session/role state.
    event.respondWith(
      fetch(req).catch(() => new Response(
        'You are offline. Reconnect to continue.',
        { status: 503, statusText: 'Offline',
          headers: { 'Content-Type': 'text/plain; charset=utf-8' } }
      ))
    );
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((resp) => {
        const copy = resp.clone();
        if (resp.ok) {
          caches.open(STATIC_CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return resp;
      }).catch(() => cached))
    );
  }
});
