/* admin_dashboard.js – filter rooms & minor interactions */

document.addEventListener('DOMContentLoaded', () => {

  // ── Filter tabs ─────────────────────────────────────
  const filterBtns = document.querySelectorAll('.filter-btn');
  const roomCards  = document.querySelectorAll('.room-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      roomCards.forEach(card => {
        if (filter === 'all' || card.dataset.status === filter) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // ── Search (client-side, filters room numbers & desc) ──
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.toLowerCase();
      roomCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? 'flex' : 'none';
      });
    });
  }

  // ── Stat card: subtle entrance animation ───────────────
  const statCards = document.querySelectorAll('.stat-card');
  statCards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    setTimeout(() => {
      card.style.transition = 'opacity .3s ease, transform .3s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 80 + i * 80);
  });

  // ── Room cards: staggered entrance ─────────────────────
  roomCards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(10px)';
    setTimeout(() => {
      card.style.transition = 'opacity .25s ease, transform .25s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 200 + i * 50);
  });

});