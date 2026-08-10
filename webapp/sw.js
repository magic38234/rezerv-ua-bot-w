// Service Worker для PWA-режиму панелі. Головна задача — приймати Web Push
// (push-подія) і показувати системне сповіщення; кешування — мінімальне,
// лише щоб застосунок взагалі вважався "інстальованим" PWA (вимога Chrome/
// Edge для показу кнопки "Встановити" і, відповідно, для роботи Push API
// поза embedded WebView Telegram — див. services/push.py про це обмеження).

const CACHE_NAME = "radar-panel-shell-v1";
const SHELL_FILES = ["./", "./index.html", "./style.css", "./app.js", "./manifest.json"];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES).catch(() => {}))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  // Мережа за замовчуванням (панель живе даними в реальному часі, кеш — лише
  // фолбек офлайн для самої оболонки, а не для /api/* запитів).
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "Сповіщення", body: "" };
  try {
    if (event.data) payload = event.data.json();
  } catch (e) {
    payload.body = event.data ? event.data.text() : "";
  }
  const options = {
    body: payload.body || "",
    icon: "icons/icon-192.png",
    badge: "icons/icon-192.png",
    tag: payload.tag || undefined,
    data: { url: payload.url || "./" },
  };
  event.waitUntil(self.registration.showNotification(payload.title || "Сповіщення", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "./";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(targetUrl);
    })
  );
});
