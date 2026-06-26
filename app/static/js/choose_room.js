/* ============================================================
   PAGE: CHOOSE ROOM
   ============================================================ */

function renderRoomCard(room) {
  const isAvail = room.status === 'available';
  const busyText = room.busyLeft ? `Busy (${room.busyLeft} left)` : 'Busy';

  return `
    <article class="room-card room-card--${room.typeClass}${!isAvail ? ' room-card--busy' : ''}"
             data-room-id="${room.id}"
             role="${isAvail ? 'button' : 'article'}"
             tabindex="${isAvail ? 0 : -1}"
             aria-label="Room ${room.id}, ${room.type}, ${isAvail ? 'Available' : 'Busy'}">

      <div class="room-card__img">
        <div class="room-card__img-fallback">${room.emoji}</div>
        <span class="status-badge status-badge--${room.status}">
          ${isAvail ? 'Available' : busyText}
        </span>
      </div>

      <div class="room-card__body">
        <div class="room-card__id-row">
          <div class="room-card__id">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            ${room.id}
          </div>
          <div class="room-card__price-col">
            <div class="room-card__price">${room.priceLabel}</div>
            <div class="room-card__type">${room.type}</div>
          </div>
        </div>

        <ul class="room-card__features">
          ${room.features.map(f => `
            <li class="room-card__feature">
              ${featureIcon(f)} ${f}
            </li>
          `).join('')}
        </ul>

        <button
          class="room-card__btn room-card__btn--${isAvail ? 'ready' : 'busy'}"
          ${!isAvail ? 'disabled aria-disabled="true"' : ''}
          data-room-id="${room.id}">
          ${isAvail ? 'Ready' : 'Busy'}
        </button>
      </div>
    </article>
  `;
}

function renderRooms() {
  const grid = $('#rooms-grid');
  if (!grid) return;

  const filtered = ROOMS.filter(r => r.type === state.currentEnv);
  grid.innerHTML = filtered.map(renderRoomCard).join('');

  /* click delegation for available cards */
  grid.addEventListener('click', e => {
    const btn   = e.target.closest('.room-card__btn:not([disabled])');
    const card  = e.target.closest('.room-card:not(.room-card--busy)');
    if (btn || card) {
      const id = (btn || card).dataset.roomId;
      if(typeof openModal === 'function') openModal(id);
    }
  });

  grid.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.room-card:not(.room-card--busy)');
      if (card) { e.preventDefault(); if(typeof openModal === 'function') openModal(card.dataset.roomId); }
    }
  });
}

function initEnvSidebar() {
  $$('.env-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.currentEnv = btn.dataset.env;
      $$('.env-btn').forEach(b => b.classList.toggle('active', b === btn));
      renderRooms();
    });
  });
}

/* Auto-init for Choose Room page */
document.addEventListener('DOMContentLoaded', () => {
  if ($('#rooms-grid')) {
    renderRooms();
    initEnvSidebar();
  }
});