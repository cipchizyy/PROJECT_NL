/* ============================================================
   payment.js – Next Level Gaming  |  MODE SIMULASI
   ============================================================ */
'use strict';

/* ── State ───────────────────────────────────────────────── */
let selectedMethod  = document.querySelector('.method-option.active')?.dataset.method || 'cashless';
let qrisReferenceId = null;
let simConfirmUrl   = null;   // URL tombol simulasi dari backend
let statusPoller    = null;

const POLL_INTERVAL = 2000;   // cek setiap 2 detik
const POLL_TIMEOUT  = 900000; // 15 menit (sesuai expiry QR)

/* ── Method Selection ────────────────────────────────────── */
function selectMethod(method) {
  selectedMethod = method;
  document.querySelectorAll('.method-option').forEach(el => {
    el.classList.toggle('active', el.dataset.method === method);
  });
  const sec = document.getElementById('qrisSection');
  if (sec) sec.style.display = method === 'cashless' ? 'flex' : 'none';
}

/* ── Booking Button ──────────────────────────────────────── */
function processBooking() {
  if (selectedMethod === 'cashless') {
    openQRISPopup();
  } else {
    if (!confirm('Lanjutkan pemesanan dengan pembayaran tunai di kasir?')) return;
    submitCashPayment();
  }
}

async function submitCashPayment() {
  const btn = document.getElementById('bookingBtn');
  btn.disabled = true;
  btn.textContent = 'Memproses...';

  const fd = new FormData();
  fd.append('reservation_id', RESERVATION_ID);
  fd.append('method', 'cash');

  try {
    const res  = await fetch('/customer/payments', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
      window.location.href = '/customer/dashboard';
    } else {
      alert('Gagal menyimpan. Coba lagi.');
      btn.disabled = false;
      btn.textContent = 'Booking ⚡';
    }
  } catch {
    alert('Koneksi gagal.');
    btn.disabled = false;
    btn.textContent = 'Booking ⚡';
  }
}

/* ── QRIS Popup ──────────────────────────────────────────── */
function openQRISPopup() {
  document.getElementById('qrisModal').classList.add('open');
  resetQRISModal();
  generateQRIS();
}

function closeQRISPopup() {
  document.getElementById('qrisModal').classList.remove('open');
  stopPolling();
}

function closeQRISModal(e) {
  if (e.target === document.getElementById('qrisModal')) closeQRISPopup();
}

function resetQRISModal() {
  showEl('qrisLoading');
  hideEl('qrisCodeDisplay');
  hideEl('simSection');
  const s = document.getElementById('qrisStatus');
  s.className = 'qris-status';
  s.textContent = '';
  document.getElementById('checkStatusBtn').disabled = true;
  const img = document.getElementById('qrisImage');
  if (img) img.style.display = '';
}

/* ── Generate QRIS (simulasi) ────────────────────────────── */
async function generateQRIS() {
  try {
    const res  = await fetch('/customer/payment/qris/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reservation_id: RESERVATION_ID, amount: TOTAL_AMOUNT }),
    });
    const data = await res.json();

    if (!data.success) { showQRISError(data.message || 'Gagal membuat QRIS.'); return; }

    qrisReferenceId = data.reference_id;
    simConfirmUrl   = data.sim_confirm_url;

    // Tampilkan QR image
    const img = document.getElementById('qrisImage');
    img.src = data.qr_image_url;

    // Expiry label
    if (data.expires_at) {
      const exp = new Date(data.expires_at);
      document.getElementById('qrisExpire').textContent =
        `Berlaku hingga ${exp.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // Tampilkan tombol simulasi
    const simBtn = document.getElementById('simPayBtn');
    if (simBtn) simBtn.textContent = `✅ Simulasi: Konfirmasi Bayar IDR ${TOTAL_AMOUNT.toLocaleString('id-ID')}`;

    hideEl('qrisLoading');
    showEl('qrisCodeDisplay');
    showEl('simSection');
    document.getElementById('checkStatusBtn').disabled = false;

    startPolling();
  } catch (err) {
    console.error('[QRIS]', err);
    showQRISError('Koneksi gagal. Coba lagi.');
  }
}

/* ── Simulasi: Tombol Konfirmasi Bayar ───────────────────── */
async function simConfirmPayment() {
  if (!simConfirmUrl) return;

  const btn = document.getElementById('simPayBtn');
  btn.disabled = true;
  btn.textContent = 'Memproses simulasi...';

  try {
    const res  = await fetch(simConfirmUrl, { method: 'POST',
      headers: { 'Content-Type': 'application/json' } });
    const data = await res.json();

    if (data.success) {
      setQRISStatus('success', '✅ Simulasi berhasil! Menunggu konfirmasi...');
      // Polling akan detect settlement dalam ≤2 detik
    } else {
      setQRISStatus('error', data.message || 'Gagal simulasi.');
      btn.disabled = false;
      btn.textContent = '✅ Simulasi: Konfirmasi Bayar';
    }
  } catch {
    setQRISStatus('error', 'Koneksi gagal.');
    btn.disabled = false;
  }
}

/* ── Polling ─────────────────────────────────────────────── */
function startPolling() {
  stopPolling();
  const deadline = Date.now() + POLL_TIMEOUT;
  statusPoller = setInterval(async () => {
    if (Date.now() > deadline) {
      stopPolling();
      setQRISStatus('error', '⏱ Waktu habis. Tutup dan coba lagi.');
      return;
    }
    await pollOnce(true);
  }, POLL_INTERVAL);
}

function stopPolling() {
  if (statusPoller) { clearInterval(statusPoller); statusPoller = null; }
}

async function pollOnce(isAuto) {
  if (!qrisReferenceId) return;
  try {
    const res  = await fetch(`/customer/payment/qris/status/${qrisReferenceId}`);
    const data = await res.json();
    await handleStatus(data.status, isAuto);
  } catch { /* silent on auto */ }
}

async function checkPaymentStatus() {
  const btn = document.getElementById('checkStatusBtn');
  btn.disabled = true;
  btn.textContent = 'Memeriksa...';
  await pollOnce(false);
  btn.disabled = false;
  btn.textContent = 'Cek Status Pembayaran';
}

/* ── Handle Status ───────────────────────────────────────── */
async function handleStatus(status, isAuto) {
  switch (status) {
    case 'settlement':
    case 'capture':
      stopPolling();
      setQRISStatus('success', '✅ Pembayaran dikonfirmasi! Menyimpan...');
      await finalizePayment();
      break;
    case 'pending':
      if (!isAuto) setQRISStatus('pending', '⏳ Menunggu pembayaran...');
      break;
    case 'expire':
    case 'cancel':
      stopPolling();
      setQRISStatus('error', '❌ QRIS kadaluarsa. Tutup dan buat baru.');
      break;
    default:
      if (!isAuto) setQRISStatus('pending', `Status: ${status}`);
  }
}

/* ── Finalize ke Server ──────────────────────────────────── */
async function finalizePayment() {
  try {
    const res  = await fetch('/customer/payment/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reservation_id: RESERVATION_ID,
        reference_id:   qrisReferenceId,
        method:         'cashless',
      }),
    });
    const data = await res.json();

    if (data.success) {
      setQRISStatus('success', '✅ Tersimpan! Mengalihkan ke dashboard...');
      setTimeout(() => { window.location.href = data.redirect_url || '/customer/dashboard'; }, 1500);
    } else {
      setQRISStatus('error', data.message || 'Gagal konfirmasi. Hubungi admin.');
    }
  } catch {
    setQRISStatus('error', 'Koneksi gagal saat konfirmasi.');
  }
}

/* ── Helpers ─────────────────────────────────────────────── */
function showEl(id) { const e = document.getElementById(id); if (e) e.style.display = ''; }
function hideEl(id) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }

function setQRISStatus(type, msg) {
  const el = document.getElementById('qrisStatus');
  el.className = `qris-status ${type}`;
  el.textContent = msg;
}

function showQRISError(msg) {
  hideEl('qrisLoading');
  showEl('qrisCodeDisplay');
  const img = document.getElementById('qrisImage');
  if (img) img.style.display = 'none';
  hideEl('simSection');
  setQRISStatus('error', msg);
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeQRISPopup(); });