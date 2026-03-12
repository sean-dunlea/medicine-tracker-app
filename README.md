# Medimate

## Setup Instructions

### Install Dependencies

Ensure you are in the project root directory and run `pip install -r requirements.txt`. This will install all required Python packages including Flask, Firebase Admin SDK, APScheduler, Flask-Mailman and python-dotenv.

### Firebase Cloud Messaging (FCM) Setup

This project uses Firebase Admin SDK to support push notifications. The service account key is not included in this repository for security reasons. 

To enable push notifications:
1. Create a new project in the [Firebase Console](https://console.firebase.google.com/).
2. Navigate to Project Settings > Service Accounts.
3. Click 'Generate New Private Key' and download the JSON file.
3. Place the file in the root directory of the project and rename it to 'serviceAccountKey.json'.

**Important:** This file is listed in `.gitignore` and must never be committed to GitHub as it contains private credentials for your Firebase project. If using your own Firebase project, you must also update the Firebase configuration and VAPID key in the JavaScript push notification files.

### Environment Variables

This project uses uses python-dotenv to store sensitive credentials in environment variables.

1. Copy the example environment file:
`cp .env.example .env`
2. Open .env and replace the placeholder values with your own credentials.
The .env file is excluded from version control via `.gitignore` to prevent sensitive data from being committed.

### Medication Autocomplete (DrugBank Dataset)

This project includes a smart medication entry system built using a preprocessed subset of the DrugBank database. Due to DrugBank's licensing terms, the dataset is not included in this repository.

To enable autocomplete functionality:
1. Download the DrugBank Dataset:
    1. Create an account [here](https://go.drugbank.com/).
    2. Request the DrugBank full database XML file.
    3. Place the file in the project root and rename it to `full_database.xml`
2. Initialise the Database Tables:
    1. Run `python initialise_drugbank_tables.py`or `python3 initialise_drugbank_tables.py`.
    2. This creates two tables: `drugbank_drugs` and `drugbank_products`.
3. Parse and Import DrugBank Data:
    1. Run `python parse_and_insert_drugbank_data.py` or `python3 parse_and_insert_drugbank_data.py`.
    2. This script extracts generic drug names, brand names, synonyms and mixtures, and inserts them into the local SQLite database.
4. Result
    1. Once completed, the medication autocomplete feature will be enabled.
    2. Without this dataset, the application will still run but autocomplete suggestions will not be available.

### Running the Application

Once dependencies are installed and configuration is complete, run the Flask application:
`python app.py` or `python3 app.py`