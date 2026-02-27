/* Usage detail modal - click on use counts to see where items are used */
document.querySelectorAll('.usage-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const url = this.dataset.url;
        const type = this.dataset.type; // 'days' or 'meals'

        const modal = new bootstrap.Modal(document.getElementById('usageModal'));
        document.getElementById('usageModalTitle').textContent = 'Loading...';
        document.getElementById('usageModalBody').innerHTML = '<p class="text-muted">Loading...</p>';
        modal.show();

        fetch(url)
            .then(r => r.json())
            .then(data => {
                document.getElementById('usageModalTitle').textContent = data.name;
                let html = '';

                if (type === 'days' && data.days && data.days.length > 0) {
                    html = '<table class="table table-sm table-hover mb-0">';
                    html += '<thead><tr><th>Date</th><th>Meal Time</th><th class="text-end">Qty</th></tr></thead><tbody>';
                    data.days.forEach(d => {
                        html += '<tr>';
                        html += '<td><a href="/log/' + d.date + '">' + d.date + '</a></td>';
                        html += '<td>' + d.meal_time + '</td>';
                        html += '<td class="text-end">' + d.quantity + '</td>';
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                } else if (type === 'meals' && data.meals && data.meals.length > 0) {
                    html = '<table class="table table-sm table-hover mb-0">';
                    html += '<thead><tr><th>Meal</th><th class="text-end">Qty</th></tr></thead><tbody>';
                    data.meals.forEach(m => {
                        html += '<tr>';
                        html += '<td><a href="/meals/' + m.id + '/edit">' + m.name + '</a></td>';
                        html += '<td class="text-end">' + m.quantity + '</td>';
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                } else {
                    html = '<p class="text-muted">No usage found.</p>';
                }

                document.getElementById('usageModalBody').innerHTML = html;
            });
    });
});
