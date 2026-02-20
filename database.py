from flask import g
import os
import sqlite3
from datetime import date, datetime

sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda d: d.isoformat())
sqlite3.register_converter("DATE", lambda s: date.fromisoformat(s.decode()))
sqlite3.register_converter("TIMESTAMP", lambda s: datetime.fromisoformat(s.decode()))

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "app.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# This initialises the DrugBank database
def initialise_drugbank():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    # This checks if the main DrugBank table already exists
    cursor.execute("""
                   SELECT name 
                   FROM sqlite_master 
                   WHERE type="table" AND name="drugbank_drugs";
                   """)
    table_exists = cursor.fetchone()
    if table_exists:
        print("DrugBank tables already exist - skipping initialisation.")
        db.close()
        return
    # This only runs if the table does not already exist
    print("Initialising DrugBank tables...")
    with open("drugbank.sql", "r") as f:
        cursor.executescript(f.read())
    db.commit()
    db.close()
    print("DrugBank initialisation complete.")