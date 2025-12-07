document.addEventListener('DOMContentLoaded', function(){
    const form = document.getElementById('search-form');
    const cityInput = document.getElementById('city-input');
    const resultBox = document.getElementById('result-box');
    const statusBox = document.getElementById('status-box');
    let chart = null;
    const chartCanvasId = 'forecast-chart';

    async function ensureChartJs(){
        if (typeof Chart === 'undefined'){
            await new Promise((resolve, reject) => {
                const s = document.createElement('script');
                s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
                s.onload = resolve; s.onerror = reject; document.head.appendChild(s);
            });
        }
    }

    form.addEventListener('submit', async function(e){
        e.preventDefault();
        const city = cityInput.value.trim();
        if(!city) return;
        statusBox.innerHTML = '<div class="loader" aria-hidden="true"></div>';
        resultBox.innerHTML = '';

        try{
            const res = await fetch('/api/forecast?days=7', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({city})
            });

            const data = await res.json();
            if(!data.success){
                statusBox.innerHTML = `<div class="error">${data.error || 'Unknown error'}</div>`;
                tidyEmpty();
                return;
            }

            const w = data.weather_data;
            statusBox.innerHTML = '';

            // render result card (show both °C and °F)
            resultBox.innerHTML = `
                <div class="card">
                    <div class="row">
                        <div>
                            <div class="city">${w.city}</div>
                            <div class="desc">${w.description}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px">
                            ${w.icon_url? `<img src="${w.icon_url}" width="64" height="64" alt="icon">` : ''}
                            <div style="text-align:right">
                                <div class="temp">${w.temp}°C / ${w.temp_f}°F</div>
                                <div class="small">Feels like ${w.feels_like}°C / ${w.feels_like_f}°F • ${w.humidity}% humidity</div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center">
                        <div class="small">Model prediction (tomorrow)</div>
                        <div class="predict"><div style="font-weight:800;font-size:20px">${w.predicted_temp}°C / ${w.predicted_temp_f}°F</div></div>
                    </div>
                </div>
            `;
            tidyEmpty();

            // render chart container (centered and larger)
                        // build small forecast list for the next days
            const daily = w.daily || [];
            const forecastItems = daily.map(d => {
                const label = d.date || '';
                const tempText =
                    (d.predicted_temp === null || typeof d.predicted_temp === 'undefined')
                        ? 'N/A'
                        : `${d.predicted_temp}°C`;
                const desc = d.description || '';
                return `
                    <div class="forecast-item">
                        <div class="forecast-date">${label}</div>
                        <div class="forecast-temp">${tempText}</div>
                        <div class="forecast-desc">${desc}</div>
                    </div>
                `;
            }).join('');

            // render forecast box (left) + chart (right)
            const chartHtml = `
                <div class="card chart-layout" style="margin-top:18px">
                    <div class="forecast-list">
                        <div class="small" style="margin-bottom:6px;">
                            Next ${daily.length} day(s)
                        </div>
                        ${forecastItems || '<div class="small">No forecast data available.</div>'}
                    </div>
                    <div class="chart-container">
                        <canvas id="${chartCanvasId}"></canvas>
                    </div>
                </div>
            `;
            resultBox.insertAdjacentHTML('beforeend', chartHtml);
            tidyEmpty();

            // prepare data for chart using the same daily list
            const labels = daily.map(d => d.date);
            const avgTempsC = daily.map(d => d.avg_temp === null ? NaN : d.avg_temp);
            const avgTempsF = daily.map(d => d.avg_temp_f === null ? NaN : d.avg_temp_f);
            const predsC = daily.map(d => d.predicted_temp === null ? NaN : d.predicted_temp);
            const predsF = daily.map(d => d.predicted_temp_f === null ? NaN : d.predicted_temp_f);


            await ensureChartJs();

            const ctx = document.getElementById(chartCanvasId).getContext('2d');
            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Avg temp (°C)',
                            data: avgTempsC,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37,99,235,0.08)',
                            tension: 0.4,
                            spanGaps: true
                        },
                        {
                            label: 'Avg temp (°F)',
                            data: avgTempsF,
                            borderColor: '#60a5fa',
                            backgroundColor: 'rgba(96,165,250,0.06)',
                            tension: 0.4,
                            borderDash: [4,2],
                            spanGaps: true
                        },
                        {
                            label: 'Predicted (°C)',
                            data: predsC,
                            borderColor: '#f97316',
                            backgroundColor: 'rgba(249,115,22,0.06)',
                            tension: 0.4,
                            borderDash: [6,3],
                            spanGaps: true
                        },
                        {
                            label: 'Predicted (°F)',
                            data: predsF,
                            borderColor: '#fb923c',
                            backgroundColor: 'rgba(251,146,60,0.04)',
                            tension: 0.4,
                            borderDash: [6,3],
                            spanGaps: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: false }
                    },
                    plugins: { legend: { position: 'bottom' } }
                }
            });

            tidyEmpty();

            // render past week table (observed averages) if available
            const past = (w.past_week || []);
            if (past.length > 0) {
                const rows = past.map(p => {
                    const c = (p.avg_temp === null || typeof p.avg_temp === 'undefined') ? 'N/A' : `${p.avg_temp}°C`;
                    const f = (p.avg_temp_f === null || typeof p.avg_temp_f === 'undefined') ? 'N/A' : `${p.avg_temp_f}°F`;
                    return `<tr><td>${p.date}</td><td style="text-align:right">${c}</td><td style="text-align:right">${f}</td></tr>`;
                }).join('');

                const pastHtml = `
                    <div class="card" style="margin-top:14px">
                        <div class="small">Past week (observed averages)</div>
                        <div style="overflow:auto;margin-top:8px">
                            <table class="past-table" style="width:100%;border-collapse:collapse">
                                <thead>
                                    <tr style="color:#334155;font-weight:600;text-align:left"><th>Date</th><th style="text-align:right">Avg (°C)</th><th style="text-align:right">Avg (°F)</th></tr>
                                </thead>
                                <tbody>${rows}</tbody>
                            </table>
                        </div>
                    </div>
                `;
                resultBox.insertAdjacentHTML('beforeend', pastHtml);
                tidyEmpty();
            }

        }catch(err){
            statusBox.innerHTML = `<div class="error">Network error: ${err.message}</div>`;
            tidyEmpty();
        }
    });

    // hide empty placeholders on load
    const cardsEl = document.querySelector('.cards');
    function tidyEmpty() {
}


    tidyEmpty();
    // run again after a short delay (in case server injected content)
});
