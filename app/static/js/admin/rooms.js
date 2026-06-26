/* admin_rooms.js */

function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape')
    document.querySelectorAll('.modal-overlay.open').forEach(m => closeModal(m.id));
});

// Add Room
document.getElementById('btnAddRoom').addEventListener('click', () => openModal('modalAdd'));

// Image preview
const imgInput   = document.getElementById('imgInput');
const imgPreview = document.getElementById('imgPreview');
const uploadArea = document.getElementById('uploadArea');

if (imgInput) {
  imgInput.addEventListener('change', () => {
    const file = imgInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => { imgPreview.src = e.target.result; imgPreview.style.display = 'block'; };
    reader.readAsDataURL(file);
  });
}

if (uploadArea) {
  uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = 'var(--accent)'; });
  uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = ''; });
  uploadArea.addEventListener('drop', e => {
    e.preventDefault(); uploadArea.style.borderColor = '';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = ev => { imgPreview.src = ev.target.result; imgPreview.style.display = 'block'; };
      reader.readAsDataURL(file);
    }
  });
}

// Edit Room
function openEdit(id, code, name, console_type, env, price, game_count, room_type, seating, desc, status) {
  document.getElementById('editCode').value      = code;
  document.getElementById('editName').value      = name;
  document.getElementById('editConsole').value   = console_type;
  document.getElementById('editEnv').value       = env;
  document.getElementById('editPrice').value     = price;
  document.getElementById('editGameCount').value = game_count;
  document.getElementById('editRoomType').value  = room_type;
  document.getElementById('editSeating').value   = seating;
  document.getElementById('editDesc').value      = desc;
  document.getElementById('editStatus').value    = status;
  document.getElementById('editForm').action     = `/admin/rooms/${id}/edit`;
  openModal('modalEdit');
}

// Delete Room
function confirmDelete(id, code) {
  document.getElementById('deleteRoomName').textContent = code;
  document.getElementById('deleteForm').action = `/admin/rooms/${id}/delete`;
  openModal('modalDelete');
}

// Filter tabs
document.querySelectorAll('#filterTabs .filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#filterTabs .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('#roomsGrid .room-card:not(.add-card)').forEach(card => {
      card.style.display = (filter === 'all' || card.dataset.env === filter) ? '' : 'none';
    });
  });
});