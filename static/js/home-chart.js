document.addEventListener("DOMContentLoaded", () => {
    // 1) Lee los datos JSON inyectados por Jinja
    const raw = document.getElementById("week-data")?.textContent;
    if (!raw) return;
    const { labels, counts, max } = JSON.parse(raw);

    // 2) Inicializa el canvas de Chart.js
    const ctx = document.getElementById("weekChart")?.getContext("2d");
    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Entrenamientos",
                data: counts,
                backgroundColor: "rgba(165, 180, 252, 0.8)",
                borderColor:     "rgba(165, 180, 252, 1)",
                borderWidth: 1,
            }]
        },
        options: {
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    max: max,
                    ticks: { stepSize: 1 }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
});
