/* ============================================================
   PAGE: PAYMENT
   ============================================================ */

function renderPaymentSummary() {
  const { room, day, duration, startTime, endTime, total } = state.cart;

  /* Reservation card */
  setEl('#pay-room-type',   room.type);
  setEl('#pay-room-id',     room.id);
  setEl('#pay-room-emoji',  room.emoji);
  setEl('#pay-date',        `${day.name} ${day.num}, Jun 2026`);
  setEl('#pay-time',        `${startTime} – ${endTime}`);
  setEl('#pay-duration',    `${duration} Hours`);

  /* Summary panel */
  setEl('#summary-desc',    `${duration} Hours @ ${fmt(room.pricePerHour)}/hr`);
  setEl('#summary-sub',     fmt(total));
  setEl('#summary-total',   `IDR ${fmt(total)}`);
}

function initPaymentMethods() {
  const opts = $$('.method-opt');
  const qrisBox = $('#qris-box');

  opts.forEach(opt => {
    opt.addEventListener('click', () => {
      opts.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');

      if (qrisBox) {
        qrisBox.style.display = opt.dataset.method === 'qris' ? 'flex' : 'none';
      }
    });
  });

  $('#btn-book')?.addEventListener('click', () => {
    if (!state.cart) return;
    state.cart.bookingId = genBookingId();
    window.location.href = 'invoice.html';
  });
}

/* Auto-init for Payment Page */
document.addEventListener('DOMContentLoaded', () => {
  const isPaymentPage = !!$('#btn-book'); 
  if (!isPaymentPage) return;

  if (!state.cart) {
    /* demo fallback */
    state.cart = {
      room: ROOMS[0], day: DAYS[3], duration: 4,
      startTime: '18:00', endTime: '22:00', total: 40000,
    };
  }

  renderPaymentSummary();
  initPaymentMethods();
});