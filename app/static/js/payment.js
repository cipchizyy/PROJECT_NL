/* ============================================================
   payment.js – Next Level Gaming · Customer Payment
   ============================================================ */

'use strict';

/* ── State ───────────────────────────────────────────────── */
let selectedMethod  = document.querySelector('.method-option.active')?.dataset.method || 'cashless';
let qrisReferenceId = null;
let statusPoller    = null;
const POLL_INTERVAL = 3000; // ms
const POLL_TIMEOUT  = 300000; // 5 min

/* ── Method Selection ────────────────────────────────────── */
function selectMethod(method) {
  selectedMethod = method;

  document.querySelectorAll('.method-option').forEach(el => {
    el.classList.toggle('active', el.dataset.method === method);
  });

  document.getElementById('paymentMethodInput').value = method;

  const qrisSection = document.getElementById('qrisSection');
  qrisSection.style.display = method === 'cashless' ? 'flex' : 'none';
}

/* ── QRIS Popup ──────────────────────────────────────────── */
function openQRISPopup() {
  const modal = document.getElementById('qrisModal');
  modal.classList.add('open');
  resetQRISModal();
  generateQRIS();
}

function closeQRISPopup() {
  document.getElementById('qrisModal').classList.remove('open');
  stopPolling();
}

function closeQRISModal(event) {
  // Close only when clicking the overlay, not the box
  if (event.target === document.getElementById('qrisModal')) {
    closeQRISPopup();
  }
}

function resetQRISModal() {
  showElement('qrisLoading');
  hideElement('qrisCodeDisplay');
  const status = document.getElementById('qrisStatus');
  status.className = 'qris-status';
  status.textContent = '';
  document.getElementById('checkStatusBtn').disabled = true;
}

/* ── Generate QRIS via backend ───────────────────────────── */
async function generateQRIS() {
  try {
    const res = await fetch('/customer/payment/qris/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ reservation_id: RESERVATION_ID, amount: TOTAL_AMOUNT }),
    });

    if (!res.ok) throw new Error(`Server error: ${res.status}`);

    const data = await res.json();

    if (data.success) {
      qrisReferenceId = data.reference_id;
      document.getElementById('paymentReferenceInput').value = qrisReferenceId;

      // Show QR image
      const img = document.getElementById('qrisImage');
      img.src = data.qr_image_url || `data:image/png;base64,${data.qr_base64}`;

      // Expiry hint
      if (data.expires_at) {
        const exp = new Date(data.expires_at);
        document.getElementById('qrisExpire').textContent = `Berlaku hingga ${formatTime(exp)}`;
      }

      hideElement('qrisLoading');
      showElement('qrisCodeDisplay');
      document.getElementById('checkStatusBtn').disabled = false;

      // Auto-start polling
      startPolling();
    } else {
      showQRISError(data.message || 'Gagal membuat QRIS. Coba lagi.');
    }
  } catch (err) {
    console.error('[QRIS] Generate error:', err);
    showQRISError('Koneksi gagal. Periksa jaringan dan coba lagi.');
  }
}

/* ── Payment Status Polling ──────────────────────────────── */
function startPolling() {
  stopPolling();
  const deadline = Date.now() + POLL_TIMEOUT;
  statusPoller = setInterval(async () => {
    if (Date.now() > deadline) {
      stopPolling();
      setQRISStatus('error', '⏱ Waktu pembayaran habis. Silakan buat QRIS baru.');
      return;
    }
    await checkPaymentStatus(true);
  }, POLL_INTERVAL);
}

function stopPolling() {
  if (statusPoller) { clearInterval(statusPoller); statusPoller = null; }
}

async function checkPaymentStatus(auto = false) {
  if (!qrisReferenceId) return;

  const btn = document.getElementById('checkStatusBtn');
  if (!auto) { btn.disabled = true; btn.textContent = 'Memeriksa...'; }

  try {
    const res = await fetch(`/customer/payment/qris/status/${qrisReferenceId}`, {
      headers: { 'X-CSRFToken': getCsrfToken() },
    });

    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    switch (data.status) {
      case 'paid':
      case 'settlement':
        stopPolling();
        setQRISStatus('success', '✅ Pembayaran berhasil! Mengalihkan...');
        setTimeout(() => {
          document.getElementById('paymentForm').submit();
        }, 1500);
        break;

      case 'pending':
        if (!auto) setQRISStatus('pending', '⏳ Menunggu pembayaran...');
        break;

      case 'expire':
      case 'cancel':
        stopPolling();
        setQRISStatus('error', '❌ QRIS kadaluarsa. Buat ulang.');
        break;

      default:
        if (!auto) setQRISStatus('pending', `Status: ${data.status}`);
    }
  } catch (err) {
    console.error('[QRIS] Status check error:', err);
    if (!auto) setQRISStatus('error', 'Gagal cek status. Coba lagi.');
  } finally {
    if (!auto) {
      btn.disabled = false;
      btn.textContent = 'Cek Status Pembayaran';
    }
  }
}

/* ── Process Booking (Cash path) ─────────────────────────── */
function processBooking() {
  if (selectedMethod === 'cashless') {
    openQRISPopup();
    return;
  }

  // Cash: submit form directly
  const btn = document.getElementById('bookingBtn');
  btn.disabled = true;
  btn.textContent = 'Memproses...';
  document.getElementById('paymentForm').submit();
}

/* ── Helpers ─────────────────────────────────────────────── */
function showElement(id) { document.getElementById(id).style.display = ''; }
function hideElement(id) { document.getElementById(id).style.display = 'none'; }

function setQRISStatus(type, message) {
  const el = document.getElementById('qrisStatus');
  el.className = `qris-status ${type}`;
  el.textContent = message;
}

function showQRISError(msg) {
  hideElement('qrisLoading');
  showElement('qrisCodeDisplay');
  document.getElementById('qrisImage').style.display = 'none';
  setQRISStatus('error', msg);
}

function formatTime(date) {
  return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

function getCsrfToken() {
  return document.querySelector('input[name="csrf_token"]')?.value ||
         document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1] || '';
}

/* ── Close modal on Escape key ───────────────────────────── */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeQRISPopup();
});