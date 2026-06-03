/* =====================================================================
   TableMaster — Frontend JavaScript
   Page Loader · Navbar · AJAX · AI Panel · Toast · Animations
   ===================================================================== */

'use strict';

/* ── Utilities ─────────────────────────────────────────────────── */
const TM = {
  // CSRF token for AJAX
  getCsrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
  },

  // Fetch wrapper with CSRF
  async post(url, data = {}) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrf() },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async get(url, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(qs ? `${url}?${qs}` : url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    return res.json();
  },

  // Format date helpers
  formatDate(d) {
    return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  },
  formatTime(t) {
    const [h, m] = t.split(':');
    const ampm = +h >= 12 ? 'PM' : 'AM';
    return `${+h % 12 || 12}:${m} ${ampm}`;
  },
};

/* ── Page Loader ───────────────────────────────────────────────── */
(function initLoader() {
  const loader = document.getElementById('page-loader');
  if (!loader) return;
  window.addEventListener('load', () => {
    setTimeout(() => loader.classList.add('hidden'), 300);
  });
  // Safety fallback
  setTimeout(() => loader.classList.add('hidden'), 2000);
})();

/* ── Sticky Navbar ─────────────────────────────────────────────── */
(function initNavbar() {
  const nav = document.getElementById('mainNav');
  if (!nav) return;
  const isTransparent = nav.classList.contains('navbar-transparent');
  const onScroll = () => {
    if (window.scrollY > 40) {
      nav.classList.add('scrolled');
      if (isTransparent) nav.classList.remove('navbar-transparent');
    } else {
      nav.classList.remove('scrolled');
      if (isTransparent) nav.classList.add('navbar-transparent');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();

/* ── Fade-up Animations ────────────────────────────────────────── */
(function initFadeUp() {
  const els = document.querySelectorAll('.fade-up');
  if (!els.length) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.12 });
  els.forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.06}s`;
    obs.observe(el);
  });
})();

/* ── Toast Notifications ───────────────────────────────────────── */
const Toast = {
  container: null,
  init() {
    if (this.container) return;
    this.container = document.createElement('div');
    this.container.className = 'tm-toast-wrap';
    document.body.appendChild(this.container);
  },
  show(title, msg = '', type = 'info', duration = 4000) {
    this.init();
    const icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
    const t = document.createElement('div');
    t.className = `tm-toast ${type}`;
    t.innerHTML = `
      <i class="bi ${icons[type] || icons.info}"></i>
      <div><div class="tm-toast-title">${title}</div>${msg ? `<div class="tm-toast-msg">${msg}</div>` : ''}</div>
      <span class="tm-toast-close bi bi-x-lg"></span>`;
    t.querySelector('.tm-toast-close').onclick = () => this.dismiss(t);
    this.container.appendChild(t);
    if (duration) setTimeout(() => this.dismiss(t), duration);
  },
  dismiss(el) {
    el.style.animation = 'toast-in 0.25s ease reverse forwards';
    el.addEventListener('animationend', () => el.remove());
  },
  success(title, msg) { this.show(title, msg, 'success'); },
  error(title, msg)   { this.show(title, msg, 'error');   },
  warning(title, msg) { this.show(title, msg, 'warning'); },
};

// Auto-show Django messages as toasts
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-toast-type]').forEach(el => {
    const type = el.dataset.toastType;
    const msg  = el.dataset.toastMsg;
    const map  = { success: 'success', error: 'error', warning: 'warning', info: 'info', debug: 'info' };
    setTimeout(() => Toast.show(msg, '', map[type] || 'info'), 400);
  });
});

/* ── Favourite Toggle ──────────────────────────────────────────── */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.fav-btn');
  if (!btn) return;
  e.preventDefault(); e.stopPropagation();
  const slug = btn.dataset.slug;
  if (!slug) return;
  try {
    const data = await TM.post(`/restaurants/${slug}/favourite/`);
    btn.classList.toggle('active', data.favourited);
    btn.title = data.favourited ? 'Remove from favourites' : 'Add to favourites';
    Toast.success(data.favourited ? 'Added to favourites' : 'Removed from favourites');
  } catch { Toast.error('Please log in to save favourites'); }
});

/* ── Restaurant Search Auto-submit ─────────────────────────────── */
(function initSearch() {
  const form = document.getElementById('restaurantSearchForm');
  if (!form) return;
  const selects = form.querySelectorAll('select[data-autosubmit]');
  selects.forEach(sel => sel.addEventListener('change', () => form.submit()));
  // Clear filters
  document.getElementById('clearFilters')?.addEventListener('click', () => {
    form.reset();
    form.submit();
  });
})();

/* ── Availability Check ────────────────────────────────────────── */
(function initAvailabilityCheck() {
  const dateInput = document.getElementById('id_reservation_date');
  const timeInput = document.getElementById('id_reservation_time');
  const guestsInput = document.getElementById('id_guest_count');
  const restaurantSlug = document.getElementById('restaurantSlug')?.value;
  const avail = document.getElementById('availabilityStatus');
  if (!dateInput || !restaurantSlug) return;

  let timer;
  const check = () => {
    clearTimeout(timer);
    const date = dateInput.value;
    const time = timeInput?.value;
    const guests = guestsInput?.value;
    if (!date) return;
    timer = setTimeout(async () => {
      try {
        if (avail) avail.innerHTML = '<span class="text-muted-tm"><span class="shimmer d-inline-block" style="width:140px;height:16px;"></span></span>';
        const data = await TM.get('/restaurants/api/check-availability/', { slug: restaurantSlug, date, time, guests });
        if (avail) {
          if (data.available) {
            avail.innerHTML = `<span class="tm-badge tm-badge-green"><i class="bi bi-check-circle-fill"></i> ${data.available_count} tables available</span>`;
          } else {
            avail.innerHTML = `<span class="tm-badge tm-badge-red"><i class="bi bi-x-circle-fill"></i> No tables available</span>`;
          }
        }
        // Trigger AI recommendation
        triggerAIRecommendation(date, time, guests);
      } catch (err) {
        console.warn('Availability check failed:', err);
      }
    }, 600);
  };

  [dateInput, timeInput, guestsInput].forEach(el => el?.addEventListener('change', check));
})();

/* ── AI Recommendation Panel ───────────────────────────────────── */
async function triggerAIRecommendation(date, time, guests) {
  const panel = document.getElementById('aiPanel');
  const restaurantSlug = document.getElementById('restaurantSlug')?.value;
  if (!panel || !restaurantSlug || !date || !time || !guests) return;

  // Show loading
  panel.querySelector('#aiContent').innerHTML = `
    <div class="ai-loading">
      <div class="ai-dots"><span></span><span></span><span></span></div>
      <span>AI is analysing availability…</span>
    </div>`;

  try {
    const data = await TM.get('/reservations/api/ai-recommend/', {
      slug: restaurantSlug, date, time, guests,
    });

    if (data.has_recommendation && data.recommended_table) {
      const t = data.recommended_table;
      const pct = Math.round((data.overall_score || 0) * 100);
      const alt = (data.alternative_slots || []).slice(0, 3);

      panel.querySelector('#aiContent').innerHTML = `
        <div class="ai-table-rec">Table ${t.number} — ${t.type}</div>
        <div style="font-size:.82rem;color:var(--tm-text-muted)">Capacity: ${t.capacity} guests · Floor: ${t.floor || '—'} · Section: ${t.section || '—'}</div>
        <div class="ai-confidence">
          <div class="confidence-bar"><div class="confidence-fill" style="width:${pct}%"></div></div>
          <span class="confidence-label">${pct}% match</span>
        </div>
        <p class="ai-reasoning">${data.reasoning?.overall || 'Best available table for your group size and preferences.'}</p>
        ${alt.length ? `
        <div style="margin-top:.75rem;font-size:.78rem;color:var(--tm-text-dim);">Alternative slots:</div>
        <div style="display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.4rem;">
          ${alt.map(s => `<span class="tm-badge tm-badge-gold" style="cursor:pointer" onclick="fillSlot('${s.date}','${s.time}')">${s.date} ${TM.formatTime(s.time)}</span>`).join('')}
        </div>` : ''}
        <div style="margin-top:1rem;">
          <button type="button" class="btn-gold" onclick="applyAIRecommendation(${t.id})">
            <i class="bi bi-magic"></i> Apply Recommendation
          </button>
        </div>`;

      // Store for form submission
      window._aiRecommendedTableId = t.id;
    } else {
      panel.querySelector('#aiContent').innerHTML = `
        <p class="ai-reasoning">No tables are available for this slot. Try the alternative times shown below.</p>
        ${(data.alternative_slots||[]).slice(0,4).map(s =>
          `<span class="tm-badge tm-badge-gold" style="cursor:pointer;margin:.2rem;" onclick="fillSlot('${s.date}','${s.time}')">${s.date} ${TM.formatTime(s.time)}</span>`
        ).join('')}`;
    }
  } catch (err) {
    panel.querySelector('#aiContent').innerHTML = `<p class="ai-reasoning">Recommendation unavailable at this time.</p>`;
  }
}

window.applyAIRecommendation = function(tableId) {
  const sel = document.getElementById('id_table');
  if (sel) {
    const opt = sel.querySelector(`option[value="${tableId}"]`);
    if (opt) { sel.value = tableId; Toast.success('Table applied', 'AI recommendation has been selected.'); }
  }
  const hidden = document.getElementById('selectedTableId') || document.getElementById('aiTableInput');
  if (hidden) hidden.value = tableId;
};

window.fillSlot = function(date, time) {
  const d = document.getElementById('id_reservation_date');
  const t = document.getElementById('id_reservation_time');
  if (d) { d.value = date; d.dispatchEvent(new Event('change')); }
  if (t) { t.value = time; t.dispatchEvent(new Event('change')); }
};

/* ── Booking Form Enhancement ──────────────────────────────────── */
(function initBookingForm() {
  // Prevent past dates
  const dateInput = document.getElementById('id_reservation_date');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 60);
    dateInput.max = maxDate.toISOString().split('T')[0];
  }

  // Guest count spinner
  const guestInput = document.getElementById('id_guest_count');
  document.getElementById('guestMinus')?.addEventListener('click', () => {
    if (guestInput && +guestInput.value > 1) { guestInput.value = +guestInput.value - 1; guestInput.dispatchEvent(new Event('change')); }
  });
  document.getElementById('guestPlus')?.addEventListener('click', () => {
    if (guestInput && +guestInput.value < 20) { guestInput.value = +guestInput.value + 1; guestInput.dispatchEvent(new Event('change')); }
  });
})();

/* ── Admin: Inline Status Update ──────────────────────────────── */
document.addEventListener('change', async (e) => {
  const sel = e.target.closest('[data-status-update]');
  if (!sel) return;
  const id = sel.dataset.reservationId;
  const status = sel.value;
  try {
    const data = await TM.post(`/dashboard/admin/reservations/${id}/status/`, { status });
    if (data.success) Toast.success('Status updated');
    else Toast.error('Update failed', data.error || '');
  } catch { Toast.error('Request failed'); }
});

/* ── Admin: Delete confirmation ────────────────────────────────── */
document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-confirm-delete]');
  if (!btn) return;
  const msg = btn.dataset.confirmDelete || 'Are you sure you want to delete this item?';
  if (!confirm(msg)) { e.preventDefault(); }
});

/* ── Profile photo preview ─────────────────────────────────────── */
(function initPhotoPreview() {
  const inp = document.getElementById('id_avatar');
  const prev = document.getElementById('avatarPreview');
  if (!inp || !prev) return;
  inp.addEventListener('change', () => {
    const file = inp.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => { prev.src = ev.target.result; };
      reader.readAsDataURL(file);
    }
  });
})();

/* ── Notification mark-read ────────────────────────────────────── */
document.addEventListener('click', async (e) => {
  const item = e.target.closest('[data-notif-id]');
  if (!item) return;
  const id = item.dataset.notifId;
  if (!id || !item.classList.contains('unread')) return;
  try {
    await TM.post(`/accounts/notifications/${id}/read/`);
    item.classList.remove('unread');
    const badge = document.getElementById('notifBadge');
    if (badge) {
      const count = parseInt(badge.textContent) - 1;
      if (count <= 0) badge.remove();
      else badge.textContent = count;
    }
  } catch {}
});

/* ── Mark all notifications read ──────────────────────────────── */
document.getElementById('markAllRead')?.addEventListener('click', async () => {
  try {
    await TM.post('/accounts/notifications/read-all/');
    document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
    document.getElementById('notifBadge')?.remove();
    Toast.success('All notifications marked as read');
  } catch { Toast.error('Failed to update notifications'); }
});

/* ── Filter sidebar toggle (mobile) ───────────────────────────── */
document.getElementById('filterToggle')?.addEventListener('click', () => {
  const sidebar = document.getElementById('filterSidebar');
  sidebar?.classList.toggle('show');
});

/* ── Reservation cancel confirmation ───────────────────────────── */
document.querySelectorAll('[data-cancel-reservation]').forEach(btn => {
  btn.addEventListener('click', (e) => {
    if (!confirm('Cancel this reservation? This action cannot be undone.')) e.preventDefault();
  });
});

/* ── Rating stars UI ───────────────────────────────────────────── */
(function initStarRating() {
  document.querySelectorAll('.star-input-group').forEach(group => {
    const stars = group.querySelectorAll('.star-input');
    const input = group.querySelector('input[type=hidden]');
    stars.forEach((star, i) => {
      star.addEventListener('mouseenter', () => stars.forEach((s, j) => s.classList.toggle('hover', j <= i)));
      star.addEventListener('mouseleave', () => stars.forEach(s => s.classList.remove('hover')));
      star.addEventListener('click', () => {
        const val = i + 1;
        if (input) input.value = val;
        stars.forEach((s, j) => s.classList.toggle('selected', j < val));
      });
    });
  });
})();

/* ── Smooth counter animation ──────────────────────────────────── */
(function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = +el.dataset.count;
      const duration = 1500;
      const step = target / (duration / 16);
      let current = 0;
      const timer = setInterval(() => {
        current = Math.min(current + step, target);
        el.textContent = Math.floor(current).toLocaleString();
        if (current >= target) clearInterval(timer);
      }, 16);
      obs.unobserve(el);
    });
  }, { threshold: 0.5 });
  counters.forEach(el => obs.observe(el));
})();

/* ── Admin analytics simple charts ────────────────────────────── */
(function initAnalyticsCharts() {
  const canvas = document.getElementById('reservationChart');
  if (!canvas || typeof Chart === 'undefined') return;
  const ctx = canvas.getContext('2d');
  const labels = JSON.parse(canvas.dataset.labels || '[]');
  const values = JSON.parse(canvas.dataset.values || '[]');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Reservations',
        data: values,
        backgroundColor: 'rgba(201,146,42,0.5)',
        borderColor: '#C9922A',
        borderWidth: 1,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(201,146,42,0.08)' }, ticks: { color: '#a07040' } },
        y: { grid: { color: 'rgba(201,146,42,0.08)' }, ticks: { color: '#a07040' } },
      },
    },
  });

  const pieCanvas = document.getElementById('cuisineChart');
  if (pieCanvas) {
    const pCtx = pieCanvas.getContext('2d');
    const pLabels = JSON.parse(pieCanvas.dataset.labels || '[]');
    const pValues = JSON.parse(pieCanvas.dataset.values || '[]');
    new Chart(pCtx, {
      type: 'doughnut',
      data: {
        labels: pLabels,
        datasets: [{
          data: pValues,
          backgroundColor: ['#C9922A','#D4A017','#E8C56D','#a06010','#7a4800','#5c3000'],
          borderColor: '#1C0A00',
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#d0a060' } } },
      },
    });
  }
})();

/* ── Image gallery lightbox ────────────────────────────────────── */
(function initGallery() {
  const thumbs = document.querySelectorAll('[data-gallery-src]');
  const mainImg = document.getElementById('galleryMain');
  if (!thumbs.length || !mainImg) return;
  thumbs.forEach(thumb => {
    thumb.addEventListener('click', () => {
      mainImg.src = thumb.dataset.gallerySrc;
      mainImg.style.animation = 'none';
      requestAnimationFrame(() => { mainImg.style.animation = ''; });
      thumbs.forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  });
})();

/* ── Time slot selector ────────────────────────────────────────── */
(function initTimeSlots() {
  const container = document.getElementById('timeSlotContainer');
  const timeInput = document.getElementById('id_reservation_time');
  if (!container || !timeInput) return;

  document.addEventListener('click', (e) => {
    const slot = e.target.closest('[data-time-slot]');
    if (!slot || !container.contains(slot)) return;
    container.querySelectorAll('[data-time-slot]').forEach(s => s.classList.remove('selected', 'btn-gold'));
    slot.classList.add('selected', 'btn-gold');
    timeInput.value = slot.dataset.timeSlot;
    timeInput.dispatchEvent(new Event('change'));
  });
})();

/* ── Mobile menu close on link click ──────────────────────────── */
document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
  link.addEventListener('click', () => {
    const toggler = document.querySelector('.navbar-toggler');
    const menu = document.querySelector('.navbar-collapse');
    if (menu?.classList.contains('show')) toggler?.click();
  });
});

/* ── Auto-dismiss Django alert banners ─────────────────────────── */
setTimeout(() => {
  document.querySelectorAll('.django-messages .alert').forEach(a => {
    a.style.transition = 'opacity 0.5s';
    a.style.opacity = '0';
    setTimeout(() => a.remove(), 500);
  });
}, 5000);

/* ── Character counter for textareas ───────────────────────────── */
document.querySelectorAll('[data-max-chars]').forEach(el => {
  const max = +el.dataset.maxChars;
  const counter = document.createElement('div');
  counter.className = 'text-end';
  counter.style.cssText = 'font-size:.75rem;color:var(--tm-text-dim);margin-top:3px;';
  el.parentNode.insertBefore(counter, el.nextSibling);
  const update = () => {
    const rem = max - el.value.length;
    counter.textContent = `${el.value.length} / ${max}`;
    counter.style.color = rem < 20 ? '#f39c12' : 'var(--tm-text-dim)';
  };
  el.addEventListener('input', update);
  update();
});

/* ── Export init on DOM ready ──────────────────────────────────── */
window.TM = TM;
window.Toast = Toast;
