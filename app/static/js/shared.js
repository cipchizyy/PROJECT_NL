/* ============================================================
   NEXT LEVEL RENT — Shared Data & Utilities
   ============================================================ */

'use strict';

/* ── Data ──────────────────────────────────────────────────── */
const ROOMS = [
  /* REGULAR */
  { id: 'R-01', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'available', emoji: '🖥️', features: ['13 Games', 'Smoking Room', 'Cozy Beanbag Seating'] },
  { id: 'R-02', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'available', emoji: '🖥️', features: ['13 Games', 'Smoking Room', 'Cozy Beanbag Seating'] },
  { id: 'R-03', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'available', emoji: '🖥️', features: ['13 Games', 'Smoking Room', 'Cozy Beanbag Seating'] },
  { id: 'R-04', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'available', emoji: '🖥️', features: ['13 Games', 'Non-Smoking Room', 'Cozy Beanbag Seating'] },
  { id: 'R-05', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'busy', busyLeft: '15min', emoji: '🖥️', features: ['13 Games', 'Non-Smoking Room', 'Cozy Beanbag Seating'] },
  { id: 'R-06', type: 'REGULAR', typeClass: 'regular', pricePerHour: 10000, priceLabel: '10K/hr', status: 'busy', busyLeft: '25min', emoji: '🖥️', features: ['13 Games', 'Non-Smoking Room', 'Cozy Beanbag Seating'] },

  /* REGULAR PRO */
  { id: 'RP-01', type: 'REGULAR PRO', typeClass: 'pro', pricePerHour: 15000, priceLabel: '15K/hr', status: 'available', emoji: '💻', features: ['16 Games', 'Non-Smoke Room', 'Cozy Beanbag Seating'] },
  { id: 'RP-02', type: 'REGULAR PRO', typeClass: 'pro', pricePerHour: 15000, priceLabel: '15K/hr', status: 'available', emoji: '💻', features: ['16 Games', 'Non-Smoke Room', 'Cozy Beanbag Seating'] },
  { id: 'RP-03', type: 'REGULAR PRO', typeClass: 'pro', pricePerHour: 15000, priceLabel: '15K/hr', status: 'busy', busyLeft: '2hr', emoji: '💻', features: ['16 Games', 'Non-Smoke Room', 'Cozy Beanbag Seating'] },

  /* VIP */
  { id: 'V-01', type: 'VIP', typeClass: 'vip', pricePerHour: 25000, priceLabel: '25K/hr', status: 'busy', busyLeft: '3hr', emoji: '👑', features: ['Unlimited Games', 'RTX 4090', 'Private Lounge'] },
  { id: 'V-02', type: 'VIP', typeClass: 'vip', pricePerHour: 25000, priceLabel: '25K/hr', status: 'available', emoji: '👑', features: ['Unlimited Games', 'RTX 4090', 'Private Lounge'] },
  { id: 'V-03', type: 'VIP', typeClass: 'vip', pricePerHour: 25000, priceLabel: '25K/hr', status: 'busy', busyLeft: '2hr', emoji: '👑', features: ['Unlimited Games', 'Smoke Room', 'Cozy Beanbag Seating'] },
];

const DAYS = [
  { name: 'MON', num: 23 }, { name: 'TUE', num: 24 }, { name: 'WED', num: 25 },
  { name: 'THU', num: 26 }, { name: 'FRI', num: 27 }, { name: 'SAT', num: 28 },
];

const DURATIONS = [1, 2, 4, 6];
const START_TIMES = ['10:00', '12:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];

/* ── State ─────────────────────────────────────────────────── */
const state = {
  currentEnv: 'REGULAR',
  selectedRoom: null,
  selectedDayIdx: 3,       /* default THU 26 */
  selectedDuration: 4,     /* hours */
  selectedStartTime: '18:00',
  cart: null,              /* { room, day, duration, startTime, endTime, total } */
};

/* ── Helpers ───────────────────────────────────────────────── */
function fmt(n) { return n.toLocaleString('id-ID'); }

function addHours(timeStr, hours) {
  const [h, m] = timeStr.split(':').map(Number);
  const total = (h + hours) % 24;
  return `${String(total).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function genBookingId() {
  return '#NL-' + Math.floor(1000 + Math.random() * 9000);
}

function featureIcon(feature) {
  if (feature.toLowerCase().includes('game')) {
    return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M8 12h8M12 8v8"/></svg>`;
  }
  if (feature.toLowerCase().includes('smoke')) {
    return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 18h12M18 6c0-2-2-3-2-3"/></svg>`;
  }
  return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`;
}

/* ── DOM refs ──────────────────────────────────────────────── */
const $  = (s, ctx = document) => ctx.querySelector(s);
const $$ = (s, ctx = document) => [...ctx.querySelectorAll(s)];

function setEl(selector, value) {
  const el = $(selector);
  if (el) el.textContent = value;
}

/* ── Global Init (Navbar) ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  $$('.nav__links a').forEach(a => {
    if (a.href && path.includes(a.getAttribute('href'))) {
      a.classList.add('active');
    }
  });
});