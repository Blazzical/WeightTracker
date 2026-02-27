/* Client-side table sorting for sortable-table tables */
document.querySelectorAll('.sortable-table').forEach(table => {
    const headers = table.querySelectorAll('th.sortable');
    let currentCol = null;
    let ascending = true;

    headers.forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
            const col = parseInt(th.dataset.col);
            const type = th.dataset.type || 'text';

            if (currentCol === col) {
                ascending = !ascending;
            } else {
                currentCol = col;
                ascending = true;
            }

            // Update arrows
            headers.forEach(h => {
                h.querySelector('.sort-arrow').textContent = '';
            });
            th.querySelector('.sort-arrow').textContent = ascending ? ' \u25B2' : ' \u25BC';

            // Sort rows
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((a, b) => {
                let aVal = a.cells[col].textContent.trim();
                let bVal = b.cells[col].textContent.trim();

                if (type === 'num') {
                    // Parse numbers, treat '-' or empty as Infinity so they sort last
                    const aNum = parseFloat(aVal) || (aVal === '-' || aVal === '' ? Infinity : 0);
                    const bNum = parseFloat(bVal) || (bVal === '-' || bVal === '' ? Infinity : 0);
                    return ascending ? aNum - bNum : bNum - aNum;
                } else {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                    if (aVal < bVal) return ascending ? -1 : 1;
                    if (aVal > bVal) return ascending ? 1 : -1;
                    return 0;
                }
            });

            rows.forEach(row => tbody.appendChild(row));
        });
    });
});
