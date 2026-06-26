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
});
