document.addEventListener("DOMContentLoaded", () => {
    const inputs = document.querySelectorAll(".otp-inputs input");

    // --- Auto pindah fokus ke kotak berikutnya setelah isi 1 digit ---
    inputs.forEach((input, index) => {
        input.addEventListener("input", () => {
            // Hanya terima angka
            input.value = input.value.replace(/[^0-9]/g, "");

            if (input.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });

        // --- Dukung paste kode 6 digit sekaligus ---
        input.addEventListener("paste", (e) => {
            e.preventDefault();
            const pasted = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, 6);

            pasted.split("").forEach((digit, i) => {
                if (inputs[i]) inputs[i].value = digit;
            });

            const nextEmptyIndex = Math.min(pasted.length, inputs.length - 1);
            inputs[nextEmptyIndex].focus();
        });
    });

    // --- Countdown tombol "Kirim ulang kode" ---
    const resendBtn = document.getElementById("resend-btn");
    const countdownSpan = document.getElementById("countdown");
    let secondsLeft = 60;

    resendBtn.disabled = true;

    const timer = setInterval(() => {
        secondsLeft -= 1;
        countdownSpan.textContent = secondsLeft;

        if (secondsLeft <= 0) {
            clearInterval(timer);
            resendBtn.disabled = false;
            resendBtn.textContent = "Kirim ulang kode";
        }
    }, 1000);
});