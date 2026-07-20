/* ============================================================
   MODAL & CART BAR: ADD TO CART
   ============================================================ */

function buildModal() {
  const dayRow = $('#modal-days');
  if (dayRow) {
    dayRow.innerHTML = DAYS.map((d, i) => `
      <button class="chip chip--day${i === state.selectedDayIdx ? ' selected' : ''}"
              data-group="day" data-idx="${i}">
        <span class="chip__day-name">${d.name}</span>
        <span class="chip__day-num">${d.num}</span>
      </button>
    `).join('');
  }

  const durRow = $('#modal-durations');
  if (durRow) {
    durRow.innerHTML = DURATIONS.map(d => `
      <button class="chip${d === state.selectedDuration ? ' selected' : ''}"
              data-group="dur" data-value="${d}">
        ${d}h
      </button>
    `).join('');
  }

  const timeGrid = $('#modal-times');
  if (timeGrid) {
    timeGrid.innerHTML = START_TIMES.map(t => `
      <button class="chip${t === state.selectedStartTime ? ' selected' : ''}"
              data-group="time" data-value="${t}">
        ${t}
      </button>
    `).join('');
  }
}

function openModal(roomId) {
  const room = ROOMS.find(r => r.id === roomId);
  if (!room) return;
  state.selectedRoom = room;

  const tag = $('#modal-room-tag');
  if (tag) tag.textContent = `${room.id} · ${room.type}`;

  buildModal();

  const overlay = $('#modal-overlay');
  if (overlay) {
    overlay.classList.add('open');
    overlay.querySelector('.modal')?.focus();
  }
}

function closeModal() {
  $('#modal-overlay')?.classList.remove('open');
}

function initModal() {
  const overlay = $('#modal-overlay');
  if (!overlay) return;

  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal();
  });

  $('#modal-close')?.addEventListener('click', closeModal);

  /* chip selection */
  overlay.addEventListener('click', e => {
    const chip = e.target.closest('.chip[data-group]');
    if (!chip) return;

    const group = chip.dataset.group;

    if (group === 'day') {
      $$('.chip[data-group="day"]', overlay).forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      state.selectedDayIdx = parseInt(chip.dataset.idx);
    }

    if (group === 'dur') {
      $$('.chip[data-group="dur"]', overlay).forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      state.selectedDuration = parseInt(chip.dataset.value);
    }

    if (group === 'time') {
      $$('.chip[data-group="time"]', overlay).forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      state.selectedStartTime = chip.dataset.value;
    }
  });

  $('#modal-confirm')?.addEventListener('click', confirmAddToCart);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });
}

function confirmAddToCart() {
  const room = state.selectedRoom;
  if (!room) return;

  const day      = DAYS[state.selectedDayIdx];
  const dur      = state.selectedDuration;
  const start    = state.selectedStartTime;
  const end      = addHours(start, dur);
  const total    = room.pricePerHour * dur;

  state.cart = { room, day, duration: dur, startTime: start, endTime: end, total };

  closeModal();
  updateCartBar();
}

function updateCartBar() {
  const bar = $('#cart-bar');
  if (!bar || !state.cart) return;

  const { room, day, duration, startTime, endTime, total } = state.cart;

  setEl('#cart-room-label', `${room.type} | ${room.id}`);
  setEl('#cart-room-detail', `${day.name} ${day.num} · ${startTime}–${endTime} · ${duration}h`);
  setEl('#cart-total', fmt(total));

  bar.classList.add('visible');
}

function initCartBar() {
  $('#cart-payment-btn')?.addEventListener('click', () => {
    if (!state.cart) return;
    window.location.href = 'payment.html';
  });
}

/* Auto-init for Modal & Cart Bar */
document.addEventListener('DOMContentLoaded', () => {
  if ($('#modal-overlay')) initModal();
  if ($('#cart-bar')) initCartBar();
});