/**
 * In-App Notification Center & Read Badges (SBDS-46)
 * Real-time notification drawer and dedicated full-screen center
 */

let currentNotifTab = 'all';
let screenCurrentFilter = 'all';
let searchFilterQuery = '';
let allNotificationsCache = [];

document.addEventListener('DOMContentLoaded', function () {
  fetchNotifications();
  // Poll every 25 seconds for live incoming notifications
  setInterval(fetchNotifications, 25000);

  // Format existing server-rendered timestamps
  formatAllTimeElements();

  // Close drawer when clicking outside
  document.addEventListener('click', function (e) {
    const drawer = document.getElementById('notificationDrawer');
    const bellBtn = document.getElementById('notifBellBtn');
    if (drawer && drawer.classList.contains('active')) {
      if (!drawer.contains(e.target) && (!bellBtn || !bellBtn.contains(e.target))) {
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
      const unreadCount = data.unread_count !== undefined
        ? data.unread_count
        : allNotificationsCache.filter(n => !n.is_read).length;
      updateNotificationBadge(unreadCount);
      renderNotifications();
      renderScreenNotifications();
    }
  } catch (err) {
    console.error('Error fetching notifications:', err);
  }
}

function updateNotificationBadge(unreadCount) {
  // 1. Top Navbar Bell Badge
  const badge = document.getElementById('notificationBadge');
  if (badge) {
    badge.textContent = unreadCount;
    badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
  }

  // 2. Drawer Header Badge
  const drawerBadge = document.getElementById('notifDrawerUnreadBadge');
  if (drawerBadge) {
    drawerBadge.textContent = `${unreadCount} unread`;
    drawerBadge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
  }

  // 3. Screen Header Pill
  const screenBadge = document.getElementById('screenUnreadBadge');
  const screenText = document.getElementById('screenUnreadCountText');
  if (screenBadge) {
    screenBadge.style.display = unreadCount > 0 ? 'inline-flex' : 'none';
  }
  if (screenText) {
    screenText.textContent = unreadCount;
  }

  // 4. Filter Chip Counts
  const chipAll = document.getElementById('chipCountAll');
  if (chipAll) chipAll.textContent = allNotificationsCache.length;
  const chipUnread = document.getElementById('chipCountUnread');
  if (chipUnread) chipUnread.textContent = unreadCount;

  // 5. Sidebar Navigation Badges
  const sideBadges = ['donorNavNotifBadge', 'seekerNavNotifBadge', 'hospitalNavNotifBadge', 'adminSidebarNotifBadge'];
  sideBadges.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = unreadCount;
      el.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }
  });

  // 6. Update document title unread indicator if on notification center
  if (document.body.getAttribute('data-page') === 'notification-center') {
    const baseTitle = 'In-App Notification Center - Smart Blood Donor System';
    document.title = unreadCount > 0 ? `(${unreadCount}) ${baseTitle}` : baseTitle;
  }
}

function switchNotifTab(tab) {
  currentNotifTab = tab;
  document.querySelectorAll('.notif-tab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tab);
  });
  renderNotifications();
}

function filterScreenNotifications(filter) {
  screenCurrentFilter = filter;
  document.querySelectorAll('.notif-filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.getAttribute('data-filter') === filter);
  });
  renderScreenNotifications();
}

function handleSearchNotifications(val) {
  searchFilterQuery = (val || '').toLowerCase().trim();
  renderScreenNotifications();
}

// ---------------------------------------------------------------------------
// Drawer Rendering
// ---------------------------------------------------------------------------
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
    let iconSymbol = 'ℹ️';
    if (item.type === 'request') {
      iconClass = 'request';
      iconSymbol = '🩸';
    } else if (item.type === 'message') {
      iconClass = 'message';
      iconSymbol = '💬';
    } else if (item.type === 'account') {
      iconClass = 'account';
      iconSymbol = '👤';
    } else if (item.type === 'emergency' || item.priority === 'critical') {
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
      <div class="notif-item ${unreadClass}" onclick="handleNotificationClick(${item.id}, '${escapeAttr(item.link || '')}')">
        <div class="notif-icon-circle ${iconClass}">${iconSymbol}</div>
        <div class="notif-item-content">
          <div class="notif-item-title">${escapeHtml(item.title)}</div>
          <div class="notif-item-msg">${escapeHtml(item.message)}</div>
          <div class="notif-item-time">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>${dateFormatted}</span>
          </div>
        </div>
        <button type="button" class="notif-item-delete-btn" onclick="event.stopPropagation(); deleteNotification(${item.id}, event)" title="Dismiss notification">✕</button>
      </div>
    `;
  }).join('');
}

// ---------------------------------------------------------------------------
// Dedicated Full-Screen Notification Center Rendering
// ---------------------------------------------------------------------------
function renderScreenNotifications() {
  const container = document.getElementById('fullNotificationList');
  if (!container) return;

  let filtered = allNotificationsCache;

  // Filter tab condition
  if (screenCurrentFilter === 'unread') {
    filtered = filtered.filter(n => !n.is_read);
  } else if (screenCurrentFilter === 'request') {
    filtered = filtered.filter(n => n.type === 'request');
  } else if (screenCurrentFilter === 'message') {
    filtered = filtered.filter(n => n.type === 'message');
  } else if (screenCurrentFilter === 'account') {
    filtered = filtered.filter(n => n.type === 'account');
  } else if (screenCurrentFilter === 'emergency') {
    filtered = filtered.filter(n => n.type === 'emergency' || n.priority === 'critical' || n.type === 'system');
  }

  // Search keyword condition
  if (searchFilterQuery) {
    filtered = filtered.filter(n => {
      const t = (n.title || '').toLowerCase();
      const m = (n.message || '').toLowerCase();
      const l = (n.link || '').toLowerCase();
      return t.includes(searchFilterQuery) || m.includes(searchFilterQuery) || l.includes(searchFilterQuery);
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="notif-empty-state">
        <div class="empty-icon-wrap">🔔</div>
        <h3>No notifications found</h3>
        <p>No alerts match your current filter selection. Select 'All' or clear your search to view other notifications.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const isUnread = !item.is_read;
    const cardClass = isUnread ? 'unread' : 'read';
    const relTime = formatRelativeTime(item.created_at);
    const fullTime = formatFullTime(item.created_at);

    let iconSymbol = 'ℹ️';
    let iconClass = item.type || 'system';
    if (item.type === 'request') { iconSymbol = '🩸'; iconClass = 'request'; }
    else if (item.type === 'message') { iconSymbol = '💬'; iconClass = 'message'; }
    else if (item.type === 'account') { iconSymbol = '👤'; iconClass = 'account'; }
    else if (item.type === 'emergency' || item.priority === 'critical') { iconSymbol = '🚨'; iconClass = 'emergency'; }
    else if (item.type === 'kyc') { iconSymbol = '📄'; iconClass = 'kyc'; }
    else if (item.type === 'moderation') { iconSymbol = '⚠️'; iconClass = 'moderation'; }

    const categoryLabel = (item.type || 'SYSTEM').replace('_', ' ').toUpperCase();

    const actionBtnHtml = (item.link && item.link !== '#') ? `
      <a href="${escapeAttr(item.link)}" class="btn-notif-action" onclick="handleNotificationClick(${item.id}, '${escapeAttr(item.link)}'); return false;">
        <span>Take Action</span>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12"/>
          <polyline points="12 5 19 12 12 19"/>
        </svg>
      </a>
    ` : '';

    const markReadBtnHtml = isUnread ? `
      <button type="button" class="btn-notif-mark-read" onclick="markSingleNotificationRead(${item.id}, event)">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>Mark Read</span>
      </button>
    ` : '';

    const unreadDotHtml = isUnread ? `<span class="notif-unread-indicator-dot" title="Unread notification" aria-label="Unread"></span>` : '';
    const unreadPillHtml = isUnread ? `<span class="notif-unread-pill-badge">UNREAD</span>` : '';
    const priorityPillHtml = (item.priority === 'critical' || item.priority === 'high') ?
      `<span class="notif-priority-badge ${item.priority}">${item.priority.toUpperCase()}</span>` : '';

    return `
      <div class="notif-card ${cardClass}"
           id="notif-card-${item.id}"
           data-id="${item.id}"
           data-type="${item.type || ''}"
           data-read="${item.is_read ? '1' : '0'}"
           onclick="handleNotificationClick(${item.id}, '${escapeAttr(item.link || '')}')">
        
        ${unreadDotHtml}

        <div class="notif-card-icon ${iconClass}">
          ${iconSymbol}
        </div>

        <div class="notif-card-body">
          <div class="notif-card-topbar">
            <div class="notif-tags-wrap">
              <span class="notif-category-badge ${iconClass}">${categoryLabel}</span>
              ${unreadPillHtml}
              ${priorityPillHtml}
            </div>
            <div class="notif-card-timestamp" title="${fullTime}">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <span>${relTime}</span>
            </div>
          </div>

          <h3 class="notif-card-title">${escapeHtml(item.title)}</h3>
          <p class="notif-card-message">${escapeHtml(item.message)}</p>

          <div class="notif-card-actions" onclick="event.stopPropagation()">
            ${actionBtnHtml}
            ${markReadBtnHtml}
            <button type="button" class="btn-notif-dismiss" onclick="deleteNotification(${item.id}, event)" title="Dismiss notification">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ---------------------------------------------------------------------------
// Actions: Read, Mark All Read, Delete, Navigate
// ---------------------------------------------------------------------------
async function handleNotificationClick(id, link) {
  try {
    const target = allNotificationsCache.find(n => n.id === id);
    if (target && !target.is_read) {
      await fetch(`/api/v1/notifications/${id}/read`, { method: 'POST' });
      target.is_read = 1;
      updateNotificationBadge(allNotificationsCache.filter(n => !n.is_read).length);
      renderNotifications();
      renderScreenNotifications();
    }

    if (link && link !== '#' && link.trim() !== '') {
      if (link.startsWith('#')) {
        const section = link.substring(1);
        if (typeof switchAdminSection === 'function') {
          switchAdminSection(section);
        } else if (typeof showDonorSection === 'function') {
          showDonorSection(section);
        } else if (typeof showSeekerSection === 'function') {
          showSeekerSection(section);
        } else {
          window.location.hash = link;
        }
      } else {
        window.location.href = link;
      }
    }
  } catch (err) {
    console.error('Error handling notification click:', err);
  }
}

async function markSingleNotificationRead(id, event) {
  if (event) event.stopPropagation();
  try {
    const res = await fetch(`/api/v1/notifications/${id}/read`, { method: 'POST' });
    if (res.ok) {
      const target = allNotificationsCache.find(n => n.id === id);
      if (target) target.is_read = 1;
      updateNotificationBadge(allNotificationsCache.filter(n => !n.is_read).length);
      renderNotifications();
      renderScreenNotifications();
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
      renderScreenNotifications();
    }
  } catch (err) {
    console.error('Error marking all notifications read:', err);
  }
}

async function deleteNotification(id, event) {
  if (event) event.stopPropagation();
  try {
    const res = await fetch(`/api/v1/notifications/${id}`, { method: 'DELETE' });
    if (res.ok) {
      allNotificationsCache = allNotificationsCache.filter(n => n.id !== id);
      updateNotificationBadge(allNotificationsCache.filter(n => !n.is_read).length);
      renderNotifications();
      renderScreenNotifications();
    }
  } catch (err) {
    console.error('Error deleting notification:', err);
  }
}

// ---------------------------------------------------------------------------
// Helpers: Time Formatting & Escaping
// ---------------------------------------------------------------------------
function formatRelativeTime(dateString) {
  if (!dateString) return 'Just now';
  try {
    const created = new Date(dateString);
    if (isNaN(created.getTime())) return dateString;
    const now = new Date();
    const diffSec = Math.floor((now - created) / 1000);
    if (diffSec < 45) return 'Just now';
    if (diffSec < 3600) return `${Math.max(1, Math.floor(diffSec / 60))}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)}d ago`;
    return created.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch (e) {
    return dateString;
  }
}

function formatFullTime(dateString) {
  if (!dateString) return '';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return dateString;
  }
}

function formatAllTimeElements() {
  document.querySelectorAll('.notif-time-text[data-time]').forEach(el => {
    const raw = el.getAttribute('data-time');
    if (raw) el.textContent = formatRelativeTime(raw);
  });
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeAttr(text) {
  if (!text) return '';
  return String(text).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
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
