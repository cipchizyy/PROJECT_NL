/* admin_dashboard.js */

// ── Filter tabs ──────────────────────────────────────────
const filterBtns = document.querySelectorAll('.filter-btn');
const roomCards  = document.querySelectorAll('.room-card');

filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    roomCards.forEach(card => {
      card.style.display =
        (filter === 'all' || card.dataset.status === filter) ? '' : 'none';
    });
  });
});

// ── Search ───────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase();
    roomCards.forEach(card => {
      const name = (card.dataset.name || '').toLowerCase();
      card.style.display = name.includes(q) ? '' : 'none';
    });
    // reset filter active state saat search
    if (q) {
      filterBtns.forEach(b => b.classList.remove('active'));
    }
  });
}

// ── Entrance animation ───────────────────────────────────
document.querySelectorAll('.stat-card').forEach((card, i) => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(12px)';
  setTimeout(() => {
    card.style.transition = 'opacity .3s ease, transform .3s ease';
    card.style.opacity = '1';
    card.style.transform = 'translateY(0)';
  }, 80 + i * 80);
});

roomCards.forEach((card, i) => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(10px)';
  setTimeout(() => {
    card.style.transition = 'opacity .25s ease, transform .25s ease';
    card.style.opacity = '1';
    card.style.transform = 'translateY(0)';
  }, 250 + i * 50);
});