/**
 * rooms.js — Admin Manage Room | Next Level
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ── Tab Filter ── */
  const tabs  = document.querySelectorAll(".rm-tab");
  const cards = document.querySelectorAll(".rm-card-room");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const filter = tab.dataset.filter;
      cards.forEach(card => {
        if (filter === "all" || card.dataset.env === filter) {
          card.classList.remove("hidden");
        } else {
          card.classList.add("hidden");
        }
      });
    });
  });

  /* ── Open Add Room Modal ── */
  document.getElementById("btnAddRoom").addEventListener("click", () => {
    openModal("modalAdd");
  });

  /* ── File input label: Add ── */
  const addFileInput = document.getElementById("addFileInput");
  if (addFileInput) {
    addFileInput.addEventListener("change", () => {
      const name = addFileInput.files[0]?.name || "";
      document.getElementById("addFileName").textContent = name ? "📎 " + name : "";
    });
  }

  /* ── File input label: Edit ── */
  const editFileInput = document.getElementById("editFileInput");
  if (editFileInput) {
    editFileInput.addEventListener("change", () => {
      const name = editFileInput.files[0]?.name || "";
      document.getElementById("editFileName").textContent = name ? "📎 " + name : "";
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

/* ── Modal helpers ── */
function openModal(id) {
  document.getElementById(id).classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
  document.body.style.overflow = "";
}

/* ── Open Edit Modal ── */
function openEditModal(id, code, name, env, console_type, price, games, room_type, seating, status, desc) {
  document.getElementById("edit_room_code").value    = code;
  document.getElementById("edit_name").value         = name;
  document.getElementById("edit_environment").value  = env;
  document.getElementById("edit_console_type").value = console_type;
  document.getElementById("edit_price_per_hour").value = price;
  document.getElementById("edit_game_count").value   = games;
  document.getElementById("edit_room_type").value    = room_type;
  document.getElementById("edit_seating_type").value = seating;
  document.getElementById("edit_status").value       = status;
  document.getElementById("edit_description").value  = desc;
  document.getElementById("editFileName").textContent = "";

  // Set form action ke URL edit yang benar
  document.getElementById("editForm").action = `/admin/rooms/${id}/edit`;

  openModal("modalEdit");
}

/* ── Open Detail Modal ── */
function openDetailModal(id, code, name, env, console_type, price, games, room_type, seating, status, image_url, desc) {
  const envMap = { regular: "Regular", regular_pro: "Regular Pro", vip: "VIP" };
  const rtMap  = { smoking: "Smoking Room", non_smoking: "Non-Smoking Room" };
  const statusMap = { available: "✅ Available", maintenance: "🔧 Maintenance", inactive: "⛔ Inactive" };

  document.getElementById("detail_title").textContent = code + " — " + name;
  document.getElementById("d_code").textContent    = code;
  document.getElementById("d_name").textContent    = name;
  document.getElementById("d_env").textContent     = envMap[env] || env;
  document.getElementById("d_console").textContent = console_type;
  document.getElementById("d_price").textContent   = "Rp " + Number(price).toLocaleString("id-ID") + " / jam";
  document.getElementById("d_games").textContent   = games + " Games";
  document.getElementById("d_roomtype").textContent = rtMap[room_type] || room_type;
  document.getElementById("d_seating").textContent = seating || "—";
  document.getElementById("d_status").textContent  = statusMap[status] || status;
  document.getElementById("d_desc").textContent    = desc || "—";

  const imgEl = document.getElementById("detail_img");
  const placeholder = document.getElementById("detail_img_placeholder");
  if (image_url) {
    imgEl.src = image_url;
    imgEl.style.display = "block";
    placeholder.style.display = "none";
  } else {
    imgEl.style.display = "none";
    placeholder.style.display = "flex";
  }

  openModal("modalDetail");
}

/* ── Open Delete Confirm Modal ── */
function confirmDelete(id, code) {
  document.getElementById("deleteRoomCode").textContent = code;
  document.getElementById("deleteForm").action = `/admin/rooms/${id}/delete`;
  openModal("modalDelete");
}