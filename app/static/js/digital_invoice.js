/* ============================================================
   PAGE: DIGITAL INVOICE
   ============================================================ */

function renderInvoice() {
  const { room, day, duration, startTime, endTime, bookingId } = state.cart;

  setEl('#inv-booking-id', bookingId || '#NL-9942');
  setEl('#inv-station',    `${room.type.charAt(0) + room.type.slice(1).toLowerCase()} Room ${room.id}`);
  setEl('#inv-date',       `Jun ${day.num}, 2026`);
  setEl('#inv-time',       `${startTime} — ${endTime}`);
  setEl('#inv-duration',   `${duration} Hours`);
}

function initDownloadBtn() {
  $('#btn-download')?.addEventListener('click', () => {
    alert('Download invoice PDF — fitur ini akan terhubung ke backend Flask kamu.');
  });

  $('#btn-back')?.addEventListener('click', () => {
    window.location.href = 'choose-room.html';
  });
}

/* Auto-init for Invoice Page */
document.addEventListener('DOMContentLoaded', () => {
  const isInvoicePage = !!$('#btn-download');
  if (!isInvoicePage) return;

  if (!state.cart) {
    /* demo fallback */
    state.cart = {
      room: ROOMS[0], day: DAYS[3], duration: 4,
      startTime: '18:00', endTime: '22:00', total: 40000,
      bookingId: '#NL-9942',
    };
  }

  renderInvoice();
  initDownloadBtn();
});