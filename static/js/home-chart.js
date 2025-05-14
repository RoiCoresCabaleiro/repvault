document.addEventListener("DOMContentLoaded", () => {
    // 1) Leer datos inyectados por Jinja
    const raw = document.getElementById("week-data")?.textContent;
    if (!raw) return;
    const { labels, counts, max } = JSON.parse(raw);

    // 2) Generar un dataset apilado por cada unidad de entrenamiento
    const datasets = Array.from({ length: max }, (_, level) => ({
        label: '',
        data: counts.map(c => c > level ? 1 : 0),
        backgroundColor: "rgba(16, 185, 129, 1)",
        borderColor: 'transparent',
        borderWidth: 1,
        borderSkipped: false,
        borderRadius: { topLeft: 4, topRight: 4, bottomRight: 4, bottomLeft: 4 },
        stack: 'stack1'
    }));

    // 3) Inicializar el chart en modo apilado
    const ctx = document.getElementById("weekChart")?.getContext("2d");
    if (!ctx) return;
    new Chart(ctx, {
        type: "bar",
        data: { labels, datasets },
        options: {
        plugins: {
            legend: { display: false },
            tooltip: { enabled: false }
        },
        scales: {
            x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0 } },
            y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 } }
        },
        datasets: {
            bar: { barPercentage: 0.8, categoryPercentage: 0.7 }
        }
        }
    });
});
