/* ============================================================
   Plant Green Inertia LMS — Main JavaScript
   ============================================================ */

// ── API Helper ────────────────────────────────────────────
const api = {
  async get(url) {
    const res = await fetch(url);
    if (res.status === 401) { window.location.href = '/login'; return null; }
    return res.json();
  },
  async post(url, data) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }
};

// ── Filter Tabs ────────────────────────────────────────────

function setActiveTab(btn) {
  btn.closest('.filter-tabs').querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
}
// Auto-wire all filter tabs on every page
document.querySelectorAll('.filter-tabs').forEach(function(row) {
  row.querySelectorAll('.tab').forEach(function(btn) {
    btn.addEventListener('click', function() {
      row.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});
// ── Page Filter Functions ─────────────────────────────────

// MY COURSES
function filterCourses(filter, btn) {
  document.querySelectorAll('.filter-tabs .tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const map = {
    all:        allCourses,
    enrolled:   allCourses.filter(c => c.enroll_status),
    inprogress: allCourses.filter(c => c.enroll_status && (c.progress_percent || 0) < 100),
    completed:  allCourses.filter(c => c.enroll_status && (c.progress_percent || 0) === 100),
  };
  renderCourses(map[filter] || allCourses);
}



// LEADERBOARD
function filterLeaderboard(period, btn) {
  document.querySelectorAll('.filter-tabs .tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (typeof loadLeaderboard === 'function') loadLeaderboard(period);
}

// NOTIFICATIONS


// ── Toast Notifications ───────────────────────────────────
const toast = {
  container: null,
  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },
  show(title, message, type = 'info') {
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `
      <div class="toast-icon">${icons[type] || '📢'}</div>
      <div class="toast-text">
        <div class="toast-title">${title}</div>
        <div class="toast-msg">${message}</div>
      </div>
    `;
    this.container.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateY(10px)'; t.style.transition = '0.3s'; setTimeout(() => t.remove(), 300); }, 3500);
  }
};

// ── Sidebar & Navigation ──────────────────────────────────
// Call this once on every page load
async function loadNavCounts() {
    try {
        const res = await fetch('/api/nav-counts');
        const counts = await res.json();

        setBadge('nav-courses',       counts.courses);
        setBadge('nav-assignments',   counts.assignments);
        setBadge('nav-quiz',          counts.quiz);
        setBadge('nav-notifications', counts.notifications);
        setBadge('nav-schedule',      counts.schedule);
    } catch (e) {
        console.error('nav-counts failed', e);
    }
}

function setBadge(navId, count) {
    const el = document.getElementById(navId);
    if (!el) return;
    let badge = el.querySelector('.nav-badge');
    if (count > 0) {
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'nav-badge';
            el.appendChild(badge);
        }
        badge.textContent = count > 99 ? '99+' : count;
    } else {
        if (badge) badge.remove();  // hide badge when count is 0
    }
}

// Run on load
loadNavCounts();

const sidebar = {
  el: null,
  overlay: null,

  init() {
    this.el = document.getElementById('sidebar');
    this.overlay = document.getElementById('sidebar-overlay');
    const hamburger = document.getElementById('hamburger');

    if (hamburger) hamburger.addEventListener('click', () => this.toggle());
    if (this.overlay) this.overlay.addEventListener('click', () => this.close());

    // Set active nav item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
      const href = item.getAttribute('href') || '';
      if (href === currentPath || (currentPath.startsWith(href) && href !== '/')) {
        item.classList.add('active');
      }
    });

    this.loadUserInfo();
    this.loadNotifCount();
    this.loadStorage();
  },

  toggle() {
    this.el.classList.toggle('open');
    if (this.overlay) {
      this.overlay.style.display = this.el.classList.contains('open') ? 'block' : 'none';
    }
  },

  close() {
    this.el.classList.remove('open');
    if (this.overlay) this.overlay.style.display = 'none';
  },

  async loadUserInfo() {
    const user = await api.get('/api/user/me');
    if (!user) return;

    // Avatar initials
    const initials = user.full_name.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase();
    // document.querySelectorAll('.sidebar-avatar').forEach(el => el.textContent = initials);
    const avatarEl = document.querySelector('.sidebar-avatar');
    if (user.avatar_url) {
       avatarEl.innerHTML = `<img src="${user.avatar_url}" style="width:100%;height:100%;object-fit:cover;border-radius:50%">`;
    } else {
       avatarEl.textContent = initials;
    }
    document.querySelectorAll('.sidebar-username').forEach(el => el.textContent = user.full_name);
    document.querySelectorAll('.sidebar-role').forEach(el => el.textContent = `Web Dev (Full Stack) · Lv${user.level}`);

    // XP bar
    const pct = Math.round((user.xp / user.xp_max) * 100);
    document.querySelectorAll('.xp-fill').forEach(el => el.style.width = pct + '%');
    document.querySelectorAll('.xp-label-text').forEach(el => el.textContent = `${user.xp} / ${user.xp_max} XP`);

    // Streak badge in topbar
    const streakBadge = document.querySelector('.streak-count');
    if (streakBadge) streakBadge.textContent = user.streak_days;

    // Dark mode
    if (user.dark_mode) document.documentElement.setAttribute('data-theme', 'dark');
  },

  async loadNotifCount() {
    const data = await api.get('/api/notifications');
    if (!data) return;
    const unread = data.filter(n => !n.is_read).length;
    const badge = document.getElementById('notif-badge');
    if (badge) {
      badge.textContent = unread;
      badge.style.display = unread > 0 ? 'inline-block' : 'none';
    }
    const dot = document.querySelector('.notif-dot');
    if (dot) dot.style.display = unread > 0 ? 'block' : 'none';
  },
  async loadStorage() {
  const data = await api.get('/api/user/storage');
  if (!data) return;

  const fill = document.getElementById('storage-fill');
  const text = document.getElementById('storage-text');

  if (fill) fill.style.width = data.used_pct + '%';

  // Color the bar based on usage
  if (fill) {
    fill.style.background = data.used_pct > 80 ? '#ef4444'
                          : data.used_pct > 50 ? '#f59e0b'
                          : '';   // default green from CSS
  }

  if (text) {
    const display = data.used_gb < 0.01
      ? `${data.used_mb} MB / ${data.max_gb} GB used`
      : `${data.used_gb} GB / ${data.max_gb} GB used`;
    text.textContent = display;
  }
},
};



// ── Notifications Panel ───────────────────────────────────
const notifPanel = {
  open: false,

  init() {
    const btn = document.getElementById('notif-btn');
    const dropdown = document.getElementById('notif-dropdown');
    if (!btn || !dropdown) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle(dropdown);
    });
    document.addEventListener('click', () => {
      dropdown.classList.remove('open');
      this.open = false;
    });
    dropdown.addEventListener('click', e => e.stopPropagation());
    this.load(dropdown);
  },

  async toggle(dropdown) {
    this.open = !this.open;
    dropdown.classList.toggle('open', this.open);
    if (this.open) await this.load(dropdown);
  },

  async load(dropdown) {
    const data = await api.get('/api/notifications');
    if (!data) return;

    const body = dropdown.querySelector('.notif-body');
    if (!body) return;

    if (data.length === 0) {
      body.innerHTML = '<div class="empty-state" style="padding:20px"><div class="empty-icon">🔔</div><p>No notifications</p></div>';
      return;
    }

    body.innerHTML = data.slice(0, 5).map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}">
        <div class="notif-item-title">${n.title}</div>
        <div class="notif-item-msg">${n.message}</div>
        <div class="notif-item-time">${formatTime(n.created_at)}</div>
      </div>
    `).join('');

    // Mark as read
    await api.post('/api/notifications/mark-read', {});
    const dot = document.querySelector('.notif-dot');
    if (dot) dot.style.display = 'none';
  }
};

// ── Utility Functions ─────────────────────────────────────
function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr.replace(' ', 'T'));
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function formatDueDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr.replace(' ', 'T'));
  const now = new Date();
  const diff = d - now;
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 0) return 'Overdue';
  if (hrs < 24) return `Due ${d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'Due tomorrow';
  return `Due ${d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`;
}

function getCourseIcon(title) {
  if (!title) return '📚';
  const t = title.toLowerCase();
  if (t.includes('web') || t.includes('react') || t.includes('html')) return '💻';
  if (t.includes('ai') || t.includes('machine') || t.includes('neural')) return '🤖';
  if (t.includes('design') || t.includes('ui') || t.includes('ux')) return '🎨';
  if (t.includes('data') || t.includes('python')) return '📊';
  if (t.includes('cloud') || t.includes('aws')) return '☁️';
  if (t.includes('devops') || t.includes('docker')) return '⚙️';
  return '📚';
}

// ── Page Init ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  toast.init();
  sidebar.init();
  notifPanel.init();

  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      window.location.href = '/api/auth/logout';
    });
  }
});


/* ── Image Preview (base64) ─────────────────────────────────────────────── */
const profileImageInput = document.getElementById('profileImage');
if (profileImageInput) {
  profileImageInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      alert('Image must be under 2 MB.');
      return;
    }

    const reader = new FileReader();
    reader.onload = function (evt) {
      const dataUrl = evt.target.result;

      // Show preview in form
      const preview = document.getElementById('profilePreview');
      const placeholder = document.getElementById('photoPlaceholder');
      if (preview) {
        preview.src = dataUrl;
        preview.style.display = 'block';
      }
      if (placeholder) placeholder.style.display = 'none';

      // Mirror in sidebar
      const sidebarAvatar = document.getElementById('sidebarAvatar');
      const sidebarPlaceholder = document.getElementById('sidebarAvatarPlaceholder');
      if (sidebarAvatar) {
        sidebarAvatar.src = dataUrl;
        sidebarAvatar.style.display = 'block';
      }
      if (sidebarPlaceholder) sidebarPlaceholder.style.display = 'none';

      // Store in hidden field for form submission
      const hiddenField = document.getElementById('profileImageData');
      if (hiddenField) hiddenField.value = dataUrl;
    };
    reader.readAsDataURL(file);
  });
}