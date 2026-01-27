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
    medication_id INTEGER PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    medication_name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    time_of_day TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    instructions TEXT,
    reminders_enabled INTEGER DEFAULT 0,
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);