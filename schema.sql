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