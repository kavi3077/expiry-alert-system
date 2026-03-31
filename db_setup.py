import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ---------------- USERS ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# ---------------- PRODUCTS ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    quantity INTEGER,
    price REAL,
    expiry_date TEXT,
    added_date TEXT,

    -- AI Features
    discount INTEGER,
    season_demand REAL,
    supplier_delay INTEGER,
    storage_temp INTEGER,
    product_age INTEGER,
    category INTEGER
)
""")

conn.commit()
conn.close()

print("✅ Database created with AI features!")