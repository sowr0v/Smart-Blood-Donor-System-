// Service Worker for SBDS Web Push Notifications (SBDS-47)
self.addEventListener('install', function (event) {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(clients.claim());
});

self.addEventListener('push', function (event) {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { title: 'Smart Blood Donor System Alert', body: event.data.text() };
    }
  }

  const notifPayload = data.notification || data;
  const dataPayload = data.data || {};

  const title = notifPayload.title || 'Emergency Blood Alert - SBDS';
  const body = notifPayload.body || 'A high-priority notification was dispatched to your device.';
  const clickUrl = dataPayload.click_url || notifPayload.click_url || '/';

  const options = {
    body: body,
    icon: notifPayload.icon || '/static/images/drop_icon.png',
    badge: notifPayload.badge || '/static/images/badge_icon.png',
    tag: dataPayload.fcm_message_id || 'sbds-push-alert',
    renotify: true,
    requireInteraction: true,
    data: {
      url: clickUrl,
      fcm_message_id: dataPayload.fcm_message_id || '',
    },
    vibrate: [200, 100, 200],
    actions: [
      { action: 'open', title: 'Open SBDS Portal' },
      { action: 'close', title: 'Dismiss' }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  if (event.action === 'close') return;

  const urlToOpen = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
