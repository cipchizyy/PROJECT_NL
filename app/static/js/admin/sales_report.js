(function () {
  "use strict";

  /**
   * 1) Render chart revenue per hari pakai Chart.js,
   *    datanya diambil dari <script id="sr-chart-data"> yang di-render Jinja.
   */
  function renderRevenueChart() {
    const canvas = document.getElementById("sr-revenue-chart");
    const dataEl = document.getElementById("sr-chart-data");
    if (!canvas || !dataEl || typeof Chart === "undefined") return;

    let payload;
    try {
      payload = JSON.parse(dataEl.textContent);
    } catch (err) {
      console.error("Gagal parse data chart sales report:", err);
      return;
    }

    const labels = payload.labels || [];
    const values = payload.values || [];
    if (labels.length === 0) return;

    new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Revenue (Rp)",
            data: values,
            borderColor: "#2f6fed",
            backgroundColor: "rgba(47, 111, 237, 0.12)",
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 3,
            pointBackgroundColor: "#2f6fed",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return "Rp " + Number(ctx.parsed.y).toLocaleString("id-ID");
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (val) {
                return "Rp " + Number(val).toLocaleString("id-ID");
              },
            },
          },
        },
      },
    });
  }

  /**
   * 2) Live search sederhana di tabel detail transaksi.
   *    Filter berdasarkan Reservasi ID dan Metode (client-side, tanpa reload).
   */
  function setupTableSearch() {
    const input = document.getElementById("sr-search");
    const table = document.getElementById("sr-table");
    if (!input || !table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));

    input.addEventListener("input", function () {
      const keyword = input.value.trim().toLowerCase();

      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(keyword) ? "" : "none";
      });
    });
  }

  /**
   * 3) Pastikan tombol "Download PDF" selalu membawa filter tanggal
   *    yang sedang aktif di form, meskipun user mengubah tanggal
   *    tanpa klik "Terapkan" dulu.
   */
  function setupDownloadLinkSync() {
    const form = document.getElementById("sr-filter-form");
    const downloadBtn = document.getElementById("sr-download-btn");
    if (!form || !downloadBtn) return;

    function syncDownloadUrl() {
      const startDate = form.querySelector("#start_date").value;
      const endDate = form.querySelector("#end_date").value;

      const url = new URL(downloadBtn.href, window.location.origin);
      if (startDate) {
        url.searchParams.set("start_date", startDate);
      } else {
        url.searchParams.delete("start_date");
      }
      if (endDate) {
        url.searchParams.set("end_date", endDate);
      } else {
        url.searchParams.delete("end_date");
      }
      downloadBtn.href = url.pathname + url.search;
    }

    form.querySelectorAll("input[type='date']").forEach(function (el) {
      el.addEventListener("change", syncDownloadUrl);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderRevenueChart();
    setupTableSearch();
    setupDownloadLinkSync();
  });
})();