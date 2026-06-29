document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".admin-sidebar");
    const hamburgerBtn = document.querySelector(".sidebar-hamburger-btn");
    const overlay = document.querySelector(".sidebar-overlay");

    if (!sidebar || !hamburgerBtn || !overlay) return;

    function openSidebar() {
        sidebar.classList.add("open");
        overlay.classList.add("active");
    }

    function closeSidebar() {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
    }

    hamburgerBtn.addEventListener("click", () => {
        const isOpen = sidebar.classList.contains("open");
        isOpen ? closeSidebar() : openSidebar();
    });

    // Klik di area gelap luar sidebar -> tutup
    overlay.addEventListener("click", closeSidebar);

    // Klik salah satu link menu di sidebar -> otomatis tutup (mobile UX biasa)
    sidebar.querySelectorAll(".sidebar-link").forEach((link) => {
        link.addEventListener("click", closeSidebar);
    });

    // Tutup otomatis kalau ukuran layar dibesarkan balik ke desktop
    window.addEventListener("resize", () => {
        if (window.innerWidth > 880) closeSidebar();
    });
});