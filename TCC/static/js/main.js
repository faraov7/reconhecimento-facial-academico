(() => {
    const chartEl = document.getElementById("chartAcessos");
    if (!chartEl || typeof Chart === "undefined") return;

    const labels = window.relatorioLabels || [];
    const reconhecido = window.relatorioReconhecido || [];
    const desconhecido = window.relatorioDesconhecido || [];

    new Chart(chartEl, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Reconhecido",
                    data: reconhecido,
                    borderColor: "#3EE084",
                    backgroundColor: "rgba(62, 224, 132, 0.15)",
                    fill: true,
                    tension: 0.35,
                },
                {
                    label: "Desconhecido",
                    data: desconhecido,
                    borderColor: "#FFC14D",
                    backgroundColor: "rgba(255, 193, 77, 0.14)",
                    fill: true,
                    tension: 0.35,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#A7C4DF" }, grid: { color: "rgba(255,255,255,0.06)" } },
                y: { ticks: { color: "#A7C4DF" }, grid: { color: "rgba(255,255,255,0.06)" } },
            },
            plugins: {
                legend: {
                    labels: { color: "#DCEEFF" },
                },
            },
        },
    });
})();
