// Motorpuls service worker: bara Web Push (push och notificationclick). Ingen cache och ingen fetch-hanterare,
// så sidorna laddas precis som utan service worker. Registreras först när läsaren har tryckt "Ja tack" och sagt ja i webbläsaren.
// Väntat innehåll i push-meddelandet (JSON): {"title": "...", "body": "...", "url": "/artikel/<slug>/", "tag": "<slug>"}
self.addEventListener('push', (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch { d = { body: event.data ? event.data.text() : '' }; }
  event.waitUntil(self.registration.showNotification(d.title || 'Motorpuls', {
    body: d.body || 'Ny artikel på Motorpuls',
    icon: '/favicon/android-chrome-192.png',
    badge: '/favicon/favicon-32.png',
    tag: d.tag || 'motorpuls',
    lang: 'sv',
    data: { url: d.url || '/' }
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  let url = new URL((event.notification.data && event.notification.data.url) || '/', self.location.origin);
  if (url.origin !== self.location.origin) url = new URL('/', self.location.origin); // bara egna sidor
  event.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const open = wins.find((c) => c.url === url.href);
    if (open && 'focus' in open) return open.focus();
    return self.clients.openWindow(url.href);
  })());
});
