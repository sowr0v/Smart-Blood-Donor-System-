// Service Worker for SBDS Web Push Notifications (SBDS-47)
self.addEventListener('push', function (event) {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { title: 'Smart Blood Donor System Alert', body: event.data.text() };
    }
  }

  const title = data.title || 'Emergency Blood Alert - SBDS';
  const options = {
    body: data.body || 'A high-priority notification was dispatched to your device.',
    icon: '/static/images/drop_icon.png',
    badge: '/static/images/badge_icon.png',
    data: {
      url: data.click_url || '/admin/dashboard',
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
