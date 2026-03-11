document.addEventListener("DOMContentLoaded", function () {

    const rawData = document.getElementById("progress-data");
    if (!rawData) return;

    const progressData = JSON.parse(rawData.textContent);

    const canvas = document.getElementById("progressChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    const labels = progressData.map(item =>
        new Date(item.date).getDate()
    );

    const values = progressData.map(item => item.adherence);

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Success Rate %",
                data: values,
                borderColor: "#c74c4c",
                backgroundColor: "rgba(199, 76, 76, 0.15)",
                pointBackgroundColor: "#c74c4c",
                borderWidth: 3,
                tension: 0.3,
                fill: true,
                spanGaps: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 10,
                        autoSkip: false,
                        callback: function (value) {
                            return value + "%";
                        }
                    },
                    grid: {
                        drawBorder: true
                    }
                }
            }
        }
    });

});