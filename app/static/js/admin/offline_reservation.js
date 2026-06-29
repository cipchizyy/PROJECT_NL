/**
 * offline_reservation.js
 * UX enhancements untuk form reservasi offline.
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ── Set datetime-local default ke sekarang ── */
  const startTimeInput = document.querySelector('input[name="start_time"]');
  if (startTimeInput && !startTimeInput.value) {
    const now = new Date();
    // Format: YYYY-MM-DDTHH:MM (sesuai datetime-local)
    const pad = n => String(n).padStart(2, "0");
    const local = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
    startTimeInput.value = local;
  }

  /* ── Validasi No. HP: hanya angka & awalan 08 ── */
  const phoneInput = document.querySelector('input[name="guest_phone"]');
  if (phoneInput) {
    phoneInput.addEventListener("input", () => {
      phoneInput.value = phoneInput.value.replace(/[^0-9]/g, "");
    });

    phoneInput.addEventListener("blur", () => {
      const val = phoneInput.value;
      if (val && !val.startsWith("08")) {
        showFieldError(phoneInput, "Nomor HP harus diawali 08");
      } else {
        clearFieldError(phoneInput);
      }
    });
  }

  /* ── Validasi durasi 1–12 ── */
  const durationInput = document.querySelector('input[name="duration_hours"]');
  if (durationInput) {
    durationInput.addEventListener("blur", () => {
      const val = parseInt(durationInput.value);
      if (isNaN(val) || val < 1) {
        durationInput.value = 1;
      } else if (val > 12) {
        durationInput.value = 12;
        showFieldError(durationInput, "Maksimal 12 jam");
        setTimeout(() => clearFieldError(durationInput), 2500);
      }
    });
  }

  /* ── Tombol submit: loading state ── */
  const form = document.querySelector(".panel-card form");
  const submitBtn = document.querySelector(".btn-primary[type='submit']");
  if (form && submitBtn) {
    form.addEventListener("submit", (e) => {
      // Validasi sederhana sebelum submit
      const roomSelect = document.querySelector('select[name="room_id"]');
      const guestName  = document.querySelector('input[name="guest_name"]');

      let valid = true;

      if (roomSelect && !roomSelect.value) {
        showFieldError(roomSelect, "Pilih room terlebih dahulu");
        valid = false;
      }

      if (guestName && !guestName.value.trim()) {
        showFieldError(guestName, "Nama customer wajib diisi");
        valid = false;
      }

      if (!valid) {
        e.preventDefault();
        return;
      }

      // Loading state
      submitBtn.disabled = true;
      submitBtn.textContent = "Memproses...";
      submitBtn.style.opacity = "0.7";
    });
  }

  /* ── Clear error saat field diubah ── */
  document.querySelectorAll(".panel-card input, .panel-card select").forEach(el => {
    el.addEventListener("input", () => clearFieldError(el));
    el.addEventListener("change", () => clearFieldError(el));
  });

  /* ── Helper: tampilkan error di bawah field ── */
  function showFieldError(field, message) {
    clearFieldError(field);
    field.style.borderColor = "#ef4444";
    field.style.boxShadow   = "0 0 0 3px rgba(239,68,68,0.15)";

    const err = document.createElement("p");
    err.className = "field-error";
    err.textContent = message;
    err.style.cssText = "color:#f87171; font-size:11px; margin:-14px 0 16px; padding:0;";
    field.insertAdjacentElement("afterend", err);
  }

  function clearFieldError(field) {
    field.style.borderColor = "";
    field.style.boxShadow   = "";
    const next = field.nextElementSibling;
    if (next && next.classList.contains("field-error")) next.remove();
  }

});