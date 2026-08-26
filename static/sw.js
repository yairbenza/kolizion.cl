// Service worker de KOLIZION -- por ahora, minimo a proposito: registrarlo
// es uno de los requisitos tecnicos para que el navegador considere la app
// "instalable" (junto con manifest.json y HTTPS), pero mientras la app
// sigue cambiando seguido (varias veces por dia), un cache agresivo
// causaria mas problemas que beneficios -- el usuario veria versiones
// viejas de la app despues de cada cambio, sin saber por que. Por eso este
// service worker deja pasar TODO directo a la red, sin guardar nada.
//
// Cuando la app este mas estable, este es el lugar para agregar un cache
// real (app shell offline, etc.) -- no antes.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
