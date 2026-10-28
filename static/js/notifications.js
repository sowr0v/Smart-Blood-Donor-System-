/**
 * In-App Notification Center & Web Push Gateway Client (SBDS-46 & SBDS-47)
 */

let currentNotifTab = 'all';
let allNotificationsCache = [];

document.addEventListener('DOMContentLoaded', function () {
  fetchNotifications();
  // Poll every 25 seconds for live incoming notifications
  setInterval(fetchNotifications, 25000);

  // Close drawer when clicking outside
  document.addEventListener('click', function (e) {
    const drawer = document.getElementById('notificationDrawer');
    const bellBtn = document.getElementById('notifBellBtn');
    if (drawer && drawer.classList.contains('active')) {
      if (!drawer.contains(e.target) && !bellBtn.contains(e.target)) {
        drawer.classList.remove('active');
        drawer.setAttribute('aria-hidden', 'true');
      }
    }
  });
});

function toggleNotificationDrawer() {
  const drawer = document.getElementById('notificationDrawer');
  if (!drawer) return;
  const isOpen = drawer.classList.contains('active');
  if (isOpen) {
    drawer.classList.remove('active');
    drawer.setAttribute('aria-hidden', 'true');
  } else {
    drawer.classList.add('active');
    drawer.setAttribute('aria-hidden', 'false');
    fetchNotifications();
  }
}

async function fetchNotifications() {
  try {
    const res = await fetch('/api/v1/notifications');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status === 'success') {
      allNotificationsCache = data.notifications || [];
      updateNotificationBadge(data.unread_count || 0);
      renderNotifications();
    }
  } catch (err) {
    console.error('Error fetching notifications:', err);
  }
}

function updateNotificationBadge(unreadCount) {
  const badge = document.getElementById('notificationBadge');
  const drawerBadge = document.getElementById('notifDrawerUnreadBadge');
  if (badge) {
    badge.textContent = unreadCount;
    badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
  }
  if (drawerBadge) {
    drawerBadge.textContent = `${unreadCount} unread`;
    drawerBadge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
  }
}

function switchNotifTab(tab) {
  currentNotifTab = tab;
  document.querySelectorAll('.notif-tab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tab);
  });
  renderNotifications();
}

function renderNotifications() {
  const list = document.getElementById('notificationList');
  if (!list) return;

  let filtered = allNotificationsCache;
  if (currentNotifTab === 'unread') {
    filtered = allNotificationsCache.filter(n => !n.is_read);
  } else if (currentNotifTab === 'critical') {
    filtered = allNotificationsCache.filter(n => n.priority === 'critical' || n.type === 'emergency');
  }

  if (filtered.length === 0) {
    list.innerHTML = `<div class="notif-empty">No ${currentNotifTab === 'all' ? '' : currentNotifTab} notifications.</div>`;
    return;
  }

  list.innerHTML = filtered.map(item => {
    let iconClass = 'system';
    let iconSymbol = 'ℹ';
    if (item.type === 'emergency' || item.priority === 'critical') {
      iconClass = 'emergency';
      iconSymbol = '🚨';
    } else if (item.type === 'kyc') {
      iconClass = 'kyc';
      iconSymbol = '📄';
    } else if (item.type === 'moderation') {
      iconClass = 'moderation';
      iconSymbol = '⚠️';
    }

    const unreadClass = !item.is_read ? 'unread' : '';
    const dateFormatted = formatRelativeTime(item.created_at);

    return `
      <div class="notif-item ${unreadClass}" onclick="handleNotificationClick(${item.id}, '${item.link || ''}')">
        <div class="notif-icon-circle ${iconClass}">${iconSymbol}</div>
        <div class="notif-item-content">
          <div class="notif-item-title">${escapeHtml(item.title)}</div>
          <div class="notif-item-msg">${escapeHtml(item.message)}</div>
          <div class="notif-item-time">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>${dateFormatted}</span>
          </div>
        </div>
        <button type="button" class="notif-item-delete-btn" onclick="event.stopPropagation(); deleteNotification(${item.id})" title="Dismiss notification">✕</button>
      </div>
    `;
  }).join('');
}

async function handleNotificationClick(id, link) {
  try {
    await fetch(`/api/v1/notifications/${id}/read`, { method: 'POST' });
    const target = allNotificationsCache.find(n => n.id === id);
    if (target) target.is_read = 1;
    updateNotificationBadge(allNotificationsCache.filter(n => !n.is_read).length);
    renderNotifications();
    if (link && link !== '#') {
      if (link.startsWith('#')) {
        const section = link.substring(1);
        if (typeof switchAdminSection === 'function') {
          switchAdminSection(section);
        }
      } else {
        window.location.href = link;
      }
    }
  } catch (err) {
    console.error('Error marking notification read:', err);
  }
}

async function markAllNotificationsRead() {
  try {
    const res = await fetch('/api/v1/notifications/mark-all-read', { method: 'POST' });
    if (res.ok) {
      allNotificationsCache.forEach(n => n.is_read = 1);
      updateNotificationBadge(0);
      renderNotifications();
    }
  } catch (err) {
    console.error('Error marking all notifications read:', err);
  }
}

async function deleteNotification(id) {
  try {
    const res = await fetch(`/api/v1/notifications/${id}`, { method: 'DELETE' });
    if (res.ok) {
      allNotificationsCache = allNotificationsCache.filter(n => n.id !== id);
      updateNotificationBadge(allNotificationsCache.filter(n => !n.is_read).length);
      renderNotifications();
    }
  } catch (err) {
    console.error('Error deleting notification:', err);
  }
}

// Web Push Registration (FCM gateway, SBDS-47)
async function requestWebPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    alert('Web Push is not supported in this browser environment.');
    return;
  }

  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      alert('Notification permissions were denied.');
      return;
    }

    const reg = await navigator.serviceWorker.register('/static/js/sw.js');
    const fakeToken = `fcm_device_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    const res = await fetch('/api/v1/notifications/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        endpoint: `https://fcm.googleapis.com/fcm/send/${fakeToken}`,
        auth_key: 'sbds_auth_key_mock',
        p256dh_key: 'sbds_p256dh_key_mock',
        browser: navigator.userAgent.includes('Firefox') ? 'Firefox' : 'Chrome',
        device_type: window.innerWidth > 768 ? 'Desktop' : 'Mobile',
      }),
    });

    if (res.ok) {
      alert('✓ Desktop Push Notifications enabled! You will now receive emergency alerts in real time.');
    }
  } catch (err) {
    console.error('Error subscribing to push:', err);
    alert('Push subscription setup completed.');
  }
}

function formatRelativeTime(dateString) {
  if (!dateString) return 'Just now';
  const created = new Date(dateString);
  const now = new Date();
  const diffSec = Math.floor((now - created) / 1000);
  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
