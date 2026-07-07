document.addEventListener('DOMContentLoaded', () => {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const roomCards = document.querySelectorAll('.room-card');
  const searchInput = document.getElementById('searchInput');
  const flashCloseBtns = document.querySelectorAll('.flash-close');

  const ensureEmptyFilter = () => {
    const roomsGrid = document.getElementById('roomsGrid');

    if (!roomsGrid || roomsGrid.querySelector('.empty-rooms')) {
      return null;
    }

    let empty = roomsGrid.querySelector('.empty-filter');

    if (!empty) {
      empty = document.createElement('p');
      empty.className = 'empty-filter is-hidden';
      empty.textContent = 'Data kamar tidak ditemukan.';
      roomsGrid.appendChild(empty);
    }

    return empty;
  };

  const applyRoomFilter = () => {
    const activeFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
    const query = (searchInput?.value || '').trim().toLowerCase();
    let visibleCount = 0;

    roomCards.forEach(card => {
      const status = card.dataset.status || '';
      const name = (card.dataset.name || '').toLowerCase();

      const matchFilter = activeFilter === 'all' || status === activeFilter;
      const matchSearch = !query || name.includes(query);
      const isVisible = matchFilter && matchSearch;

      card.classList.toggle('is-hidden', !isVisible);

      if (isVisible) {
        visibleCount += 1;
      }
    });

    const emptyFilter = ensureEmptyFilter();

    if (emptyFilter) {
      emptyFilter.classList.toggle('is-hidden', visibleCount !== 0);
    }
  };

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(item => item.classList.remove('active'));
      btn.classList.add('active');
      applyRoomFilter();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', applyRoomFilter);
  }

  flashCloseBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.flash')?.remove();
    });
  });

  document.querySelectorAll('.stat-card').forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';

    setTimeout(() => {
      card.style.transition = 'opacity .3s ease, transform .3s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 80 + index * 80);
  });

  roomCards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(10px)';

    setTimeout(() => {
      card.style.transition = 'opacity .25s ease, transform .25s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 250 + index * 50);
  });

  applyRoomFilter();
});