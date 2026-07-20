document.addEventListener("DOMContentLoaded", () => {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const forms = {
        login: document.getElementById("login-form"),
        signup: document.getElementById("signup-form"),
    };

    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;

            tabBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");

            Object.entries(forms).forEach(([key, form]) => {
                form.classList.toggle("active", key === target);
            });
        });
    });
    // Toggle show/hide passcode (khusus form login)
    document.querySelectorAll(".toggle-password-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetInput = document.getElementById(btn.dataset.target);
            const eyeIcon = btn.querySelector(".icon-eye");
            const eyeOffIcon = btn.querySelector(".icon-eye-off");

            const isHidden = targetInput.type === "password";
            targetInput.type = isHidden ? "text" : "password";
            eyeIcon.style.display = isHidden ? "none" : "block";
            eyeOffIcon.style.display = isHidden ? "block" : "none";
        });
    });
});
