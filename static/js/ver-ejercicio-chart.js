document.addEventListener("DOMContentLoaded", () => {
    // 1) Lee el JSON inyectado
    const raw = document.getElementById("chart-data")?.textContent;
    if (!raw) return;
    const chartData = JSON.parse(raw);

    // 2) Formatea las fechas "DD/MM/YYYY" a algo legible ("D abr.", etc.)
    const formattedLabels = chartData.labels.map(label => {
        const [d, m, y] = label.split("/");
        // Construye un Date en UTC para no desincronizar mes
        const date = new Date(`${y}-${m}-${d}T00:00:00`);
        return date.toLocaleDateString("es-ES", {
            day:   "numeric",
            month: "short"
        });
    });

    // 3) Obtiene el contexto del canvas
    const ctx = document.getElementById("chart-1rm")?.getContext("2d");
    if (!ctx) return;

    // 4) Crea el gráfico
    new Chart(ctx, {
        type: "line",
        data: {
            labels: formattedLabels,
            datasets: [{
                label: "1RM estimado",
                data: chartData.values,
                fill: false,
                tension: 0.1,
                borderColor: "#10b981",
                backgroundColor: "#10b981"
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: "Fecha" }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "1RM (kg)" }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
});
