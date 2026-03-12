import sqlite3
import xml.etree.ElementTree as ET

DATABASE = "app.db"
XML_FILE = "full_database.xml"

# Connect to our DB
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Parse the XML
tree = ET.parse(XML_FILE)
root = tree.getroot()
ns = {"db": "http://www.drugbank.ca"}  # DrugBank XML namespace

# Loop over each drug in the XML
for drug in root.findall("db:drug", ns):
    # --- Generic name ---
    drug_id_el = drug.find("db:drugbank-id[@primary='true']", ns)
    if drug_id_el is None:
        continue  # skip drugs without primary ID
    drug_id = drug_id_el.text

    generic_name_el = drug.find("db:name", ns)
    generic_name = generic_name_el.text if generic_name_el is not None else None

    if generic_name:
        cursor.execute("INSERT OR IGNORE INTO drugbank_drugs (drug_id, generic_name) VALUES (?, ?)",
                       (drug_id, generic_name))

    # --- Synonyms ---
    for syn in drug.findall("db:synonyms/db:synonym", ns):
        name = syn.text
        if name:
            cursor.execute("INSERT OR IGNORE INTO drugbank_products (drug_id, name, type) VALUES (?, ?, ?)",
                           (drug_id, name, "synonym"))

    # --- Products ---
    for prod in drug.findall("db:products/db:product", ns):
        name_el = prod.find("db:name", ns)
        if name_el is not None and name_el.text:
            cursor.execute("INSERT OR IGNORE INTO drugbank_products (drug_id, name, type) VALUES (?, ?, ?)",
                           (drug_id, name_el.text, "brand"))

    # --- Mixtures ---
    for mix in drug.findall("db:mixtures/db:mixture", ns):
        name_el = mix.find("db:name", ns)
        if name_el is not None and name_el.text:
            cursor.execute("INSERT OR IGNORE INTO drugbank_products (drug_id, name, type) VALUES (?, ?, ?)",
                           (drug_id, name_el.text, "mixture"))

# Commit and close
conn.commit()
conn.close()
print("DrugBank XML parsed successfully")