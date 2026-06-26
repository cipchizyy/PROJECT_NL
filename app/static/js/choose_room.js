document.addEventListener("DOMContentLoaded", function () {
    const filterButtons = document.querySelectorAll(".filter-btn");
    const roomCards = document.querySelectorAll(".room-card");
    const readyButtons = document.querySelectorAll(".room-btn.ready");

    filterButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const selectedCategory = button.dataset.filter;

            filterButtons.forEach(function (btn) {
                btn.classList.remove("active");
            });

            button.classList.add("active");

            roomCards.forEach(function (card) {
                const cardCategory = card.dataset.category;

                if (cardCategory === selectedCategory) {
                    card.style.display = "block";
                } else {
                    card.style.display = "none";
                }
            });
        });
    });

    readyButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const roomCode = button.dataset.room;
            const roomPrice = button.dataset.price;

            localStorage.setItem("selectedRoom", roomCode);
            localStorage.setItem("selectedRoomPrice", roomPrice);

            window.location.href = "/customer/payment?room=" + encodeURIComponent(roomCode);
        });
    });
});