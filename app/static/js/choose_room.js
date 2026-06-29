/* ================================================================
   choose_room.js – filter sidebar + modal customize session
   ================================================================ */

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

/* ── State ───────────────────────────────────────────────── */
const state = {
  currentEnv: 'regular',
  selectedRoom: null,
  selectedDate: null,
  selectedDuration: null,
  selectedTime: null,
};

/* ── Helpers ─────────────────────────────────────────────── */
function formatRupiah(n) {
  return 'Rp ' + Number(n).toLocaleString('id-ID');
}

function nextDays(n = 7) {
  const days = [];
  const names = ['Min','Sen','Sel','Rab','Kam','Jum','Sab'];
  const months = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
  for (let i = 0; i < n; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    days.push({
      label: `${names[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`,
      value: d.toISOString().split('T')[0],
    });
  }
  return days;
}

const DURATIONS = [1, 2, 3, 4, 5, 6];
const START_HOURS = ['08:00','09:00','10:00','11:00','12:00','13:00',
                     '14:00','15:00','16:00','17:00','18:00','19:00',
                     '20:00','21:00','22:00'];

/* ── ENV Sidebar filter ──────────────────────────────────── */
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
    const match = state.currentEnv === 'all' || card.dataset.env === state.currentEnv;
    card.style.display = match ? '' : 'none';
  });
}

/* ── Modal ───────────────────────────────────────────────── */
function openModal(roomId) {
  const room = ROOMS_DATA.find(r => r.id === roomId);
  if (!room) return;

  state.selectedRoom  = room;
  state.selectedDate  = null;
  state.selectedDuration = null;
  state.selectedTime  = null;

  $('modal-room-tag').textContent = `${room.room_code} · ${room.environment_label}`;
  renderDays();
  renderDurations();
  renderTimes();
  updateConfirmBtn();

  $('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  $('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

function renderDays() {
  const container = $('modal-days');
  container.innerHTML = nextDays(7).map(d => `
    <button class="chip" data-value="${d.value}">${d.label}</button>
  `).join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      state.selectedDate = chip.dataset.value;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      renderTimes(); // refresh waktu setelah pilih tanggal
      updateConfirmBtn();
    });
  });
}

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
      updateConfirmBtn();
    });
  });
}

function renderTimes() {
  const container = $('modal-times');
  container.innerHTML = START_HOURS.map(t => `
    <button class="chip" data-value="${t}">${t}</button>
  `).join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      state.selectedTime = chip.dataset.value;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      updateCartBar();
      updateConfirmBtn();
    });
  });
}

function updateConfirmBtn() {
  const ready = state.selectedDate && state.selectedDuration && state.selectedTime;
  $('modal-confirm').disabled = !ready;
}

/* ── Cart Bar ────────────────────────────────────────────── */
function updateCartBar() {
  if (!state.selectedRoom || !state.selectedDuration) return;

  const total = state.selectedRoom.price_per_hour * state.selectedDuration;
  $('cart-room-label').textContent = state.selectedRoom.room_code;
  $('cart-room-detail').textContent =
    `${state.selectedRoom.environment_label} · ${state.selectedDuration} Jam`;
  $('cart-total').textContent = formatRupiah(total);
  $('cart-bar').classList.add('visible');
}

/* ── Confirm & Book ──────────────────────────────────────── */
$('modal-confirm').addEventListener('click', () => {
  if (!state.selectedRoom || !state.selectedDate || !state.selectedDuration || !state.selectedTime) return;

  const startDateTime = `${state.selectedDate}T${state.selectedTime}:00`;

  // Submit via fetch ke endpoint make_reservation
  fetch('/customer/reservations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      room_id:        state.selectedRoom.id,
      start_time:     startDateTime,
      duration_hours: state.selectedDuration,
    }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      closeModal();
      // Redirect ke halaman reservasi
      window.location.href = '/customer/reservations';
    } else {
      alert(data.message || 'Gagal membuat reservasi. Coba lagi.');
    }
  })
  .catch(() => alert('Terjadi kesalahan. Periksa koneksi.'));
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

/* ── Payment btn ─────────────────────────────────────────── */
$('cart-payment-btn').addEventListener('click', () => {
  if (state.selectedRoom) openModal(state.selectedRoom.id);
});

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initEnvSidebar();
  initRoomCards();
  filterRooms(); // tampilkan hanya regular by default
});