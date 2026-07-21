/**
 * Healthify AI — API Client
 * Centralised fetch wrapper with JWT auth and error handling.
 */

// Auto-detect environment: use Render backend in production, localhost in dev
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'
  : 'https://healthifyy-backend.onrender.com/api';

function getToken() {
  return localStorage.getItem('healthify_token');
}

function setToken(token) {
  localStorage.setItem('healthify_token', token);
}

function clearToken() {
  localStorage.removeItem('healthify_token');
  localStorage.removeItem('healthify_user');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('healthify_user') || 'null');
  } catch { return null; }
}

function setUser(user) {
  localStorage.setItem('healthify_user', JSON.stringify(user));
}

function isAuthenticated() {
  return !!getToken();
}

function redirectToLogin() {
  clearToken();
  window.location.href = '/index.html';
}

/**
 * Core fetch wrapper with automatic JWT injection and error normalisation.
 */
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (err) {
    throw new Error('Cannot connect to Healthify server. Please try again later.');
  }

  if (response.status === 401) {
    clearToken();
    window.location.href = 'index.html';
    throw new Error('Session expired. Please log in again.');
  }

  let data;
  const ct = response.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const msg = typeof data === 'object' ? (data.detail || JSON.stringify(data)) : data;
    throw new Error(msg || `Server error ${response.status}`);
  }

  return data;
}

// ─── Auth API ────────────────────────────────────────────────────────────────

const AuthAPI = {
  async register(payload) {
    const data = await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setToken(data.access_token);
    if (data.user) setUser(data.user);
    return data;
  },

  async login(email, password) {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    if (data.user) setUser(data.user);
    return data;
  },

  async getMe() {
    return apiFetch('/auth/me');
  },

  async updateMe(payload) {
    return apiFetch('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  logout() {
    clearToken();
    window.location.href = 'index.html';
  },
};

// ─── Health API ───────────────────────────────────────────────────────────────

const HealthAPI = {
  async logHealth(payload) {
    return apiFetch('/health/log', { method: 'POST', body: JSON.stringify(payload) });
  },

  async getLatest() {
    return apiFetch('/health/latest');
  },

  async getHistory(limit = 30) {
    return apiFetch(`/health/history?limit=${limit}`);
  },

  async getSummary() {
    return apiFetch('/health/summary');
  },

  async setGoal(payload) {
    return apiFetch('/health/goal', { method: 'POST', body: JSON.stringify(payload) });
  },

  async getGoal() {
    return apiFetch('/health/goal');
  },
};

// ─── Plan API ─────────────────────────────────────────────────────────────────

const PlanAPI = {
  async generate(payload = {}) {
    return apiFetch('/plan/generate', {
      method: 'POST',
      body: JSON.stringify({ include_yoga: true, generate_weekly: false, ...payload }),
    });
  },

  async getLatestDiet() {
    return apiFetch('/plan/diet/latest');
  },

  async getLatestWorkout() {
    return apiFetch('/plan/workout/latest');
  },

  async getDietHistory(limit = 7) {
    return apiFetch(`/plan/diet/history?limit=${limit}`);
  },
};

// ─── Progress API ─────────────────────────────────────────────────────────────

const ProgressAPI = {
  async getLatestWeekly() {
    return apiFetch('/progress/weekly/latest');
  },

  async getWeeklyHistory(limit = 8) {
    return apiFetch(`/progress/weekly/history?limit=${limit}`);
  },

  async triggerWeeklyReport() {
    return apiFetch('/progress/weekly/generate', { method: 'POST' });
  },

  async getHealthTrend(days = 30) {
    return apiFetch(`/progress/health-trend?days=${days}`);
  },

  async getStats() {
    return apiFetch('/progress/stats');
  },
};

// ─── Toast Notification System ────────────────────────────────────────────────

function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span style="font-size:18px">${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('removing');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Loading Overlay ──────────────────────────────────────────────────────────

function showLoading(text = 'Processing...') {
  let overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `<div class="spinner"></div><p class="loading-text" id="loading-text">${text}</p>`;
    document.body.appendChild(overlay);
  }
  document.getElementById('loading-text').textContent = text;
  overlay.classList.add('active');
}

function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.remove('active');
}

// ─── Auth Guard ───────────────────────────────────────────────────────────────

function requireAuth() {
  if (!isAuthenticated()) {
    redirectToLogin();
    return false;
  }
  return true;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function getBMIColor(bmi) {
  if (bmi < 18.5) return 'var(--info)';
  if (bmi < 25)   return 'var(--accent)';
  if (bmi < 30)   return 'var(--warning)';
  return 'var(--danger)';
}

function getGlucoseColor(mmol) {
  if (mmol < 5.6)  return 'var(--accent)';
  if (mmol < 7.0)  return 'var(--warning)';
  return 'var(--danger)';
}

function getWarningLevelColor(level) {
  const map = { critical: 'var(--danger)', high: '#f97316', moderate: 'var(--warning)', info: 'var(--info)' };
  return map[level] || 'var(--text-secondary)';
}
