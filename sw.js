/* Para usar en el campo las herramientas de exposición larga sin cobertura.
   Solo se ocupa de esas páginas, de sus iconos y de las tipografías que cargan;
   todo lo demás del sitio pasa de largo, sin tocar.

   Las páginas se piden primero a la red, para que siempre salga la última versión
   cuando hay conexión, y se sirven de la copia guardada cuando no la hay. */
const CACHE = 'campo-v1';
const PAGINAS = [
  'exposicion-larga.html',
  'manual-exposicion-larga.html',
  'reciprocidad.html',
  'filtro-temporal.html',
  'icons/exposicion-larga-180.png',
  'icons/manual-exposicion-larga-180.png',
  'icons/reciprocidad-180.png',
  'icons/filtro-temporal-180.png'
];
const RUTAS = PAGINAS.map(p => new URL(p, self.location).pathname);

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      /* una a una: si falta alguna, las demás se guardan igual */
      .then(c => Promise.all(PAGINAS.map(p => c.add(new Request(p, { cache: 'reload' })).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k.startsWith('campo-') && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const pet = e.request;
  if (pet.method !== 'GET') return;
  const url = new URL(pet.url);

  /* las páginas de campo: red primero, copia guardada si no hay red */
  if (url.origin === self.location.origin && RUTAS.indexOf(url.pathname) >= 0) {
    e.respondWith(
      fetch(pet)
        .then(r => {
          if (r && r.ok) { const copia = r.clone(); caches.open(CACHE).then(c => c.put(url.pathname, copia)); }
          return r;
        })
        .catch(() => caches.match(url.pathname).then(r => r || Response.error()))
    );
    return;
  }

  /* tipografías de Google: lo guardado primero, y se refresca por detrás */
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    e.respondWith(
      caches.open(CACHE).then(c => c.match(pet).then(guardada => {
        const red = fetch(pet).then(r => { if (r && (r.ok || r.type === 'opaque')) c.put(pet, r.clone()); return r; });
        if (guardada) { red.catch(() => {}); return guardada; }
        return red;
      }))
    );
  }
});
