/**
 * SpotMyShoot Frontend Application Library (app.js)
 */

const API_BASE = '/api/v1';

// Toast Notification System
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Unified API Fetch
async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  
  const headers = options.headers ? { ...options.headers } : {};
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Also include Bearer token from localStorage if present
  const token = localStorage.getItem('sms_access_token');
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  options.headers = headers;
  options.credentials = 'include'; // Send httpOnly cookies

  try {
    const res = await fetch(url, options);
    
    // Check unauthenticated
    if (res.status === 401) {
      localStorage.removeItem('sms_user');
      localStorage.removeItem('sms_access_token');
      // If on protected page, redirect
      const path = window.location.pathname;
      if (path.includes('owner.html') || path.includes('admin.html') || path.includes('my-bookings.html') || path.includes('checkout.html')) {
        window.location.href = `/login.html?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      }
    }

    if (res.status === 204) {
      return null;
    }

    const data = await res.json();
    if (!res.ok) {
      const err = data.detail || (data.errors ? JSON.stringify(data.errors) : 'An error occurred.');
      throw new Error(err);
    }
    return data;
  } catch (err) {
    throw err;
  }
}

// Authentication Helpers
async function fetchCurrentUser() {
  try {
    const user = await apiFetch('/auth/me');
    localStorage.setItem('sms_user', JSON.stringify(user));
    return user;
  } catch (e) {
    localStorage.removeItem('sms_user');
    localStorage.removeItem('sms_access_token');
    return null;
  }
}

function getStoredUser() {
  const raw = localStorage.getItem('sms_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

async function logout() {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } catch (e) {}
  localStorage.removeItem('sms_user');
  localStorage.removeItem('sms_access_token');
  showToast('Logged out successfully.', 'info');
  setTimeout(() => {
    window.location.href = '/login.html';
  }, 500);
}

// Header & Navigation Renderer
function renderHeader() {
  const headerEl = document.querySelector('.header');
  if (!headerEl) return;

  const user = getStoredUser();
  const currentPath = window.location.pathname;

  let navLinksHtml = `
    <li><a href="/locations.html" class="nav-link ${currentPath.includes('locations') ? 'active' : ''}">Explore Locations</a></li>
  `;

  let actionHtml = '';

  if (user) {
    if (user.role === 'admin') {
      navLinksHtml += `<li><a href="/admin.html" class="nav-link ${currentPath.includes('admin') ? 'active' : ''}">Admin Portal</a></li>`;
    } else if (user.role === 'owner') {
      navLinksHtml += `<li><a href="/owner.html" class="nav-link ${currentPath.includes('owner') ? 'active' : ''}">Owner Dashboard</a></li>`;
    } else {
      navLinksHtml += `<li><a href="/my-bookings.html" class="nav-link ${currentPath.includes('my-bookings') ? 'active' : ''}">My Shoots</a></li>`;
    }

    actionHtml = `
      <div class="notif-wrapper" id="notif-bell-btn">
        <button class="notif-bell" title="Notifications">🔔</button>
        <span class="notif-badge" id="notif-unread-count" style="display:none;">0</span>
      </div>
      <div class="user-menu">
        <div class="user-avatar" title="${user.name}">${user.name.charAt(0).toUpperCase()}</div>
        <div style="font-size: 13px;">
          <div style="font-weight: 700;">${user.name}</div>
          <div style="font-size: 11px; color: var(--text-muted); text-transform: capitalize;">${user.role} &bull; <span class="status-badge status-${user.approval_status}" style="padding: 2px 6px; font-size: 10px;">${user.approval_status}</span></div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="logout()">Logout</button>
      </div>
    `;
  } else {
    actionHtml = `
      <a href="/login.html" class="btn btn-secondary btn-sm">Log In</a>
      <a href="/register.html" class="btn btn-primary btn-sm">Sign Up</a>
    `;
  }

  headerEl.innerHTML = `
    <div class="container header-inner">
      <a href="/" class="logo">
        <span>🎬 SpotMyShoot</span>
        <span class="logo-badge">Pro</span>
      </a>
      <ul class="nav-links">
        ${navLinksHtml}
      </ul>
      <div class="nav-actions">
        ${actionHtml}
      </div>
    </div>
  `;

  if (user) {
    pollNotifications();
    setupNotificationModal();
  }
}

// Notification Polling
async function pollNotifications() {
  try {
    const data = await apiFetch('/notifications/unread-count');
    const badge = document.getElementById('notif-unread-count');
    if (badge) {
      if (data.unread_count > 0) {
        badge.innerText = data.unread_count > 9 ? '9+' : data.unread_count;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }
  } catch (e) {}
}

function setupNotificationModal() {
  const bell = document.getElementById('notif-bell-btn');
  if (!bell) return;

  bell.addEventListener('click', async () => {
    // Open notifications overlay
    let overlay = document.getElementById('notif-modal-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'notif-modal-overlay';
      overlay.className = 'modal-overlay';
      overlay.innerHTML = `
        <div class="modal">
          <div class="modal-header">
            <h3 class="modal-title">Notifications</h3>
            <button class="modal-close" onclick="closeNotifModal()">&times;</button>
          </div>
          <div id="notif-list-container" style="max-height: 400px; overflow-y: auto;">
            <p style="color: var(--text-muted); text-align: center;">Loading notifications...</p>
          </div>
          <div style="margin-top: 16px; text-align: right;">
            <button class="btn btn-secondary btn-sm" onclick="markAllNotificationsRead()">Mark all as read</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    }

    overlay.classList.add('active');
    loadNotificationsList();
  });
}

function closeNotifModal() {
  const overlay = document.getElementById('notif-modal-overlay');
  if (overlay) overlay.classList.remove('active');
}

async function loadNotificationsList() {
  const container = document.getElementById('notif-list-container');
  if (!container) return;

  try {
    const list = await apiFetch('/notifications');
    if (!list || list.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No notifications yet.</p>';
      return;
    }

    container.innerHTML = list.map(n => `
      <div style="padding: 12px; border-bottom: 1px solid var(--border); ${n.status !== 'read' ? 'background: #F8FAFC;' : ''}">
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${n.title || 'Notification'}</div>
        <div style="font-size: 13px; color: var(--text-muted);">${(n.payload && n.payload.message) || ''}</div>
        <div style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${new Date(n.created_at).toLocaleString('en-IN')}</div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<p style="color: var(--danger); text-align: center;">Failed to load: ${e.message}</p>`;
  }
}

async function markAllNotificationsRead() {
  try {
    await apiFetch('/notifications/mark-read', { method: 'POST' });
    showToast('All notifications marked as read', 'success');
    pollNotifications();
    loadNotificationsList();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

// Formatters
function formatINR(amount) {
  if (amount == null) return '₹0';
  return '₹' + Number(amount).toLocaleString('en-IN');
}

function formatISTDate(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

function formatISTTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

// Auto-run on document ready
document.addEventListener('DOMContentLoaded', async () => {
  renderHeader();
  // Refresh user state in background
  if (localStorage.getItem('sms_access_token')) {
    await fetchCurrentUser();
    renderHeader();
  }
  // Set interval for notification polling
  setInterval(() => {
    if (getStoredUser()) pollNotifications();
  }, 30000);
});
