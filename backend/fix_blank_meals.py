import sqlite3

DB = "smartmess.db"

meal_mapping = {
    "2026-10-07": {
        "Idli": "breakfast",
        "Sambar": "breakfast",
        "Chutney": "breakfast",
        "Rice": "lunch",
        "Potato Fry": "lunch",
        "Curd": "lunch",
        "Chapati": "dinner",
        "Vegetable Kurma": "dinner",
    },

    "2026-10-06": {
        "Pongal": "breakfast",
        "Sambar": "breakfast",
        "Chutney": "breakfast",
        "Jeera Rice": "lunch",
        "Dal": "lunch",
        "Carrot Poriyal": "lunch",
        "Curd": "lunch",
        "Dosa": "dinner",
    },

    "2026-10-05": {
        "Dosa": "breakfast",
        "Sambar": "breakfast",
        "Chutney": "breakfast",
        "Rice": "lunch",
        "Kara Kuzhambu": "lunch",
        "Beans Poriyal": "lunch",
        "Curd": "lunch",
        "Chapati": "dinner",
        "Chana Masala": "dinner",
    },

    "2026-10-04": {
        "Idli": "breakfast",
        "Sambar": "breakfast",
        "Chutney": "breakfast",
        "Lemon Rice": "lunch",
        "Vegetable Kurma": "lunch",
        "Curd": "lunch",
        "Parotta": "dinner",
        "Vegetable Salna": "dinner",
    },

    "2026-10-03": {
        "Poori": "breakfast",
        "Potato Masala": "breakfast",
        "Rice": "lunch",
        "Rasam": "lunch",
        "Cabbage Poriyal": "lunch",
        "Curd": "lunch",
        "Chapati": "dinner",
        "Dal": "dinner",
    },

    "2026-10-02": {
        "Pongal": "breakfast",
        "Vada": "breakfast",
        "Chutney": "breakfast",
        "Tomato Rice": "lunch",
        "Potato Fry": "lunch",
        "Curd": "lunch",
        "Dosa": "dinner",
        "Sambar": "dinner",
    },

    "2026-10-01": {
        "Idli": "breakfast",
        "Sambar": "breakfast",
        "Coconut Chutney": "breakfast",
        "Rice": "lunch",
        "Beans Poriyal": "lunch",
        "Curd": "lunch",
        "Chapati": "dinner",
        "Vegetable Kurma": "dinner",
    },
}


conn = sqlite3.connect(DB)
cur = conn.cursor()

updated = 0

for record_date, items in meal_mapping.items():

    for item_name, meal in items.items():

        cur.execute(
            """
            UPDATE daily_consumption
            SET meal = ?
            WHERE date = ?
              AND item_name = ?
              AND meal IS NULL
            """,
            (meal, record_date, item_name),
        )

        updated += cur.rowcount


conn.commit()

print()
print("BLANK MEAL REPAIR COMPLETE")
print("---------------------------")
print("Records updated:", updated)

print()
print("Remaining blank meals:")

cur.execute(
    """
    SELECT COUNT(*)
    FROM daily_consumption
    WHERE meal IS NULL
    """
)

remaining = cur.fetchone()[0]

print(remaining)

conn.close()
