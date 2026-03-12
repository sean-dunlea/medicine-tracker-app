import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "app.db")

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# This table stores generic drug names. It will used as a fall back
# in case there's no brand or synonym matches.
cursor.execute("DROP TABLE IF EXISTS drugbank_drugs;")
cursor.execute("""
               CREATE TABLE IF NOT EXISTS drugbank_drugs (
                    drug_id TEXT PRIMARY KEY,
                    generic_name TEXT
               );
               """)

# This table stores user-friendly names (brands, synonyms, mixtures).
cursor.execute("DROP TABLE IF EXISTS drugbank_products;")
cursor.execute("""
               CREATE TABLE IF NOT EXISTS drugbank_products (
                    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drug_id TEXT,
                    name TEXT,
                    type TEXT,
                    FOREIGN KEY(drug_id) REFERENCES drugbank_drugs(drug_id)
                    );
               """)

# This creates an index on idx_product_name for faster lookup speeds.
cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON drugbank_products(name)")

conn.commit()
conn.close()
print("Tables created successfully")