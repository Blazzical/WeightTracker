"""Seed initial data from the spreadsheet into the database."""

import models


def seed():
    """Initialize DB and seed default data if tables are empty."""
    models.init_db()

    conn = models.get_db()
    count = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    conn.close()
    if count > 0:
        seed_quick_adds()
        return  # Already seeded

    # --- Seed components from spreadsheet (columns L-O) ---
    components = [
        # (name, kj, calories, protein_g)
        ("Scrambled Egg", 377, 90, 6.0),
        ("Bread Slice", 377, 90, 0),
        ("Beans 300g", 910, 217, 14.4),
        ("Cheese Slice", 270, 65, 0),
        ("Milk 250mL", 674, 161, 8.5),
        ("Protein Scoop", 664, 159, 30.0),
        ("50g Strawberries", 53, 13, 0.3),
        ("50g Mixed Berries", 85, 20, 0),
        ("Peanut Butter (thick spread)", 1000, 239, 0),
        ("Honey (1 tbsp)", 200, 48, 0),
        ("Bread Roll", 969, 232, 0),
        ("Pocket Pasta 1/4", 1800, 430, 0),
        ("Bolognaise 1/4", 242, 58, 0),
        ("Shredded Cheese 25g", 300, 72, 0),
        ("15g Protein Yoghurt", 544, 130, 15.0),
        ("Cappuccino", 628, 150, 0),
        ("Lasagna", 1350, 323, 0),
        ("Blackberries 100g", 180, 43, 0),
        ("Greek Yoghurt 200g", 1000, 239, 8.4),
        ("Red Lentils uncooked 100g", 1381, 330, 0),
        ("Banana", 506, 121, 1.1),
        ("McD Cheeseburger", 1259, 301, 16.0),
        ("McD Chk Cheese", 1757, 420, 18.0),
        ("McD Sml Chips", 862, 206, 3.0),
        ("Dom Supreme Classic (slice)", 616, 147, 6.6),
        ("Dom Supreme Thin (slice)", 554, 132, 5.9),
        ("Dom Vegorama Thin (slice)", 442, 106, 4.5),
        ("Dom Smk BBQ Chk Classic (slice)", 509, 121, 5.9),
        ("Dom Smk BBQ Chk Thin (slice)", 433, 104, 4.9),
        ("Cheesy Crust (per slice)", 222, 53, 3.2),
        ("Milk 50mL", 135, 32, 1.7),
    ]
    for name, kj, cal, prot in components:
        models.add_component(name, kj, cal, prot)

    # --- Seed meals from spreadsheet (columns P-S) ---
    meals_data = [
        # (name, kj, cal, protein)
        ("1 Toast 3 Eggs 1 Cheese", 1778, 425, None),
        ("1 Toast Beans 300g 1 Cheese", 1557, 372, None),
        ("Protein Drink (half water) Strawberries", 1476, 353, 38.5),
        ("Coffee w/ 50mL Milk", 175, 42, 1.7),
        ("Protein Drink (half water) Banana", 1929, 461, 39.6),
        ("Protein Drink Banana", 2603, 622, 48.1),
        ("Peanut Butter + Honey Bread Roll", 2169, 518, None),
        ("Pocket Pasta Meal", 2342, 560, None),
        ("200g Greek Yoghurt, 60g Blackberries, Honey", 1380, 330, 8.4),
        ("McSmart Meal", 3878, 927, 37.0),
        ("Half Supreme Pizza Classic", 2464, 588, 26.4),
        ("Half Supreme Pizza Thin", 2216, 528, 23.6),
        ("Half Vegorama Pizza Thin", 1768, 424, 18.0),
        ("Half Smk BBQ Chk Pizza Classic", 2036, 484, 23.6),
        ("Half Smk BBQ Chk Pizza Thin", 1732, 416, 19.6),
        ("Half Smk BBQ Chk Pizza Cheesy", 2924, 696, 36.4),
    ]
    for name, kj, cal, prot in meals_data:
        models.add_meal(name, kj_override=kj, calories_override=cal, protein_override=prot)

    # --- Seed target presets from spreadsheet (column K) ---
    targets = [
        ("Maintain weight", 2454, 10272, 150),
        ("Lose 250g/week", 2204, 9226, 150),
        ("Lose 500g/week", 1954, 8179, 150),
        ("Lose 1kg/week", 1454, 6086, 150),
    ]
    for i, (label, cal, kj, prot) in enumerate(targets):
        models.add_target(label, cal, kj, prot)

    # Set "Lose 500g/week" as default active target
    models.set_active_target(3)

    # Seed default quick-add presets
    seed_quick_adds()


def seed_quick_adds():
    """Seed default quick-add items if table is empty."""
    conn = models.get_db()
    count = conn.execute("SELECT COUNT(*) FROM quick_add").fetchone()[0]
    conn.close()
    if count > 0:
        return

    # Find the "Coffee w/ 50mL Milk" meal
    conn = models.get_db()
    row = conn.execute("SELECT id FROM meals WHERE name = ?", ("Coffee w/ 50mL Milk",)).fetchone()
    conn.close()
    if row:
        models.add_quick_add("Coffee w/ Milk", meal_id=row[0], meal_time='coffee', quantity=1)
