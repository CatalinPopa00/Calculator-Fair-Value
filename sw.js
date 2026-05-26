// Service Worker minim pentru validarea PWA
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // Lasă browserul să rezolve cererile în mod normal
});
