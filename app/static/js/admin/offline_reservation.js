/**
 * offline_reservation.js
 * Form reservasi offline (admin) -- logika slot jam disamakan dengan
 * booking online customer: pilih room -> pilih tanggal -> pilih durasi ->
 * jam yang sudah bentrok dengan reservasi lain (status pending/confirmed)
 * otomatis di-disable, gak bisa dipilih.
 *
 * FIX: durasi maksimal ditampilkan cuma sampai 6 jam (samain kayak booking
 * customer, sebelumnya sampai 12 jam). Juga toko tutup jam 01:00 -- begitu
 * "Jam Mulai" dipilih, opsi durasi yang bakal melewati jam tutup otomatis
 * di-disable (mis: pilih 22:00 -> cuma 1/2/3 Jam yang bisa dipilih).
 */

document.addEventListener("DOMContentLoaded", () => {

  const $ = id => document.getElementById(id);

  const roomSelect     = $("room_id");
  const daysContainer  = $("picker-days");
  const durContainer   = $("picker-durations");
  const timesContainer = $("picker-times");
  const startTimeInput = $("start_time");
  const durationInput  = $("duration_hours");
  const submitBtn      = $("submit-btn");
  const form           = $("offline-form");

  // FIX: cap durasi max 6 jam (dulu [1,2,3,4,5,6,8,12])
  const DURATIONS = [1, 2, 3, 4, 5, 6];
  const ALL_HOURS = [
    "08:00","09:00","10:00","11:00","12:00","13:00",
    "14:00","15:00","16:00","17:00","18:00","19:00",
    "20:00","21:00","22:00"
  ];

  const state = {
    roomId:      "",
    date:        null,
    duration:    1,
    time:        null,
    bookedSlots: [],
  };

  /* ── Tanggal: 14 hari ke depan (admin boleh input lebih jauh dari customer) ── */
  function nextDays(n = 14) {
    const days  = [];
    const names = ["Min","Sen","Sel","Rab","Kam","Jum","Sab"];
    const months= ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"];
    for (let i = 0; i < n; i++) {
      const d = new Date();
      d.setDate(d.getDate() + i);
      days.push({
        label: `${names[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`,
        value: d.toISOString().split("T")[0],
        isToday: i === 0,
      });
    }
    return days;
  }

  function renderDays() {
    daysContainer.innerHTML = nextDays(14).map(d => `
      <button type="button" class="chip" data-value="${d.value}">${d.label}</button>
    `).join("");

    daysContainer.querySelectorAll(".chip").forEach(chip => {
      chip.addEventListener("click", async () => {
        state.date = chip.dataset.value;
        state.time = null;
        daysContainer.querySelectorAll(".chip").forEach(c => c.classList.remove("selected"));
        chip.classList.add("selected");

        await refreshBookedSlots();
        renderTimes();
        syncHiddenInputs();
      });
    });
  }

  // FIX: toko tutup jam 01:00 -- hitung berapa jam maksimal dari jam mulai
  // sampai jam tutup (identik dengan logic CLOSING_TIME di admin.py).
  function maxHoursForTime(timeStr) {
    const [h, m] = timeStr.split(":").map(Number);
    const startMinutes   = h * 60 + m;
    const closingMinutes = 25 * 60; // 01:00 dinihari hari berikutnya = jam 25:00
    return (closingMinutes - startMinutes) / 60;
  }

  function renderDurations() {
    const maxAllowed = state.time ? maxHoursForTime(state.time) : Infinity;

    durContainer.innerHTML = DURATIONS.map(h => {
      const disabled = h > maxAllowed;
      const title = disabled
        ? `Toko tutup jam 01:00, mulai jam ${state.time} maksimal ${Math.floor(maxAllowed)} jam`
        : "";
      return `
        <button type="button"
                class="chip${disabled ? ' disabled' : ''}${state.duration === h ? ' selected' : ''}"
                data-value="${h}"
                ${disabled ? "disabled" : ""}
                title="${title}">
          ${h} Jam
        </button>
      `;
    }).join("");

    durContainer.querySelectorAll(".chip:not([disabled])").forEach(chip => {
      chip.addEventListener("click", () => {
        state.duration = Number(chip.dataset.value);
        durContainer.querySelectorAll(".chip").forEach(c => c.classList.remove("selected"));
        chip.classList.add("selected");
        renderTimes();
        syncHiddenInputs();
      });
    });

    // Kalau durasi yang lagi dipilih jadi gak valid lagi (karena jam mulai
    // berubah), reset ke durasi terbesar yang masih diizinkan.
    if (state.duration > maxAllowed) {
      const fallback = DURATIONS.filter(h => h <= maxAllowed).pop();
      state.duration = fallback || null;
      renderDurations();
    }
  }

  /* ── Cek apakah slot jam konflik dengan reservasi lain ── */
  function isSlotBooked(timeStr, durationHours) {
    if (!state.date) return false;
    const slotStart = new Date(`${state.date}T${timeStr}:00`);
    const slotEnd   = new Date(slotStart.getTime() + durationHours * 60 * 60 * 1000);

    return state.bookedSlots.some(booked => {
      const bookedStart = new Date(booked.start_time);
      const bookedEnd   = new Date(booked.end_time);
      return slotStart < bookedEnd && slotEnd > bookedStart;
    });
  }

  async function refreshBookedSlots() {
    if (!state.roomId || !state.date) {
      state.bookedSlots = [];
      return;
    }
    try {
      const res = await fetch(`/admin/rooms/${state.roomId}/booked-slots?date=${state.date}`);
      const data = res.ok ? await res.json() : { slots: [] };
      state.bookedSlots = data.slots || [];
    } catch {
      state.bookedSlots = [];
    }
  }

  function renderTimes() {
    if (!state.roomId) {
      timesContainer.innerHTML = `<p class="picker-hint">Pilih room terlebih dahulu.</p>`;
      return;
    }
    if (!state.date) {
      timesContainer.innerHTML = `<p class="picker-hint">Pilih tanggal untuk melihat jam yang tersedia.</p>`;
      return;
    }

    const now         = new Date();
    const isToday      = state.date === now.toISOString().split("T")[0];
    const currentHour  = now.getHours();
    const currentMin   = now.getMinutes();

    timesContainer.innerHTML = ALL_HOURS.map(t => {
      const [h, m] = t.split(":").map(Number);

      let isPast = false;
      if (isToday) {
        isPast = h < currentHour || (h === currentHour && m <= currentMin);
      }

      const isBooked = isSlotBooked(t, state.duration || 1);
      const disabled = isPast || isBooked;
      const label    = isBooked ? `${t} 🚫` : t;
      const title    = isBooked ? "Slot ini sudah dibooking" : isPast ? "Jam sudah lewat" : "";

      return `
        <button type="button" class="chip${disabled ? ' disabled' : ''}${state.time === t ? ' selected' : ''}"
                data-value="${t}"
                ${disabled ? "disabled" : ""}
                title="${title}">
          ${label}
        </button>
      `;
    }).join("");

    timesContainer.querySelectorAll(".chip:not([disabled])").forEach(chip => {
      chip.addEventListener("click", () => {
        state.time = chip.dataset.value;
        timesContainer.querySelectorAll(".chip").forEach(c => c.classList.remove("selected"));
        chip.classList.add("selected");
        // FIX: begitu jam mulai dipilih, re-render pilihan durasi supaya
        // opsi yang melewati jam tutup (01:00) otomatis di-disable.
        renderDurations();
        syncHiddenInputs();
      });
    });
  }

  function syncHiddenInputs() {
    durationInput.value = state.duration || 1;
    startTimeInput.value = (state.date && state.time) ? `${state.date}T${state.time}` : "";

    const ready = !!(state.roomId && state.date && state.duration && state.time);
    submitBtn.disabled = !ready;
  }

  /* ── Room select ── */
  roomSelect.addEventListener("change", async () => {
    state.roomId = roomSelect.value;
    state.time   = null;
    clearFieldError(roomSelect);

    await refreshBookedSlots();
    renderTimes();
    syncHiddenInputs();
  });

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

  /* ── Submit ── */
  if (form && submitBtn) {
    form.addEventListener("submit", (e) => {
      let valid = true;

      if (!roomSelect.value) {
        showFieldError(roomSelect, "Pilih room terlebih dahulu");
        valid = false;
      }

      const guestName = $("guest_name");
      if (guestName && !guestName.value.trim()) {
        showFieldError(guestName, "Nama customer wajib diisi");
        valid = false;
      }

      if (!state.date || !state.time) {
        valid = false;
        alert("Pilih tanggal dan jam mulai terlebih dahulu.");
      }

      // Re-cek konflik di sisi client sebelum submit (server tetap jadi validasi final)
      if (state.date && state.time && isSlotBooked(state.time, state.duration || 1)) {
        valid = false;
        alert("Jam ini sudah dibooking, silakan pilih jam lain.");
        renderTimes();
      }

      if (!valid) {
        e.preventDefault();
        return;
      }

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

  /* ── Init ── */
  renderDays();
  renderDurations();
  renderTimes();
  syncHiddenInputs();
});
