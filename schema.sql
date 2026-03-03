-- Drop table so we can start fresh each time
-- This is useful while we're developing the app
DROP TABLE IF EXISTS users;

-- We might add an email later (and other things if needed)
-- user_id is the unique identifier (in case we allow usernames to 
-- change later) and it also auto increments 
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    profile_picture TEXT DEFAULT "avatar1.png",
    allow_mates_activity BOOLEAN DEFAULT 1,
    timezone TEXT, -- Stored here to send push notifications at user's local time
    weekly_summary TEXT,
    weekly_summary_outdated BOOLEAN DEFAULT 1
);

DROP TABLE IF EXISTS fcm_tokens;

-- FCM tokens are stored in a separate table so that users can have multiple tokens associated with them (in case 
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
-- The end_date is optional because some medications may need to be taken forever
-- Users can opt in for reminders or not
CREATE TABLE medications (
    user_medication_id INTEGER PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    medication_name TEXT NOT NULL,
    dosage_amount REAL NOT NULL,
    dosage_unit TEXT NOT NULL, -- e.g. mg, ml, tablet etc.
    frequency_count INT NOT NULL, -- e.g. 1/2/3/ times
    frequency_type TEXT NOT NULL, -- e.g. daily, weekly etc.
    start_date DATE NOT NULL,
    end_date DATE,
    instructions TEXT,
    push_notifications_enabled BOOLEAN NOT NULL DEFAULT 0,
    email_notifications_enabled BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS medication_times;

CREATE TABLE medication_times (
    time_id INTEGER PRIMARY KEY,
    user_medication_id INT NOT NULL REFERENCES medications(user_medication_id),
    time_of_day TIME NOT NULL,
    weekday INTEGER, -- 0 is Monday, 6 is Sunday
    day_of_month INTEGER
);

-- I added this table to make avoiding duplicate messages easier
DROP TABLE IF EXISTS medication_reminders_sent;

CREATE TABLE medication_reminders_sent (
    id INTEGER PRIMARY KEY,
    user_medication_id INTEGER NOT NULL,
    time_of_day TEXT NOT NULL,
    date_sent DATE NOT NULL,
    UNIQUE(user_medication_id, time_of_day, date_sent) -- This ensures a reminder is only sent once per medication per time per day
);

-- This tracks each time a user takes their medication
DROP TABLE IF EXISTS medication_logs;

CREATE TABLE medication_logs (
    medication_log_id INTEGER PRIMARY KEY,
    user_medication_id INTEGER NOT NULL REFERENCES medications(user_medication_id),
    -- This links the log to a specific medication plan
    scheduled_date DATE NOT NULL,
    time_of_day TEXT NOT NULL,
    datetime_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- This stores when the user marks a medication as taken
);

-- This stores notifications
DROP TABLE IF EXISTS notifications;

CREATE TABLE notifications (
    notification_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL, -- This is the receiver of the notification
    user_medication_id INTEGER,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    is_read INTEGER DEFAULT 0, -- 0 means unread, 1 means read
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (user_medication_id) REFERENCES medications(user_medication_id)
);

-- This keeps track is an overdue notification was sent to avoid spamming a user's
-- MediMate every minute
DROP TABLE IF EXISTS overdue_notifications_sent;

CREATE TABLE overdue_notifications_sent (
    id INTEGER PRIMARY KEY,
    user_medication_id INTEGER,
    scheduled_date DATE,
    FOREIGN KEY (user_medication_id) REFERENCES medications(user_medication_id),
    UNIQUE(user_medication_id, scheduled_date)
);

-- This table keeps track of re-reminders sent to avoid a MediMate spamming
-- another user
DROP TABLE IF EXISTS medimate_reminders_sent;

CREATE TABLE medimate_reminders_sent (
    id INTEGER PRIMARY KEY,
    user_medication_id INTEGER,
    reminded_by TEXT,
    scheduled_date DATE,
    FOREIGN KEY (user_medication_id) REFERENCES medications(user_medication_id),
    UNIQUE(user_medication_id, reminded_by, scheduled_date)
);

DROP TABLE IF EXISTS invites;

-- Table to differentiate the sender and receiver of invites
CREATE TABLE invites (
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL
);

DROP TABLE IF EXISTS friends;

CREATE TABLE friends (
    friend1 TEXT NOT NULL,
    friend2 TEXT NOT NULL
);

DROP TABLE IF EXISTS symptoms;

CREATE TABLE symptoms (
    symptom_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symptom_name TEXT NOT NULL,
    severity INTEGER NOT NULL,
    symptom_date DATE NOT NULL,
    symptom_time TIME,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

DROP TABLE IF EXISTS drugbank_drugs;
DROP TABLE IF EXISTS drugbank_products;

SELECT *
FROM users