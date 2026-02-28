"""Flask application for WeightTracker."""

from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import models
from seed_data import seed

app = Flask(__name__)
app.secret_key = 'weight-tracker-local-only'


@app.before_request
def ensure_db():
    if not hasattr(app, '_db_initialized'):
        seed()
        app._db_initialized = True


# --- Dashboard (Today's Log) ---

@app.route('/')
def dashboard():
    today = date.today().isoformat()
    return redirect(url_for('daily_log', log_date=today))


# --- Components ---

@app.route('/components')
def components_page():
    query = request.args.get('q', '')
    if query:
        components = models.search_components(query)
    else:
        components = models.get_all_components()
    return render_template('components.html', components=components, query=query)


@app.route('/components/add', methods=['POST'])
def add_component():
    name = request.form.get('name', '').strip()
    kj = float(request.form.get('kj', 0) or 0)
    calories = float(request.form.get('calories', 0) or 0)
    protein_g = float(request.form.get('protein_g', 0) or 0)
    notes = request.form.get('notes', '')

    if not name:
        flash('Name is required.', 'danger')
        return redirect(url_for('components_page'))

    result = models.add_component(name, kj, calories, protein_g, notes)
    if result is None:
        flash(f'Component "{name}" already exists.', 'danger')
    else:
        flash(f'Component "{name}" added.', 'success')
    return redirect(url_for('components_page'))


@app.route('/components/<int:comp_id>/edit', methods=['POST'])
def edit_component(comp_id):
    name = request.form.get('name', '').strip()
    kj = float(request.form.get('kj', 0) or 0)
    calories = float(request.form.get('calories', 0) or 0)
    protein_g = float(request.form.get('protein_g', 0) or 0)
    notes = request.form.get('notes', '')

    if not name:
        flash('Name is required.', 'danger')
        return redirect(url_for('components_page'))

    if models.update_component(comp_id, name, kj, calories, protein_g, notes):
        flash(f'Component "{name}" updated.', 'success')
    else:
        flash(f'Component name "{name}" already exists.', 'danger')
    return redirect(url_for('components_page'))


@app.route('/components/<int:comp_id>/delete', methods=['POST'])
def delete_component(comp_id):
    models.delete_component(comp_id)
    flash('Component deleted.', 'info')
    return redirect(url_for('components_page'))


@app.route('/api/components/search')
def api_search_components():
    query = request.args.get('q', '')
    components = models.search_components(query) if query else models.get_all_components()
    return jsonify([{'id': c['id'], 'name': c['name'], 'kj': c['kj'],
                     'calories': c['calories'], 'protein_g': c['protein_g']} for c in components])


@app.route('/api/meal/<int:meal_id>/usage')
def api_meal_usage(meal_id):
    """Return list of days that use this meal."""
    rows = models.get_meal_daily_usage(meal_id)
    meal = models.get_meal(meal_id)
    return jsonify({
        'name': meal['name'] if meal else '',
        'days': [{'date': r['date'], 'meal_time': r['meal_time'], 'quantity': r['quantity']} for r in rows]
    })


@app.route('/api/component/<int:comp_id>/usage')
def api_component_usage(comp_id):
    """Return list of days that directly use this component."""
    rows = models.get_component_daily_usage(comp_id)
    comp = models.get_component(comp_id)
    return jsonify({
        'name': comp['name'] if comp else '',
        'days': [{'date': r['date'], 'meal_time': r['meal_time'], 'quantity': r['quantity']} for r in rows]
    })


@app.route('/api/component/<int:comp_id>/meals')
def api_component_meals(comp_id):
    """Return list of meals that include this component."""
    rows = models.get_component_meal_usage(comp_id)
    comp = models.get_component(comp_id)
    return jsonify({
        'name': comp['name'] if comp else '',
        'meals': [{'id': r['id'], 'name': r['name'], 'quantity': r['quantity']} for r in rows]
    })


# --- Meals ---

@app.route('/meals')
def meals_page():
    query = request.args.get('q', '')
    if query:
        meals = models.search_meals(query)
    else:
        meals = models.get_all_meals()
    return render_template('meals.html', meals=meals, query=query)


@app.route('/meals/add', methods=['POST'])
def add_meal():
    name = request.form.get('name', '').strip()
    kj = request.form.get('kj_override', '')
    cal = request.form.get('calories_override', '')
    prot = request.form.get('protein_override', '')

    kj_override = float(kj) if kj else None
    cal_override = float(cal) if cal else None
    prot_override = float(prot) if prot else None

    if not name:
        flash('Meal name is required.', 'danger')
        return redirect(url_for('meals_page'))

    meal_id = models.add_meal(name, kj_override, cal_override, prot_override)
    if meal_id is None:
        flash(f'Meal "{name}" already exists.', 'danger')
        return redirect(url_for('meals_page'))

    flash(f'Meal "{name}" created.', 'success')
    return redirect(url_for('edit_meal', meal_id=meal_id))


@app.route('/meals/<int:meal_id>/edit', methods=['GET'])
def edit_meal(meal_id):
    meal = models.get_meal(meal_id)
    if not meal:
        flash('Meal not found.', 'danger')
        return redirect(url_for('meals_page'))

    components = models.get_all_components()
    return render_template('meal_edit.html', meal=meal, components=components)


@app.route('/meals/<int:meal_id>/save', methods=['POST'])
def save_meal(meal_id):
    name = request.form.get('name', '').strip()
    kj = request.form.get('kj_override', '')
    cal = request.form.get('calories_override', '')
    prot = request.form.get('protein_override', '')
    notes = request.form.get('notes', '')

    kj_override = float(kj) if kj else None
    cal_override = float(cal) if cal else None
    prot_override = float(prot) if prot else None

    models.update_meal(meal_id, name, kj_override, cal_override, prot_override, notes)

    # Save components
    comp_ids = request.form.getlist('comp_id')
    comp_qtys = request.form.getlist('comp_qty')
    components_list = []
    for i in range(len(comp_ids)):
        if comp_ids[i]:
            qty = float(comp_qtys[i]) if i < len(comp_qtys) and comp_qtys[i] else 1
            components_list.append((int(comp_ids[i]), qty))
    models.save_meal_components(meal_id, components_list)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        meal = models.get_meal(meal_id)
        return jsonify({'status': 'ok', 'totals': {
            'kj': meal['total_kj'], 'calories': meal['total_calories'], 'protein': meal['total_protein']
        }})

    flash('Meal saved.', 'success')
    return redirect(url_for('edit_meal', meal_id=meal_id))


@app.route('/meals/<int:meal_id>/delete', methods=['POST'])
def delete_meal(meal_id):
    models.delete_meal(meal_id)
    flash('Meal deleted.', 'info')
    return redirect(url_for('meals_page'))


# --- Daily Log ---

@app.route('/log/<log_date>')
def daily_log(log_date):
    try:
        dt = datetime.strptime(log_date, '%Y-%m-%d').date()
    except ValueError:
        return redirect(url_for('dashboard'))

    log = models.get_or_create_daily_log(log_date)
    entries = models.get_daily_entries(log['id'])
    totals = models.calc_daily_totals(log['id'])
    target = models.get_active_target()
    meals = models.get_all_meals()
    components = models.get_all_components()

    prev_date = (dt - timedelta(days=1)).isoformat()
    next_date = (dt + timedelta(days=1)).isoformat()

    # Group entries by meal_time
    grouped = {}
    for label in ['breakfast', 'lunch', 'dinner', 'snack', 'coffee', 'other']:
        grouped[label] = [e for e in entries if e['meal_time'] == label]

    quick_adds = models.get_all_quick_adds()
    # Group quick adds by meal_time
    quick_adds_by_time = {}
    for qa in quick_adds:
        quick_adds_by_time.setdefault(qa['meal_time'], []).append(qa)

    rank_tiers = models.get_rank_tiers()
    day_rank = models.calc_rank(totals['calories'], rank_tiers)

    # History data for the trend chart
    history_logs = models.get_all_daily_logs()
    history = []
    for hl in history_logs:
        hl['totals'] = models.calc_daily_totals(hl['id'])
        history.append(hl)

    return render_template('daily_log.html',
                           log=log, entries=entries, grouped=grouped,
                           totals=totals, target=target,
                           meals=meals, components=components,
                           quick_adds_by_time=quick_adds_by_time,
                           log_date=log_date, dt=dt,
                           prev_date=prev_date, next_date=next_date,
                           today=date.today().isoformat(),
                           rank=day_rank, rank_tiers=rank_tiers,
                           history=history)


@app.route('/log/<log_date>/update', methods=['POST'])
def update_daily_log(log_date):
    log = models.get_or_create_daily_log(log_date)
    wm = request.form.get('weight_morning', '')
    wn = request.form.get('weight_night', '')
    weight_morning = float(wm) if wm else None
    weight_night = float(wn) if wn else None
    exercise = request.form.get('exercise', '')
    notes = request.form.get('notes', '')
    models.update_daily_log(log['id'], weight_morning, weight_night, exercise, notes)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return jsonify({'status': 'ok'})

    flash('Day updated.', 'success')
    return redirect(url_for('daily_log', log_date=log_date))


@app.route('/log/<log_date>/add-entry', methods=['POST'])
def add_daily_entry(log_date):
    log = models.get_or_create_daily_log(log_date)
    entry_type = request.form.get('entry_type', 'meal')
    meal_time = request.form.get('meal_time', 'other')
    quantity = float(request.form.get('quantity', 1) or 1)
    notes = request.form.get('entry_notes', '')

    if entry_type == 'meal':
        meal_id = request.form.get('meal_id')
        if meal_id:
            models.add_daily_entry(log['id'], meal_id=int(meal_id), quantity=quantity, meal_time=meal_time, notes=notes)
            flash('Meal added.', 'success')
    elif entry_type == 'component':
        comp_id = request.form.get('component_id')
        if comp_id:
            models.add_daily_entry(log['id'], component_id=int(comp_id), quantity=quantity, meal_time=meal_time, notes=notes)
            flash('Item added.', 'success')

    return redirect(url_for('daily_log', log_date=log_date))


@app.route('/log/<log_date>/quick-add/<int:qa_id>', methods=['POST'])
def quick_add_entry(log_date, qa_id):
    qa = models.get_quick_add(qa_id)
    if not qa:
        flash('Quick add item not found.', 'danger')
        return redirect(url_for('daily_log', log_date=log_date))

    log = models.get_or_create_daily_log(log_date)
    models.add_daily_entry(
        log['id'],
        meal_id=qa['meal_id'],
        component_id=qa['component_id'],
        quantity=qa['quantity'],
        meal_time=qa['meal_time'],
    )
    flash(f'{qa["label"]} added.', 'success')
    return redirect(url_for('daily_log', log_date=log_date))


@app.route('/log/entry/<int:entry_id>/delete', methods=['POST'])
def delete_daily_entry(entry_id):
    log_date = request.form.get('log_date', date.today().isoformat())
    models.delete_daily_entry(entry_id)
    flash('Entry removed.', 'info')
    return redirect(url_for('daily_log', log_date=log_date))


# --- History ---

@app.route('/history')
def history_page():
    logs = models.get_all_daily_logs()
    rank_tiers = models.get_rank_tiers()
    history = []
    for log in logs:
        totals = models.calc_daily_totals(log['id'])
        log['totals'] = totals
        log['rank'] = models.calc_rank(totals['calories'], rank_tiers)
        history.append(log)
    target = models.get_active_target()
    return render_template('history.html', history=history, target=target, rank_tiers=rank_tiers)


# --- Settings / Targets ---

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'add_target':
            label = request.form.get('label', '').strip()
            cal = float(request.form.get('daily_calories', 0) or 0)
            kj = float(request.form.get('daily_kj', 0) or 0)
            prot = float(request.form.get('daily_protein_g', 0) or 0)
            if label:
                models.add_target(label, cal, kj, prot)
                flash(f'Target "{label}" added.', 'success')

        elif action == 'update_target':
            target_id = int(request.form.get('target_id', 0))
            label = request.form.get('label', '').strip()
            cal = float(request.form.get('daily_calories', 0) or 0)
            kj = float(request.form.get('daily_kj', 0) or 0)
            prot = float(request.form.get('daily_protein_g', 0) or 0)
            models.update_target(target_id, label, cal, kj, prot)
            flash('Target updated.', 'success')

        elif action == 'activate_target':
            target_id = int(request.form.get('target_id', 0))
            models.set_active_target(target_id)
            flash('Active target changed.', 'success')

        elif action == 'delete_target':
            target_id = int(request.form.get('target_id', 0))
            models.delete_target(target_id)
            flash('Target deleted.', 'info')

        elif action == 'add_quick_add':
            label = request.form.get('qa_label', '').strip()
            entry_type = request.form.get('qa_entry_type', 'meal')
            meal_time = request.form.get('qa_meal_time', 'coffee')
            quantity = float(request.form.get('qa_quantity', 1) or 1)
            meal_id = None
            component_id = None
            if entry_type == 'meal':
                mid = request.form.get('qa_meal_id', '')
                meal_id = int(mid) if mid else None
            else:
                cid = request.form.get('qa_component_id', '')
                component_id = int(cid) if cid else None

            if label and (meal_id or component_id):
                models.add_quick_add(label, meal_id=meal_id, component_id=component_id,
                                     meal_time=meal_time, quantity=quantity)
                flash(f'Quick add "{label}" created.', 'success')
            else:
                flash('Label and a meal or component are required.', 'danger')

        elif action == 'delete_quick_add':
            qa_id = int(request.form.get('qa_id', 0))
            models.delete_quick_add(qa_id)
            flash('Quick add item removed.', 'info')

        return redirect(url_for('settings_page'))

    targets = models.get_all_targets()
    quick_adds = models.get_all_quick_adds()
    meals = models.get_all_meals()
    components = models.get_all_components()
    return render_template('settings.html', targets=targets, quick_adds=quick_adds,
                           meals=meals, components=components)


if __name__ == '__main__':
    import webbrowser
    import threading

    def open_browser():
        webbrowser.open('http://localhost:5001')

    threading.Timer(1.5, open_browser).start()
    app.run(debug=False, host='0.0.0.0', port=5001)
