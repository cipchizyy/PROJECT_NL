document.addEventListener("DOMContentLoaded", () => {

    // ── Elemen ───────────────────────────────────────────────
    const methodCards   = document.querySelectorAll(".method-card");
    const qrisPanel     = document.getElementById("qris-panel");
    const qrisScanArea  = document.getElementById("qris-scan-area");
    const qrisImage     = document.getElementById("qris-image");
    const qrisCountdown = document.getElementById("qris-countdown");
    const qrisStatusTxt = document.getElementById("qris-status-text");
    const qrisSimBtn    = document.getElementById("qris-sim-btn");
    const bookingBtn    = document.getElementById("booking-btn");
    const bookingNote   = document.getElementById("booking-note");

    let selectedMethod   = "cashless";  // default: cashless sudah di-select di HTML
    let currentRefId     = null;
    let pollingInterval  = null;
    let countdownTimer   = null;
    let simConfirmUrl    = null;

    // ── Toggle metode ─────────────────────────────────────────
    methodCards.forEach((card) => {
        card.addEventListener("click", () => {
            methodCards.forEach((c) => c.classList.remove("selected"));
            card.classList.add("selected");
            selectedMethod = card.dataset.method;

            if (selectedMethod === "cashless") {
                qrisPanel.classList.add("show");
                bookingNote.textContent = "Klik Booking untuk generate QR pembayaran.";
            } else {
                qrisPanel.classList.remove("show");
                hideScanArea();
                bookingNote.textContent = "Bayar tunai di kasir setelah booking dikonfirmasi.";
            }

            stopPolling();
            stopCountdown();
        });
    });

    // ── Tombol Booking ────────────────────────────────────────
    bookingBtn.addEventListener("click", async () => {
        if (selectedMethod === "cash") {
            await processCash();
        } else {
            await startQrisFlow();
        }
    });

    // ── Tombol Simulasi Bayar (testing) ───────────────────────
    qrisSimBtn.addEventListener("click", async () => {
        if (!simConfirmUrl) return;

        qrisSimBtn.disabled = true;
        qrisSimBtn.textContent = "Memproses...";

        try {
            const res = await fetch(simConfirmUrl, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                qrisStatusTxt.textContent = "✅ Pembayaran dikonfirmasi! Menyelesaikan...";
                qrisStatusTxt.className = "qris-status success";
            }
        } catch (e) {
            console.error("Sim confirm error:", e);
        }
    });

    // ── Flow Cash ─────────────────────────────────────────────
    async function processCash() {
        bookingBtn.disabled = true;
        bookingBtn.textContent = "Memproses...";

        try {
            const res = await fetch(URL_CONFIRM, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reservation_id: RESERVATION_ID,
                    reference_id: "CASH-" + Date.now(),
                    method: "cash",
                }),
            });
            const data = await res.json();
            if (data.success) {
                window.location.href = data.redirect_url || URL_DASHBOARD;
            } else {
                alert("Gagal memproses pembayaran cash.");
                bookingBtn.disabled = false;
                bookingBtn.textContent = "Booking ⚡";
            }
        } catch (e) {
            console.error(e);
            bookingBtn.disabled = false;
            bookingBtn.textContent = "Booking ⚡";
        }
    }

    // ── Flow Cashless QRIS ────────────────────────────────────
    async function startQrisFlow() {
        bookingBtn.disabled = true;
        bookingBtn.textContent = "Generating QR...";
        qrisStatusTxt.textContent = "";
        hideScanArea();

        try {
            const res = await fetch(URL_GENERATE_QRIS, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reservation_id: RESERVATION_ID,
                    amount: RESERVATION_AMOUNT,
                }),
            });

            const data = await res.json();
            if (!data.success) throw new Error("Generate QRIS gagal.");

            currentRefId   = data.reference_id;
            simConfirmUrl  = data.sim_confirm_url;

            // Tampilkan QR image
            qrisImage.src = data.qr_image_url;
            qrisScanArea.style.display = "block";
            qrisSimBtn.disabled = false;
            qrisSimBtn.textContent = "⚡ Simulasi Bayar (Testing)";

            bookingBtn.textContent = "Menunggu Pembayaran...";

            // Countdown timer 15 menit
            const expiresAt = new Date(data.expires_at);
            startCountdown(expiresAt);

            // Polling status setiap 3 detik
            startPolling(currentRefId);

        } catch (e) {
            console.error(e);
            alert("Gagal generate QR. Coba lagi.");
            bookingBtn.disabled = false;
            bookingBtn.textContent = "Booking ⚡";
        }
    }

    function hideScanArea() {
        if (qrisScanArea) qrisScanArea.style.display = "none";
    }

    // ── Polling status QRIS ───────────────────────────────────
    function startPolling(refId) {
        stopPolling();
        pollingInterval = setInterval(async () => {
            try {
                const res  = await fetch(`/customer/payment/qris/status/${refId}`);
                const data = await res.json();

                if (data.status === "settlement") {
                    stopPolling();
                    stopCountdown();
                    await finalizePayment(refId);

                } else if (data.status === "expire") {
                    stopPolling();
                    stopCountdown();
                    qrisStatusTxt.textContent = "❌ QR kadaluarsa. Silakan coba lagi.";
                    qrisStatusTxt.className = "qris-status error";
                    bookingBtn.disabled = false;
                    bookingBtn.textContent = "Booking ⚡";
                }
            } catch (e) {
                console.error("Polling error:", e);
            }
        }, 3000);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    // ── Konfirmasi final ke backend ───────────────────────────
    async function finalizePayment(refId) {
        qrisStatusTxt.textContent = "✅ Pembayaran diterima! Mengkonfirmasi...";
        qrisStatusTxt.className = "qris-status success";

        try {
            const res = await fetch(URL_CONFIRM, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reservation_id: RESERVATION_ID,
                    reference_id:   refId,
                    method:         "cashless",
                }),
            });
            const data = await res.json();
            if (data.success) {
                setTimeout(() => {
                    window.location.href = data.redirect_url || URL_DASHBOARD;
                }, 1200);
            } else {
                qrisStatusTxt.textContent = "⚠️ " + (data.message || "Konfirmasi gagal.");
                qrisStatusTxt.className = "qris-status error";
            }
        } catch (e) {
            console.error("Finalize error:", e);
        }
    }

    // ── Countdown timer ───────────────────────────────────────
    function startCountdown(expiresAt) {
        stopCountdown();
        countdownTimer = setInterval(() => {
            const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
            const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
            const ss = String(remaining % 60).padStart(2, "0");
            qrisCountdown.textContent = `${mm}:${ss}`;

            if (remaining === 0) stopCountdown();
        }, 1000);
    }

    function stopCountdown() {
        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }
    }

});