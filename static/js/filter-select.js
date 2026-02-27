/**
 * Filterable select dropdowns.
 * Add class "select-filter" to an <input> and place it before a <select>
 * inside the same parent. Typing filters the select's options.
 */
function initFilterableSelect(input) {
    const select = input.parentElement.querySelector('select');
    if (!select || select._filterReady) return;

    // Store original options
    select._allOptions = Array.from(select.options).map(function(opt) {
        return { value: opt.value, text: opt.textContent, selected: opt.selected };
    });
    select._filterReady = true;

    input.addEventListener('input', function() {
        var filter = this.value.toLowerCase();
        var currentValue = select.value;

        select.innerHTML = '';
        select._allOptions.forEach(function(opt) {
            if (!opt.value || opt.text.toLowerCase().indexOf(filter) !== -1) {
                var option = new Option(opt.text, opt.value);
                if (opt.value === currentValue) option.selected = true;
                select.appendChild(option);
            }
        });
    });
}

function initAllFilterableSelects(root) {
    (root || document).querySelectorAll('input.select-filter').forEach(initFilterableSelect);
}

document.addEventListener('DOMContentLoaded', function() {
    initAllFilterableSelects();
});
