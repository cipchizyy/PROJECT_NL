/**
 * games.js — Admin Manage Game | Next Level
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ── Open Add Game Modal ── */
  document.getElementById("btnAddGame").addEventListener("click", () => {
    openModal("modalAddGame");
  });

  /* ── File input label: Add ── */
  const addFileInput = document.getElementById("addGameFileInput");
  if (addFileInput) {
    addFileInput.addEventListener("change", () => {
      const name = addFileInput.files[0]?.name || "";
      document.getElementById("addGameFileName").textContent = name ? "📎 " + name : "";
    });
  }

  /* ── File input label: Edit ── */
  const editFileInput = document.getElementById("editGameFileInput");
  if (editFileInput) {
    editFileInput.addEventListener("change", () => {
      const name = editFileInput.files[0]?.name || "";
      document.getElementById("editGameFileName").textContent = name ? "📎 " + name : "";
    });
  }

  /* ── Close modal on overlay click ── */
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  /* ── ESC to close ── */
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach(m => closeModal(m.id));
    }
  });
});

/* ── Modal helpers (sama seperti rooms.js, dipakai independen karena
   games.html tidak memuat rooms.js) ── */
function openModal(id) {
  document.getElementById(id).classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
  document.body.style.overflow = "";
}

/* ── Open Edit Game Modal ── */
function openEditGameModal(id, name, category, description) {
  document.getElementById("edit_game_name").value = name;
  document.getElementById("edit_game_category").value = category || "";
  document.getElementById("edit_game_description").value = description || "";
  document.getElementById("editGameFileName").textContent = "";

  document.getElementById("editGameForm").action = `/admin/games/${id}/edit`;

  openModal("modalEditGame");
}

/* ── Open Delete Confirm Modal ── */
function confirmDeleteGame(id, name) {
  document.getElementById("deleteGameName").textContent = name;
  document.getElementById("deleteGameForm").action = `/admin/games/${id}/delete`;
  openModal("modalDeleteGame");
}