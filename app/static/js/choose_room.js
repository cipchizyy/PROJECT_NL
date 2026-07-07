/* ================================================================
   choose_room.js
   ================================================================ */

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

const state = {
  currentEnv:       'regular',
  selectedRoom:     null,
  selectedDate:     null,
  selectedDuration: null,
  selectedTime:     null,
  bookedSlots:      [], // slot yang sudah dipesan untuk room+tanggal ini
};

function formatRupiah(n) {
  return 'Rp ' + Number(n).toLocaleString('id-ID');
}

function nextDays(n = 7) {
  const days  = [];
  const names = ['Min','Sen','Sel','Rab','Kam','Jum','Sab'];
  const months= ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
  for (let i = 0; i < n; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    days.push({
      label: `${names[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`,
      value: d.toISOString().split('T')[0],
      isToday: i === 0,
    });
  }
  return days;
}

// Semua slot jam yang tersedia
const ALL_HOURS = [
  '08:00','09:00','10:00','11:00','12:00','13:00',
  '14:00','15:00','16:00','17:00','18:00','19:00',
  '20:00','21:00','22:00'
];

const DURATIONS = [1, 2, 3, 4, 5, 6];

/* ── Cek apakah slot konflik dengan booked slots ─────────── */
function isSlotBooked(timeStr, durationHours) {
  if (!state.selectedDate) return false;

  const slotStart = new Date(`${state.selectedDate}T${timeStr}:00`);
  const slotEnd   = new Date(slotStart.getTime() + durationHours * 60 * 60 * 1000);

  return state.bookedSlots.some(booked => {
    const bookedStart = new Date(booked.start_time);
    const bookedEnd   = new Date(booked.end_time);
    // Konflik kalau ada overlap
    return slotStart < bookedEnd && slotEnd > bookedStart;
  });
}

/* ── Fetch booked slots untuk room + tanggal tertentu ───── */
async function fetchBookedSlots(roomId, date) {
  try {
    const res = await fetch(`/customer/rooms/${roomId}/booked-slots?date=${date}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.slots || [];
  } catch {
    return [];
  }
}

/* ── ENV Sidebar ─────────────────────────────────────────── */
function initEnvSidebar() {
  $$('.env-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.currentEnv = btn.dataset.env;
      $$('.env-btn').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      filterRooms();
    });
  });
}

function filterRooms() {
  $$('#rooms-grid .room-card').forEach(card => {
    card.style.display =
      (state.currentEnv === 'all' || card.dataset.env === state.currentEnv) ? '' : 'none';
  });
}

/* ── Modal ───────────────────────────────────────────────── */
function openModal(roomId) {
  const room = ROOMS_DATA.find(r => r.id === roomId);
  if (!room) return;

  state.selectedRoom     = room;
  state.selectedDate     = null;
  state.selectedDuration = null;
  state.selectedTime     = null;
  state.bookedSlots      = [];

  $('modal-room-tag').textContent = `${room.room_code} · ${room.environment_label}`;
  renderDays();
  renderDurations();
  renderTimes(); // render kosong dulu
  updateConfirmBtn();

  $('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  $('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

/* ── Render days ─────────────────────────────────────────── */
function renderDays() {
  const container = $('modal-days');
  container.innerHTML = nextDays(7).map(d => `
    <button class="chip" data-value="${d.value}" data-today="${d.isToday}">
      ${d.label}
    </button>
  `).join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', async () => {
      state.selectedDate = chip.dataset.value;
      state.selectedTime = null;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');

      // Fetch booked slots untuk room + tanggal ini
      if (state.selectedRoom) {
        state.bookedSlots = await fetchBookedSlots(state.selectedRoom.id, state.selectedDate);
      }

      renderTimes();
      updateConfirmBtn();
    });
  });
}

/* ── Render durations ────────────────────────────────────── */
function renderDurations() {
  const container = $('modal-durations');
  container.innerHTML = DURATIONS.map(h => `
    <button class="chip" data-value="${h}">${h} Jam</button>
  `).join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      state.selectedDuration = Number(chip.dataset.value);
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      // Re-render times karena durasi mempengaruhi konflik
      renderTimes();
      updateCartBar();
      updateConfirmBtn();
    });
  });
}

/* ── Render times ────────────────────────────────────────── */
function renderTimes() {
  const container = $('modal-times');
  const now       = new Date();
  const isToday   = state.selectedDate === now.toISOString().split('T')[0];
  const currentHour = now.getHours();
  const currentMin  = now.getMinutes();

  container.innerHTML = ALL_HOURS.map(t => {
    const [h, m] = t.split(':').map(Number);

    // Disable kalau jam sudah lewat (hari ini)
    let isPast = false;
    if (isToday) {
      isPast = h < currentHour || (h === currentHour && m <= currentMin);
    }

    // Disable kalau slot sudah dipesan (dengan durasi yang dipilih, default 1 jam)
    const dur     = state.selectedDuration || 1;
    const isBooked = state.selectedDate ? isSlotBooked(t, dur) : false;

    const disabled = isPast || isBooked || !state.selectedDate;
    const label    = isBooked ? `${t} 🚫` : isPast ? `${t}` : t;
    const title    = isBooked ? 'Slot ini sudah dipesan' : isPast ? 'Jam sudah lewat' : '';

    return `
      <button class="chip${disabled ? ' disabled' : ''}"
              data-value="${t}"
              ${disabled ? 'disabled' : ''}
              title="${title}">
        ${label}
      </button>
    `;
  }).join('');

  container.querySelectorAll('.chip:not([disabled])').forEach(chip => {
    chip.addEventListener('click', () => {
      state.selectedTime = chip.dataset.value;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      updateCartBar();
      updateConfirmBtn();
    });
  });
}

/* ── Update confirm button ───────────────────────────────── */
function updateConfirmBtn() {
  const ready = state.selectedDate && state.selectedDuration && state.selectedTime;
  $('modal-confirm').disabled = !ready;
}

/* ── Cart Bar ────────────────────────────────────────────── */
function updateCartBar() {
  if (!state.selectedRoom || !state.selectedDuration) return;
  const total = state.selectedRoom.price_per_hour * state.selectedDuration;
  $('cart-room-label').textContent  = state.selectedRoom.room_code;
  $('cart-room-detail').textContent =
    `${state.selectedRoom.environment_label} · ${state.selectedDuration} Jam`;
  $('cart-total').textContent = formatRupiah(total);
  $('cart-bar').classList.add('visible');
}

/* ── Confirm → buat reservasi → redirect ke payment ─────── */
$('modal-confirm').addEventListener('click', async () => {
  if (!state.selectedRoom || !state.selectedDate || !state.selectedDuration || !state.selectedTime) return;

  const btn = $('modal-confirm');
  btn.disabled    = true;
  btn.textContent = 'Memproses...';

  const startDateTime = `${state.selectedDate}T${state.selectedTime}:00`;

  try {
    const res = await fetch('/customer/reservations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        room_id:        state.selectedRoom.id,
        start_time:     startDateTime,
        duration_hours: state.selectedDuration,
      }),
    });

    const data = await res.json();

    if (data.success && data.redirect_url) {
      window.location.href = data.redirect_url;
    } else {
      alert(data.message || 'Gagal membuat reservasi. Coba lagi.');
      btn.disabled    = false;
      btn.textContent = 'Confirm & Add to GCard';
    }
  } catch (err) {
    alert('Terjadi kesalahan koneksi.');
    btn.disabled    = false;
    btn.textContent = 'Confirm & Add to GCard';
  }
});

/* ── Room card click ─────────────────────────────────────── */
function initRoomCards() {
  const grid = $('rooms-grid');
  if (!grid) return;

  grid.addEventListener('click', e => {
    const btn  = e.target.closest('.room-card__btn--ready');
    const card = e.target.closest('.room-card:not(.room-card--busy)');
    if (btn || card) {
      const roomId = (btn || card).dataset.roomId;
      if (roomId) openModal(roomId);
    }
  });

  grid.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.room-card:not(.room-card--busy)');
      if (card) { e.preventDefault(); openModal(card.dataset.roomId); }
    }
  });
}

/* ── Close modal ─────────────────────────────────────────── */
$('modal-close').addEventListener('click', closeModal);
$('modal-overlay').addEventListener('click', e => {
  if (e.target === $('modal-overlay')) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

/* ── Cart payment btn ────────────────────────────────────── */
$('cart-payment-btn').addEventListener('click', () => {
  if (state.selectedRoom) openModal(state.selectedRoom.id);
});

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initEnvSidebar();
  initRoomCards();
  filterRooms();
});