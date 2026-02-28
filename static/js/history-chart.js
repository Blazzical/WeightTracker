/**
 * History page trend chart — Cal bars (vs target) + single weight line (AM→PM→AM→PM…)
 * with linear-regression trend line and summary stats.
 */
function initHistoryChart(historyData, targetCalories) {
    if (!historyData || historyData.length === 0) return;

    // Data arrives newest-first from the template; reverse to chronological order
    const allData = historyData.slice().reverse();

    let chart = null;
    let currentRange = 'month'; // default

    // Simple linear regression: returns {slope, intercept} for arrays of x,y pairs
    function linReg(points) {
        var n = points.length;
        if (n < 2) return null;
        var sx = 0, sy = 0, sxx = 0, sxy = 0;
        for (var i = 0; i < n; i++) {
            sx += points[i][0];
            sy += points[i][1];
            sxx += points[i][0] * points[i][0];
            sxy += points[i][0] * points[i][1];
        }
        var denom = n * sxx - sx * sx;
        if (denom === 0) return null;
        var slope = (n * sxy - sx * sy) / denom;
        var intercept = (sy - slope * sx) / n;
        return { slope: slope, intercept: intercept };
    }

    function buildChart(range) {
        var data = range === 'month' ? allData.slice(-30) : allData;

        // Interleave: each day gets two x-axis slots (AM, PM)
        var labels = [];
        var calBars = [];
        var weightLine = [];
        var barColors = [];
        var barBorders = [];
        var targetLine = [];

        data.forEach(function(d) {
            var cal = d.totals ? d.totals.calories : 0;
            var overTarget = targetCalories && cal > targetCalories;

            // AM slot — carries the calorie bar
            labels.push(d.date);
            calBars.push(cal);
            weightLine.push(d.weight_morning || null);
            barColors.push(overTarget ? 'rgba(220,53,69,0.5)' : 'rgba(25,135,84,0.5)');
            barBorders.push(overTarget ? 'rgba(220,53,69,0.8)' : 'rgba(25,135,84,0.8)');
            if (targetCalories) targetLine.push(targetCalories);

            // PM slot — no bar, just weight
            labels.push('');
            calBars.push(null);
            weightLine.push(d.weight_night || null);
            barColors.push('rgba(0,0,0,0)');
            barBorders.push('rgba(0,0,0,0)');
            if (targetCalories) targetLine.push(targetCalories);
        });

        // Compute weight axis bounds: 10% padding below min and above max
        var allWeights = weightLine.filter(function(v) { return v != null; });
        var weightMin, weightMax;
        if (allWeights.length > 0) {
            var wMin = Math.min.apply(null, allWeights);
            var wMax = Math.max.apply(null, allWeights);
            var wRange = wMax - wMin || 1;
            weightMin = Math.floor((wMin - wRange * 0.1) * 10) / 10;
            weightMax = Math.ceil((wMax + wRange * 0.1) * 10) / 10;
        }

        // Build trend line via linear regression on non-null weight points
        var regPoints = [];
        for (var i = 0; i < weightLine.length; i++) {
            if (weightLine[i] != null) regPoints.push([i, weightLine[i]]);
        }
        var trendData = new Array(labels.length).fill(null);
        var reg = linReg(regPoints);
        if (reg && regPoints.length >= 2) {
            var firstIdx = regPoints[0][0];
            var lastIdx = regPoints[regPoints.length - 1][0];
            trendData[firstIdx] = reg.slope * firstIdx + reg.intercept;
            trendData[lastIdx] = reg.slope * lastIdx + reg.intercept;
        }

        // Datasets
        var datasets = [
            {
                label: 'Calories',
                data: calBars,
                backgroundColor: barColors,
                borderColor: barBorders,
                borderWidth: 1,
                yAxisID: 'yCal',
                order: 3,
                skipNull: true
            },
            {
                label: 'Weight',
                data: weightLine,
                type: 'line',
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13,110,253,0.1)',
                borderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4,
                tension: 0.3,
                spanGaps: true,
                yAxisID: 'yWeight',
                order: 1
            },
            {
                label: 'Trend',
                data: trendData,
                type: 'line',
                borderColor: 'rgba(13,110,253,0.45)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                spanGaps: true,
                tension: 0,
                yAxisID: 'yWeight',
                order: 0
            }
        ];

        // Target line dataset
        if (targetCalories) {
            datasets.push({
                label: 'Target',
                data: targetLine,
                type: 'line',
                borderColor: '#fd7e14',
                borderWidth: 2,
                borderDash: [6, 4],
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                yAxisID: 'yCal',
                order: 2
            });
        }

        if (chart) {
            chart.destroy();
            chart = null;
        }

        var ctx = document.getElementById('historyChart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12, padding: 8, font: { size: 11 },
                            filter: function(item) {
                                return item.text !== 'Trend';
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(items) {
                                var idx = items[0].dataIndex;
                                while (idx > 0 && labels[idx] === '') idx--;
                                var isAM = items[0].dataIndex % 2 === 0;
                                return labels[idx] + (isAM ? ' AM' : ' PM');
                            },
                            label: function(ctx) {
                                if (ctx.dataset.label === 'Trend') return '';
                                if (ctx.dataset.label === 'Target') {
                                    return 'Target: ' + ctx.parsed.y + ' Cal';
                                }
                                if (ctx.dataset.label === 'Calories') {
                                    if (ctx.parsed.y == null) return '';
                                    var s = 'Calories: ' + Math.round(ctx.parsed.y);
                                    if (targetCalories) {
                                        var diff = Math.round(ctx.parsed.y - targetCalories);
                                        s += diff >= 0
                                            ? ' (+' + diff + ' over)'
                                            : ' (' + diff + ' under)';
                                    }
                                    return s;
                                }
                                if (ctx.parsed.y == null) return '';
                                return 'Weight: ' + ctx.parsed.y.toFixed(1) + ' kg';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 15,
                            font: { size: 10 },
                            callback: function(value, index) {
                                return labels[index] || null;
                            }
                        }
                    },
                    yCal: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        title: { display: true, text: 'Cal', font: { size: 11 } },
                        ticks: { font: { size: 10 } }
                    },
                    yWeight: {
                        type: 'linear',
                        position: 'right',
                        min: weightMin,
                        max: weightMax,
                        title: { display: true, text: 'kg', font: { size: 11 } },
                        ticks: { font: { size: 10 } },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });

        // --- Summary stats ---
        updateStats(data);
    }

    // Check if a day has all three main meals logged
    function hasAllMeals(d) {
        var mt = d.totals && d.totals.meal_times ? d.totals.meal_times : [];
        return mt.indexOf('breakfast') !== -1
            && mt.indexOf('lunch') !== -1
            && mt.indexOf('dinner') !== -1;
    }

    function updateStats(data) {
        var el = document.getElementById('chartStats');
        if (!el) return;

        if (data.length < 2) { el.innerHTML = ''; return; }

        // Only include days with all 3 main meals for calorie averages
        var completeDays = data.filter(hasAllMeals);
        var dayWeights = []; // {day index, weight} from AM readings
        data.forEach(function(d, i) {
            if (d.weight_morning) dayWeights.push({ idx: i, w: d.weight_morning });
        });

        var lines = [];

        if (completeDays.length > 0) {
            var totalCal = 0;
            for (var i = 0; i < completeDays.length; i++) {
                totalCal += completeDays[i].totals.calories;
            }
            var avgDailyCal = totalCal / completeDays.length;
            lines.push('<strong>Avg daily intake:</strong> ' + Math.round(avgDailyCal) + ' Cal'
                + ' <small>(' + completeDays.length + ' full days)</small>');

            // Average daily deficit/surplus (needs target)
            if (targetCalories) {
                var avgDailyDiff = avgDailyCal - targetCalories;
                var diffLabel = avgDailyDiff >= 0 ? 'surplus' : 'deficit';
                lines.push('<strong>Avg daily ' + diffLabel + ':</strong> ' + Math.abs(Math.round(avgDailyDiff)) + ' Cal');

                var avgWeeklyDiff = avgDailyDiff * 7;
                lines.push('<strong>Avg weekly ' + diffLabel + ':</strong> ' + Math.abs(Math.round(avgWeeklyDiff)) + ' Cal');
            }
        }

        // Average weekly weight change (using first & last AM weight)
        if (dayWeights.length >= 2) {
            var first = dayWeights[0];
            var last = dayWeights[dayWeights.length - 1];
            var span = last.idx - first.idx; // days between
            if (span > 0) {
                var totalChange = last.w - first.w;
                var weeklyChange = totalChange / span * 7;
                var sign = weeklyChange >= 0 ? '+' : '';
                lines.push('<strong>Avg weekly weight change:</strong> ' + sign + weeklyChange.toFixed(2) + ' kg');

                var totalStr = totalChange >= 0 ? '+' : '';
                lines.push('<strong>Total weight change:</strong> ' + totalStr + totalChange.toFixed(1) + ' kg over ' + span + ' days');
            }
        }

        el.innerHTML = lines.join('<br>');
    }

    // Initial build
    buildChart(currentRange);

    // Toggle buttons
    document.querySelectorAll('[data-chart-range]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-chart-range]').forEach(function(b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            currentRange = btn.getAttribute('data-chart-range');
            buildChart(currentRange);
        });
    });
}
