-- Drop table so we can start fresh each time
-- This is useful while we're developing the app
DROP TABLE IF EXISTS users;

-- We might add an email later (and other things if needed)
-- user_id is the unique identifier (in case we allow usernames to 
-- change later) and it also auto increments 
CREATE TABLE users
(
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

DROP TABLE IF EXISTS fcm_tokens;

-- FCM tokens are stored in a separate table so that users
-- can have multiple tokens associated with them (in case 
-- they're logged in on multiple devices/browsers)
CREATE TABLE fcm_tokens (
    token_id INTEGER PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    token TEXT UNIQUE NOT NULL,
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS medications;

-- Medications are linked to users through their user_id
-- This allows flexible dosage and frequency 
-- The end_date is optional because some medications may
-- need to be taken forever
-- Users can opt in for reminders or not
CREATE TABLE medications (
    user_medication_id INTEGER PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    medication_name TEXT NOT NULL,
    dosage_amount REAL NOT NULL, 
    dosage_unit TEXT NOT NULL, -- e.g. mg, ml, tablet etc.
    frequency_count INT NOT NULL, -- e.g. 1/2/3/ times per day
    frequency_type TEXT NOT NULL, -- e.g. daily, weekly etc.
    start_date DATE NOT NULL,
    end_date DATE,
    instructions TEXT,
    reminders_enabled BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS medication_times;

-- I separated time_of_day into its own separate table
-- to make handling multiple times per day easier
CREATE TABLE medication_times (
    time_id INTEGER PRIMARY KEY,
    user_medication_id INT NOT NULL REFERENCES medications(user_medication_id),
    time_of_day TIME NOT NULL
);