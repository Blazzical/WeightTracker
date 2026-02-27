"""SQLite schema and query helpers for WeightTracker."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'weighttracker.db')

CAL_PER_KJ = 0.239006
KJ_PER_CAL = 1 / CAL_PER_KJ  # ~4.184


def fill_energy(kj, calories):
    """Auto-fill missing kJ or calories from the other."""
    if kj and not calories:
        calories = round(kj * CAL_PER_KJ, 1)
    elif calories and not kj:
        kj = round(calories * KJ_PER_CAL, 1)
    return kj or 0, calories or 0


def fill_energy_nullable(kj, calories):
    """Same as fill_energy but keeps None when both are missing (for overrides)."""
    if kj and not calories:
        return kj, round(kj * CAL_PER_KJ, 1)
    elif calories and not kj:
        return round(calories * KJ_PER_CAL, 1), calories
    return kj, calories


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kj REAL DEFAULT 0,
            calories REAL DEFAULT 0,
            protein_g REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kj_override REAL,
            calories_override REAL,
            protein_override REAL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS meal_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            quantity REAL DEFAULT 1,
            FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            weight_morning REAL,
            weight_night REAL,
            exercise TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_log_id INTEGER NOT NULL,
            meal_id INTEGER,
            component_id INTEGER,
            quantity REAL DEFAULT 1,
            meal_time TEXT DEFAULT 'other',
            notes TEXT DEFAULT '',
            FOREIGN KEY (daily_log_id) REFERENCES daily_log(id) ON DELETE CASCADE,
            FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE SET NULL,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            daily_kj REAL DEFAULT 0,
            daily_calories REAL DEFAULT 0,
            daily_protein_g REAL DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quick_add (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            meal_id INTEGER,
            component_id INTEGER,
            meal_time TEXT NOT NULL DEFAULT 'coffee',
            quantity REAL DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# --- Component helpers ---

def get_all_components():
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*,
            (SELECT COUNT(*) FROM daily_entries de WHERE de.component_id = c.id) as direct_uses,
            (SELECT COUNT(*) FROM meal_components mc WHERE mc.component_id = c.id) as meal_count
        FROM components c
        ORDER BY c.name
    """).fetchall()
    conn.close()
    return rows


def get_component(component_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM components WHERE id = ?", (component_id,)).fetchone()
    conn.close()
    return row


def search_components(query):
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*,
            (SELECT COUNT(*) FROM daily_entries de WHERE de.component_id = c.id) as direct_uses,
            (SELECT COUNT(*) FROM meal_components mc WHERE mc.component_id = c.id) as meal_count
        FROM components c
        WHERE c.name LIKE ?
        ORDER BY c.name
    """, (f'%{query}%',)).fetchall()
    conn.close()
    return rows


def add_component(name, kj, calories, protein_g, notes=''):
    kj, calories = fill_energy(kj, calories)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO components (name, kj, calories, protein_g, notes) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), kj, calories, protein_g, notes)
        )
        conn.commit()
        comp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        conn.close()
        return None
    conn.close()
    return comp_id


def update_component(component_id, name, kj, calories, protein_g, notes=''):
    kj, calories = fill_energy(kj, calories)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE components SET name=?, kj=?, calories=?, protein_g=?, notes=? WHERE id=?",
            (name.strip(), kj, calories, protein_g, notes, component_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True


def get_component_daily_usage(component_id):
    """Get all daily log entries that directly use this component."""
    conn = get_db()
    rows = conn.execute("""
        SELECT dl.date, de.meal_time, de.quantity
        FROM daily_entries de
        JOIN daily_log dl ON de.daily_log_id = dl.id
        WHERE de.component_id = ?
        ORDER BY dl.date DESC
    """, (component_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_component_meal_usage(component_id):
    """Get all meals that include this component."""
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, m.name, mc.quantity
        FROM meal_components mc
        JOIN meals m ON mc.meal_id = m.id
        WHERE mc.component_id = ?
        ORDER BY m.name
    """, (component_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_component(component_id):
    conn = get_db()
    conn.execute("DELETE FROM components WHERE id = ?", (component_id,))
    conn.commit()
    conn.close()


# --- Meal helpers ---

def get_all_meals():
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, COUNT(de.id) as use_count
        FROM meals m
        LEFT JOIN daily_entries de ON de.meal_id = m.id
        GROUP BY m.id
        ORDER BY m.name
    """).fetchall()
    conn.close()
    result = []
    for row in rows:
        meal = dict(row)
        meal['components'] = get_meal_components(meal['id'])
        totals = calc_meal_totals(meal)
        meal['total_kj'] = totals['kj']
        meal['total_calories'] = totals['calories']
        meal['total_protein'] = totals['protein']
        result.append(meal)
    return result


def search_meals(query):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, COUNT(de.id) as use_count
        FROM meals m
        LEFT JOIN daily_entries de ON de.meal_id = m.id
        WHERE m.name LIKE ?
        GROUP BY m.id
        ORDER BY m.name
    """, (f'%{query}%',)).fetchall()
    conn.close()
    result = []
    for row in rows:
        meal = dict(row)
        meal['components'] = get_meal_components(meal['id'])
        totals = calc_meal_totals(meal)
        meal['total_kj'] = totals['kj']
        meal['total_calories'] = totals['calories']
        meal['total_protein'] = totals['protein']
        result.append(meal)
    return result


def get_meal(meal_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM meals WHERE id = ?", (meal_id,)).fetchone()
    conn.close()
    if row:
        meal = dict(row)
        meal['components'] = get_meal_components(meal_id)
        totals = calc_meal_totals(meal)
        meal['total_kj'] = totals['kj']
        meal['total_calories'] = totals['calories']
        meal['total_protein'] = totals['protein']
        return meal
    return None


def add_meal(name, kj_override=None, calories_override=None, protein_override=None, notes=''):
    kj_override, calories_override = fill_energy_nullable(kj_override, calories_override)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO meals (name, kj_override, calories_override, protein_override, notes) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), kj_override, calories_override, protein_override, notes)
        )
        conn.commit()
        meal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        conn.close()
        return None
    conn.close()
    return meal_id


def update_meal(meal_id, name, kj_override=None, calories_override=None, protein_override=None, notes=''):
    kj_override, calories_override = fill_energy_nullable(kj_override, calories_override)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE meals SET name=?, kj_override=?, calories_override=?, protein_override=?, notes=? WHERE id=?",
            (name.strip(), kj_override, calories_override, protein_override, notes, meal_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True


def get_meal_daily_usage(meal_id):
    """Get all daily log entries that use this meal."""
    conn = get_db()
    rows = conn.execute("""
        SELECT dl.date, de.meal_time, de.quantity
        FROM daily_entries de
        JOIN daily_log dl ON de.daily_log_id = dl.id
        WHERE de.meal_id = ?
        ORDER BY dl.date DESC
    """, (meal_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_meal(meal_id):
    conn = get_db()
    conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    conn.commit()
    conn.close()


# --- Meal component helpers ---

def get_meal_components(meal_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT mc.id, mc.quantity, c.id as component_id, c.name, c.kj, c.calories, c.protein_g
        FROM meal_components mc
        JOIN components c ON mc.component_id = c.id
        WHERE mc.meal_id = ?
        ORDER BY c.name
    """, (meal_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_meal_component(meal_id, component_id, quantity=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO meal_components (meal_id, component_id, quantity) VALUES (?, ?, ?)",
        (meal_id, component_id, quantity)
    )
    conn.commit()
    conn.close()


def update_meal_component(mc_id, quantity):
    conn = get_db()
    conn.execute("UPDATE meal_components SET quantity = ? WHERE id = ?", (quantity, mc_id))
    conn.commit()
    conn.close()


def remove_meal_component(mc_id):
    conn = get_db()
    conn.execute("DELETE FROM meal_components WHERE id = ?", (mc_id,))
    conn.commit()
    conn.close()


def save_meal_components(meal_id, components_list):
    """Replace all components for a meal. components_list: [(component_id, quantity), ...]"""
    conn = get_db()
    conn.execute("DELETE FROM meal_components WHERE meal_id = ?", (meal_id,))
    for comp_id, qty in components_list:
        conn.execute(
            "INSERT INTO meal_components (meal_id, component_id, quantity) VALUES (?, ?, ?)",
            (meal_id, comp_id, qty)
        )
    conn.commit()
    conn.close()


def calc_meal_totals(meal):
    """Calculate totals from components or overrides."""
    components = meal.get('components', [])
    if components:
        kj = sum(c['kj'] * c['quantity'] for c in components)
        cal = sum(c['calories'] * c['quantity'] for c in components)
        prot = sum(c['protein_g'] * c['quantity'] for c in components)
        return {'kj': round(kj, 1), 'calories': round(cal, 1), 'protein': round(prot, 1)}
    return {
        'kj': meal.get('kj_override') or 0,
        'calories': meal.get('calories_override') or 0,
        'protein': meal.get('protein_override') or 0,
    }


# --- Daily log helpers ---

def get_or_create_daily_log(date_str):
    conn = get_db()
    row = conn.execute("SELECT * FROM daily_log WHERE date = ?", (date_str,)).fetchone()
    if not row:
        conn.execute("INSERT INTO daily_log (date) VALUES (?)", (date_str,))
        conn.commit()
        row = conn.execute("SELECT * FROM daily_log WHERE date = ?", (date_str,)).fetchone()
    conn.close()
    return dict(row)


def get_daily_log(date_str):
    conn = get_db()
    row = conn.execute("SELECT * FROM daily_log WHERE date = ?", (date_str,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_daily_log(log_id, weight_morning=None, weight_night=None, exercise='', notes=''):
    conn = get_db()
    conn.execute(
        "UPDATE daily_log SET weight_morning=?, weight_night=?, exercise=?, notes=? WHERE id=?",
        (weight_morning, weight_night, exercise, notes, log_id)
    )
    conn.commit()
    conn.close()


def get_daily_logs_range(start_date, end_date):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM daily_log WHERE date BETWEEN ? AND ? ORDER BY date DESC",
        (start_date, end_date)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_daily_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM daily_log ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Daily entry helpers ---

def get_daily_entries(log_id):
    """Get all entries for a daily log with full nutritional info."""
    conn = get_db()
    rows = conn.execute("""
        SELECT de.id, de.quantity, de.meal_time, de.notes,
               de.meal_id, de.component_id,
               m.name as meal_name,
               c.name as component_name, c.kj as comp_kj, c.calories as comp_cal, c.protein_g as comp_protein
        FROM daily_entries de
        LEFT JOIN meals m ON de.meal_id = m.id
        LEFT JOIN components c ON de.component_id = c.id
        WHERE de.daily_log_id = ?
        ORDER BY de.meal_time, de.id
    """, (log_id,)).fetchall()
    conn.close()

    entries = []
    for r in rows:
        entry = dict(r)
        if entry['meal_id']:
            meal = get_meal(entry['meal_id'])
            if meal:
                entry['name'] = meal['name']
                entry['entry_kj'] = meal['total_kj'] * entry['quantity']
                entry['entry_cal'] = meal['total_calories'] * entry['quantity']
                entry['entry_protein'] = meal['total_protein'] * entry['quantity']
            else:
                entry['name'] = entry['meal_name'] or '(deleted meal)'
                entry['entry_kj'] = entry['entry_cal'] = entry['entry_protein'] = 0
        elif entry['component_id']:
            entry['name'] = entry['component_name'] or '(deleted component)'
            entry['entry_kj'] = (entry['comp_kj'] or 0) * entry['quantity']
            entry['entry_cal'] = (entry['comp_cal'] or 0) * entry['quantity']
            entry['entry_protein'] = (entry['comp_protein'] or 0) * entry['quantity']
        else:
            entry['name'] = entry['notes'] or '(unknown)'
            entry['entry_kj'] = entry['entry_cal'] = entry['entry_protein'] = 0
        entries.append(entry)
    return entries


def add_daily_entry(log_id, meal_id=None, component_id=None, quantity=1, meal_time='other', notes=''):
    conn = get_db()
    conn.execute(
        "INSERT INTO daily_entries (daily_log_id, meal_id, component_id, quantity, meal_time, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (log_id, meal_id, component_id, quantity, meal_time, notes)
    )
    conn.commit()
    conn.close()


def delete_daily_entry(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM daily_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def calc_daily_totals(log_id):
    entries = get_daily_entries(log_id)
    total_kj = sum(e['entry_kj'] for e in entries)
    total_cal = sum(e['entry_cal'] for e in entries)
    total_protein = sum(e['entry_protein'] for e in entries)
    return {
        'kj': round(total_kj, 1),
        'calories': round(total_cal, 1),
        'protein': round(total_protein, 1),
        'entry_count': len(entries),
    }


# --- Target helpers ---

def get_all_targets():
    conn = get_db()
    rows = conn.execute("SELECT * FROM targets ORDER BY daily_calories").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_target():
    conn = get_db()
    row = conn.execute("SELECT * FROM targets WHERE is_active = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def set_active_target(target_id):
    conn = get_db()
    conn.execute("UPDATE targets SET is_active = 0")
    conn.execute("UPDATE targets SET is_active = 1 WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()


def add_target(label, daily_calories, daily_kj, daily_protein_g):
    conn = get_db()
    conn.execute(
        "INSERT INTO targets (label, daily_calories, daily_kj, daily_protein_g) VALUES (?, ?, ?, ?)",
        (label, daily_calories, daily_kj, daily_protein_g)
    )
    conn.commit()
    conn.close()


def update_target(target_id, label, daily_calories, daily_kj, daily_protein_g):
    conn = get_db()
    conn.execute(
        "UPDATE targets SET label=?, daily_calories=?, daily_kj=?, daily_protein_g=? WHERE id=?",
        (label, daily_calories, daily_kj, daily_protein_g, target_id)
    )
    conn.commit()
    conn.close()


def delete_target(target_id):
    conn = get_db()
    conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()


def get_rank_tiers():
    """Build rank tiers from all targets relative to the active target.

    Targets stricter than active (lower cal) get S, SS, SSS (closest to active = S).
    Active target = A.  More lenient targets get B, C, D, E.
    Returns list sorted by daily_calories ascending, each dict has:
      label, rank, calories
    """
    targets = get_all_targets()  # already sorted by daily_calories asc
    active = get_active_target()
    if not targets or not active:
        return []

    active_cal = active['daily_calories']
    stricter = [t for t in targets if t['daily_calories'] < active_cal]
    more_lenient = [t for t in targets if t['daily_calories'] > active_cal]

    # Stricter ranks: closest to active = AA, next = AAA, then AAAA...
    tiers = []
    for i, t in enumerate(reversed(stricter)):
        rank = 'A' * (i + 2)  # AA, AAA, AAAA...
        tiers.insert(0, {'label': t['label'], 'rank': rank, 'calories': t['daily_calories']})

    # Active = A
    tiers.append({'label': active['label'], 'rank': 'A', 'calories': active_cal})

    # Lenient: B, C, D, E...
    lenient_labels = ['B', 'C', 'D', 'E']
    for i, t in enumerate(more_lenient):
        rank = lenient_labels[i] if i < len(lenient_labels) else chr(ord('B') + i)
        tiers.append({'label': t['label'], 'rank': rank, 'calories': t['daily_calories']})

    # F tier (over all targets)
    tiers.append({'label': 'Over all targets', 'rank': 'F', 'calories': None})

    return tiers


def calc_rank(calories, tiers):
    """Return the rank string for a calorie total given tier list.

    Walks tiers from strictest to most lenient; rank = strictest tier met.
    Returns None if calories is 0 (no entries) or tiers is empty.
    """
    if not tiers or not calories or calories <= 0:
        return None

    result = 'F'
    for tier in tiers:
        if tier['calories'] is not None and calories <= tier['calories']:
            result = tier['rank']
            break

    return result


# --- Quick Add helpers ---

def get_all_quick_adds(meal_time=None):
    conn = get_db()
    if meal_time:
        rows = conn.execute("""
            SELECT qa.*, m.name as meal_name, c.name as component_name
            FROM quick_add qa
            LEFT JOIN meals m ON qa.meal_id = m.id
            LEFT JOIN components c ON qa.component_id = c.id
            WHERE qa.meal_time = ?
            ORDER BY qa.sort_order, qa.label
        """, (meal_time,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT qa.*, m.name as meal_name, c.name as component_name
            FROM quick_add qa
            LEFT JOIN meals m ON qa.meal_id = m.id
            LEFT JOIN components c ON qa.component_id = c.id
            ORDER BY qa.meal_time, qa.sort_order, qa.label
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_quick_add(label, meal_id=None, component_id=None, meal_time='coffee', quantity=1):
    conn = get_db()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM quick_add WHERE meal_time = ?",
        (meal_time,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO quick_add (label, meal_id, component_id, meal_time, quantity, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
        (label.strip(), meal_id, component_id, meal_time, quantity, max_order)
    )
    conn.commit()
    conn.close()


def delete_quick_add(qa_id):
    conn = get_db()
    conn.execute("DELETE FROM quick_add WHERE id = ?", (qa_id,))
    conn.commit()
    conn.close()


def get_quick_add(qa_id):
    conn = get_db()
    row = conn.execute("""
        SELECT qa.*, m.name as meal_name, c.name as component_name
        FROM quick_add qa
        LEFT JOIN meals m ON qa.meal_id = m.id
        LEFT JOIN components c ON qa.component_id = c.id
        WHERE qa.id = ?
    """, (qa_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
