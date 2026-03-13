# CS3305: Team 14 Report

## MediMate

**By Mark Vaughan (123446326), Sean Dunlea (122353906), Tracy Lazarus (123388563) and Amina Baig (123482946)**

[GitHub Repository](https://github.com/sean-dunlea/medicine-tracker-app)

## Academic Integrity Declaration
We declare that this report and the project work are our own original work. All sources used in the development of this project have been acknowledged.

\newpage 

## Table of Contents
1. [Introduction](#introduction) 
    - [Problem & Competitors](#problem_and_competitors)
    - [Our Solution](#our_solution)
2. [Workflow](#workflow)
3. [System Architecture](#system_architecture)
    - [High-Level System Architecture](#high_level_system_architecture)
    - [System Data Flow](#system_data_flow)
    - [Database Schema](#database_schema)
4. [Features](#features)
    - [User Authentication & Management](#user_authentication_and_management)
    - [Dashboard & User Analytics](#dashboard_and_user_analytics)
    - [Medication Management](#medication_management)
    - [MediMates Management](#medimates_management)
    - [Symptom Logging](#symptom_logging)
    - [Notification System](#notification_system)
    - [Background Scheduler](#background_scheduler)
    - [AI-Powered Summaries](#ai_powered_summaries)
    - [User Interface & Experience](#user_interface_and_experience)
5. [Roles & Responsibilities](#roles_and_responsibilities)
    - [Mark Vaughan](#mark_vaughan)
    - [Sean Dunlea](#sean_dunlea)
    - [Tracy Lazarus](#tracy_lazarus)
    - [Amina Baig](#amina_baig)
7. [Table of Contributions](#table_of_contributions)
8. [Challenges & Lessons Learned](#challenges_and_lessons_learned)
9. [Areas for Improvement](#areas_for_improvement)
10. [Conclusion](#conclusion)
11. [Use of Generative AI](#use_of_generative_ai)
12. [References](#references)

\newpage

## 1. Introduction <a id="introduction"></a>
### Problem & Competitors <a id="problem_and_competitors"></a>
Have you ever worried about whether you or someone close to you has taken their medication on time? Medication adherence is a very common challenge in healthcare, especially for the elderly, people with illnesses, or simply those who just tend to forget. Missing medications or taking it at the wrong time can negatively impact one's overall health.

While a number of solutions already exist in helping this matter, many medication trackers simply focus on basic reminder functionality. Applications such as **MyTherapy**, **MediSafe**, and **CareClinic** allow users to set reminders and track medication schedules, but they fail to include strong social accountability features or deeper insights into a user's behaviour over time. Additionally, many of these are designed primarily for mobile applications, with very limited web-based alternatives.

As a result, users struggle with maintaining a good habit of keeping track of their medications. This also creates a sense of anxiety for those who care for elderly parents, relatives, or loved ones, as they may worry about whether medication routines are actually being followed correctly.

### Our Solution <a id="our_solution"></a>
To combat this issue, we present MediMate - a medication tracker web application which is designed to help users manage their medications more effectively.

A web-based platform was chosen not only because there are limited web-based solutions available, but also because it allows the app to be accessed from any device with a browser, without having to install additional software. Since our target audience includes elderly users, this approach makes it slightly more accessible for both patients and their caretakers.

The application allows users to schedule their medications, log their taken doses, and monitor adherence through a personalised dashboard. The dashboard includes a weekly colour-coded status, a progress chart displaying adherence over time, statistics for streak, total adherence percentage, and total active medications. We also provide a weekly AI generated summary of their medication activity. This allows users to keep on top of their routine and better understand their habits.

The key feature of our system is the 'MediMates' functionality - A feature allowing users to share their progress with trusted friends, families, or caretakers. These MediMates can view the user's medication activity, and send reminders if a dose has not been logged. The aim of this feature is to create a sense of support for the user, and motivating them to stay consistent. The system also includes automated reminders through push notification and email alerts to help users remember scheduled doses. If the user misses a dose after the scheduled time, an alert will be sent to the medimate, allowing them to provide encouragement or reminders.

Our app goes a step further by providing users a space to log the symptoms they've experienced . They are given the option to print or download a compilation of their symptoms as a report, along with a report of their current medications to share with their doctor.

The overall goal of our app is to help the user manage their medication well and provide reassurance for the people responsible for their care.

## 2. Workflow <a id="workflow"></a>

After our group had been created we set up a meeting as early as possible to get to know each other and begin brainstorming ideas for what we could build for our software project. We came up with a few ideas before we voted on MediMate to be our project. 

We discussed how we could build upon a medicine tracker app before deciding that a helpful feature that had not been worked upon would be to split the responsibility of remembering to take your medication among others. We talked about how we could implement this with a notification system.

Once we had a solid idea of how to go about creating the project, we divided the work between us. We made the decision to split up the work through each persons personal preference and their skills.

Before starting the development process, we created a shared google docs to write down all the tasks we had to complete. 

Each week we would have a mandatory meeting in person, and additionally online meetings to ensure work was getting done and to bring up problems team members might have been facing in order to solve them faster and not have one team member stuck on a bug for too long.

For the time between where the team would have meetings we created a Whatsapp groupchat as a way to ask and answer quick questions we had on others work or to make requests of other members that had arose.

Toward the end of the development process the code was tested with different ways we thought may cause an error in order for us to find bugs and fix them before the project had to be presented.

To prepare for the presentation we had a meeting to see what were the most important parts to present. We each took parts that related to our work and decided the best order to put the slides in to make it as linear as we could. We practiced the presentation multiple times in order to get more familiar with our parts and to deliver a presentation that flowed well.

## 3. System Architecture <a id="system_architecture"></a>

### High-Level System Architecture <a id="high_level_system_architecture"></a>

![High-Level System Architecture Diagram](images/high_level_system_architecture_diagram.png)

As outlined in the High-Level System Architecture Diagram, our MediMate system uses a layered web application architecture, consisting of a user interface, a backend application server and a persistent database.

The frontend provides an intuitive interface through which users can perform core actions such as adding medication, logging symptoms, managing MediMates and receiving reminders. User requests are transmitted to the backend via `HTTP`.

The backend processes user actions through a set of specialised modules, namely, the MediMates module which manages social connections between users, the reminder engine which schedules medication reminders to be delivered through email or push notifications, the smart medication entry system which facilitates the efficient lookup of medications, the AI module which analyses user symptoms and medication intake to produce health summaries, and the streak calculator which tracks users' adherence streaks.

The database layer stores all of our system's persistent data, including user information, medications, symptom logs, notifications, friends, invites and a local DrugBank database that supports autocomplete functionality. Each backend component interacts with the database, as required, ensuring all modules operate on consistent and up to date information.

This layered approach enhances modularity, resulting in a more maintainable and scalable system.

### System Data Flow <a id="system_data_flow"></a>

![System Data Flow Diagram](images/system_data_flow_diagram.png)

This diagram illustrates the primary data flows between users, the backend application modules, the database layer and the notification infrastrcture within our MediMate system.

The medication management component processes user requests related to medications. When adding, deleting or scheduling medications, entries in `medications`, `medication_logs` and `medication_times` are updated accordingly. Additionally, a preprocessed subsection of the DrugBank dataset, stored locally, enables users to search for medications quickly.

The authentication component controls user authentication and session management, supporting user registration, login, logout, as well as session tracking. Interactions within this module are limited primarily to the users table to validate credentials and maintain user sessions.

AI-powered summaries provide user health reports, utilising aggregated data from `medication_logs` and `symptoms`. These insights are stored in `users` to be presented subsequently.

The symptoms component allows users to log and view health observations. Records are stored in `symptoms`, and later retrieved for analytical purposes.

Users may update account information through the profile and preferences component, which provides centralised control over email updates, privacy configurations and additional user data. These changes are reflected in the database to ensure user preferences are respected across the system.

The MediMates component captures social connections between accounts. Users can send, accept or reject mate requests, as well as remove existing connections. Relationships are represented in `friends` and `invites`, determining whether users can view each other's medication activity and symptom logs.

Notifications are handled through a dedicated module, which calculates unread messages and manages user-facing alerts. Triggered at scheduled medication times, or perhaps due to MediMate actions, the system generates appropriate alerts to be delivered through our notification infrastructure.

The notification infrastrucutre utilises external services to deliver reliable messages to users. Firebase Cloud Message (FCM) delivers push notifications, while Gmail's SMTP server handles email notifications. Stored FCM tokens and notification preferences ensure dependable and consistent delivery.

Each backend component interacts with the database layer, which functions as the central repository for our application's data. This ensures all features operate on the latest data.

### Database Schema <a id="database_schema"></a>

![Database Schema Diagram](images/database_schema_diagram.png)

As demonstrated in the Database Schema Diagram, our application utilises a relational database to store all persistent data.

`users` stores the primary account information, including username, email, password, profile picture and additional user preferences. `allow_mates_activity` provides data privacy autonomy, allowing users to limit the visibility of personal information from medimates. `medication`, `symptoms`, `notifications` and `fcm_tokens` reference `users` through foreign keys, making it a primary driver for all user-related data in our system.

`medications` reserves information of medications registered by users. Each entry contains the medication name, dosage information, frequency and duration. A single entry belongs to a specific user and serves as the central reference point for related data, including reminder schedules, medication logs and notifications. 

`medication_times` defines the medication intake schedule for each user. Entries specify timestamps and recurrence patterns for medications, allowing our system to support various scheduling configurations (e.g daily/weekly/monthly).

When a user confirms medication intake, the event is stored in `medication_logs`. Each entry contains the scheduled date, the time of confirmation and the corresponding medication reference. These records provide the historical data required for adherence tracking, streak calculations and weekly health summaries.

`medication_reminders_sent` and `overdue_notifications_sent` record sent notifications, preventing duplicate alerts by ensuring that reminders are delivered only once per scheduled event.

`medimate_reminders_sent` stores reminders generated by the MediMates component, when friends prompt each other to stay consistent with their medication routines. This data is then used to implement safeguards, ensuring users are not spammed with messages. 

All notifications are stored in `notifications`, for display in our in-app notification centre. Each entry records the message title, content, read status and timestamp.

Our system supports push notifications through Firebase Cloud Messaging (FCM). FCM tokens are required to send push notifications, which are stored in `fcm_tokens`. Each token is associated with a specific user, allowing the notification infrastructure to deliver alerts directly to their registered devices.

Symptom tracking functionality is implemented through `symptoms`. Each entry documents user-reported symptoms, including severity, time of occurence and optional notes. These records are then analysed for inclusion in our AI-powered health summaries.

To support social accountability features, our system includes tables for managing relations between users. `invites` records pending friend requests, while `friends` stores established connections bewteen users. These relationships aid in determining the visibility of user activity within our application.

Finally, a preprocessed local copy of the DrugBank dataset supports efficient medication lookup. `drugbank_drugs` and `drugbank_products` store medication names and associated product information, allowing the system to provide fast autocomplete search suggestions as users add new medications.

These tables form a relational schema that supports the core functionality of MediMate, including medication scheduling, adherence tracking, symptom logging, social accountability features and notification delivery. Through the separation of responsibilities across specialised tables while linking them through foreign key relationships, our schema achieves flexibility and consistency for system evolution.

## 4. Features <a id="features"></a>

### User Authentication & Management <a id="user_authentication_and_management"></a>
Our system provides secure user registration and login with username or email and password. Emails are authenticated before registration, ensuring only valid addresses are accepted. The application maintains user sessions through a "Remember Me" option, allowing users to stay logged in across several browser sessions.

**Registration Interface**
![Registration Interface](images/registration_interface.jpg)

**Login Interface**
![Login Interface](images/login_interface.jpg)

### Dashboard & User Analytics <a id="dashboard_and_user_analytics"></a>

The dashboard provides a central overview of recent user activity, with key insights into their medication routine. Users can quickly view upcoming medication events and adherence analytics, including streak tracking for consecutive days where medications were taken as scheduled. These streaks aim to encourage consistency and reinforce positive self-care habits. By visualising adherence patterns and recent activity through the dashboard, users can quickly assess how well they are maintaining their medication schedule.

**Dashboard & User Analytics Interface (1/2)**
![Dashboard & User Analytics Interface (1:2)](images/dashboard.jpg)

**Dashboard & User Analytics Interface (2/2)**
![Dashboard & User  Analytics Interface (2:2)](images/dashboard2.jpg)

### Medication Management <a id="medication_management"></a>
Users can add and log medications with customisable schedules, including daily, weekly, monthly or as-needed reminders. Our system supports specifying dosage, timing and duration for each medication, as well as dynamic field adjustments based on the selected frequency type. A smart medication entry system, powered by the DrugBank database, provides autocomplete suggestions with generic names, brand names and synonyms for reliable searching. Validation logic prevents erroneous entries. The calendar provides an intuitive interface through which users can view scheduled medications in upcoming months. Users may also view past and current medications, with the ability to print or save this information for quick reference.

**Add Medication Form (1/4)**
![Add Medication Form (1:4)](images/add_medication_form1.jpg)

**Add Medication Form (2/4)**
![Add Medication Form (2:4)](images/add_medication_form2.jpg)

**Add Medication Form (3/4)**
![Add Medication Form (3:4)](images/add_medication_form3.jpg)

**Add Medication Form (4/4)**
![Add Medication Form (4:4)](images/add_medication_form4.jpg)

**Calendar Interface**
![Calendar Interface](images/calendar_interface.jpg)

**Medication Management Interface (1/2)**
![Medication Management Interface (1:2)](images/medication_management_interface1.jpg)

**Medication Management Interface (2/2)**
![Medication Management Interface (2:2)](images/medication_management_interface2.jpg)

### MediMate Management with Privacy Controls <a id="medimate_management_with_privacy_controls"></a>
This is the key feature that distinguishes our application from similar medication trackers. Users may add other users as MediMates to provide support and accountability. If user settings permit, MediMates may view each other's medications, logged symptoms and receive notification if a dosage is missed, allowing for gentle re-reminders. Users can manage their MediMates list, adding or removing friends as needed to maintain a supportive network.

**MediMates Interface**
![MediMates Interface](images/medimates_interface.jpg)

**MediMate's Activity Interface**
![MediMate's Activity Interface](images/medimates_activity_interface.jpg)

**Privacy Control Settings**
![Privacy Control Settings](images/privacy_control_settings.jpg)

### Symptom Logging <a id="symptom_logging"></a>
Users can log symptoms they experience alongside their medications. The symptom logging system allows users to track patterns overtime and provides input for generating personalised AI health summaries. Logged symptoms are stored securely and can be viewed and managed through the user dashboard.

**Symptom Log Interface**
![Symptom Log Interface](images/log_symptom_interface.jpg)

### Notification System <a id="notification_system"></a>
Our system implements multiple notification channels, ensuring users never miss their medications. Browser push notifications are delivered via Firebase Cloud Messaging, and email reminders are sent through the integrated email system. Users can also view all notifications through our in-application notification centre, and if a medication is missed by one hour, their designated MediMates are notified to provide a gentle reminder.

**Friend Request Notification**
![Friend Request Notification](images/friend_request_notification.jpg)

**Medication Reminder**
![Medication Reminder](images/medication_reminder.jpg)

**Notification Centre Interface**
![Notification Centre Interface](images/notification_centre_interface.jpg)

**Overdue Alert**
![Overdue Alert](images/overdue_alert.jpg)

### Background Scheduler <a id="background_scheduler"></a>
The background scheduler triggers reminders at the precise time for each user at their local timezone. The scheduler checks all medication schedules with minute-level precision to ensure reliable alerts. It also detects overdue medications and automatically sends MediMate reminders, as needed.

### AI-Powered Summaries <a id="ai_powered_summaries"></a>
Our system generates personalised health summaries based on logged medications and symptoms. The AI provides friendly and encouraging messages for users who follow their medication schedule and gentle reminders for missed doses. Data privacy is ensured, as no personally identifiable information is included in the summaries.

**AI Summary Output**
![AI Summary Output](images/summary_output.jpg)

### User Profile & Settings <a id="user_profile_and_settings"></a>

The system provides users with a dedicated profile and setting section where they can manage personal information. Users can change the email or password associated with their account, enhancing user agency. They can also opt-in for push notification reminders, or control the visibility of their activity to MediMates.

**User Settings Interface (1/2)**
![User Settings Interface (1:2)](images/user_settings_interface1.jpg)

**User Settings Interface (2/2)**
![User Settings Interface (2:2)](images/user_settings_interface2.jpg)

### User Interface & Experience <a id="user_interface_and_experience"></a>
The application offers a responsive ninterface with intuitive navigation across pages. Notifications and reminders are supported across multiple devices, enhancing accessibility and convenience.

## 5. Roles & Responsibilities <a id="roles_and_responsibilities"></a>

### Mark Vaughan (123446326) <a id="mark_vaughan"></a>

My primary focus was to work on the backend logic of the app and specifically on the friend system called **"medimates"**. This was done through the use the use of the following technologies: **HTML, Jinja, Python(Flask) and SQL**. 

The main section I worked on was the Medimates section. This section o the app handles all the features to do with the friend system that the app uses. This required a form to take the name of a user, check if they exist or are not yourself and send them a friend request. Friend relationships would be stored in a table with a reversed duplicate entry maikng it easy to gather friend data for use without gathering duplicates of relationships. Two sub sections were made for the medimate section, one showing the pending requests that a user had sent to other users and the other being incoming requests from other users.

I worked on the privacy feature for users accounts. I added a column in the user table that stored if users allowed for the privacy settings in the profile page. I then worked across existing parts of the app to implement checks to enforce privacy if the user has cosen to share information with medimates or not. I made modifications to the notification functions in order to make them adhere to the privacy settings. If they allow for info to be shared their medimates will recieve reminders if they have not taken their medication. Otherwise the scheduler ignores the 


Merged pages that were originally separate. I took the originally separate profile and settings page and merged them into a single flask route that feels more connected and simple. 



### Sean Dunlea - Backend and Systems Developer <a id="sean_dunlea"></a>

As a backend and systems developer, my primary responsibility was building the backend server architecture. This involved implementing several advanced features for our application such as the authentication and user management system, medication recording and scheduling functionality, the push and email notification infrastructure, an in-application notification centre, the background reminder scheduler, a smart medication autocomplete system and AI-powered health summaries. These features required careful co-ordination of multiple technologies, including Flask, SQLite, JavaScript, Firebase Cloud Messaging (FCM), as well as external APIs.

One of the first components I developed was the authentication and user management infrastructure. I implemented secure registration and login functionality using Flask, WTForms and session-based authentication. Passwords are hashed using `Werkzeug`, and I took further security measures by providing generic login error messages to mitigate user enumeration attacks. The registration process includes validated email addresses, ensuring authentication sessions are managed reliably across the application.

Next, I worked on building our notification infrastructure. After researching several options, I decided to integrate FCM to support browser push notifications, as relying solely on email notifications may result in missed reminders. Implementing this system required developing both frontend and backend components. On the frontend, I wrote JavaScript to request user notification permissions, register service workers, retrieve FCM tokens and synchronise those tokens with the backend server. On the backend, I developed routes and helper functions to send notifications to all devices associated with a specific user, while automatically removing invalid or expired tokens. This ensures notifications remain reliable, even when users access the application from mulitple different browsers or devices. In addition to push notifications, I implemented an email notification system by creating a dedicated Gmail account and integrating it with `Flask-Mailman` and `Gmail SMTP`. This ensures that users still receive medication reminders even if push notifications are unavailable or disabled. I also developed an in-application notification centre, allowing users to view their notifications directly within the user interface.

After this, I worked on designing and implementing the database structure and backend logic needed for reliable medication management. This required developing an efficient schema that supports user-specific medications, configurable medication schedules and multiple intake times per day. I created functionality that allows users to add medications with various scheduling patterns, including daily, weekly, monthly and as needed frequencies. I also wrote JavaScript to support dynamic form input, allowing users to specify dosage, duration and multiple daily intake times. To ensure data consistency, I implemented validation logic that ensures only valid medication schedules may be submitted.

I implemented a background scheduling system using `APScheduler` to support medication reminders. This is a Python library designed for scheduling code execution at specificed times or intervals. The scheduler runs periodically and checks medication schedules at minute-level precision, determining whether reminders should be sent or not. One challenge I faced during this process was ensuring that reminders get delivered at the correct time for users in different time zones. To address this, I implemented JavaScript that detects the user's timezone in the browser and transmits this data to the backend. Here, it is stored in `users` and retrieved for calculating reminder times. The scheduler converts the user's local timezone before triggering notifications. I also designed database mechanisms to prevent duplicate reminders and implemented logic to detect overdue medications. If a medication is not recorded as taken within one hour of the scheduled time, the system automatically notifies the user's designated medimates and allows them to send additional reminder notifications.

To enhance user experience, I developed a smart medication entry system, allowing users to search for and find medications efficiently. Initially, after doing some research, I explored the RxNorm dataset. However, I found its structure unsuitable for the intended purpose as it separated medications into extremely granular variations (e.g. distinguishing between base drug names and specific dosage forms) and relied on US-centric naming conventions. I researched alternative resources and contacted DrugBank to request API access. DrugBank is a "trusted intelligence operating system built on the most comprehensive biomedical knowledge base". Although the API was not available for academic use, I was granted access to their full database dataset. As the dataset was very large (approximately 2GB), I implemented a preprocessing pipeline to extract only the relevant medication name information required for autocomplete functionality. I then created a separate database schema and integration logic so that the dataset could be automatically initialised without other team members having to manually manage the large source file. This allows our application to provide intuitive autocomplete suggestions while keeping the repository manageable.

Finally, I implemented the AI-generated health summary feature. I explored several possible solutions before choosing OpenRouter as the most suitable API choice for our project. Some of my earlier approaches using OpenAI and Hugging Face came with limitiations in cost and storage size to store large local models. Using OpenRouter allows our application to generate summaries dynamically without requiring large local resources. I designed prompts that summarise medication adherence and symptom logs in a supportive tone. The summaries encourage users when medications are taken as scheduled, gently highlight missed doses and provide general feedback on recorded symptoms, while avoiding any diagnostic language. To protect user privacy, the data provided to this API is anonymised, and contains no personal identifiable information such as usernames or email addresses. To improve performance and minimise API calls, I implemented caching logic that stores the generated summary and only regenerates it when relevant user data changes, for example, when a new symptom is logged or if a new medication event occurs.

Overall, my role focused on backend development, notification infrastructure, system architecture and the integration of advanced features that support the functionality of our Medimate application. Through my work, I gained a lot of experience designing and integrating full stack systems, especially in co-ordinating backend logic, client-side functionality and third party services in a reliable, maintainable and scalable manner.

### Tracy Lazarus - Full-Stack Feature Developer <a id="tracy_lazarus"></a>
My primary responsibility was to create features that users would interact with across both the frontend and backend. This involved displaying the features on the interface using HTML and Jinja templates, and doing the backend logic with Python(Flask). I integrated database operations to complete features of the system. In total, the features I worked on required technologies such as Flask, HTML, Jinja templates, JavaScript, and SQL.

The first feature I worked on was improving the authentication that was already built. I developed a 'Remember Me' feature that optionally allows users to remain signed in. This required linking the frontend form inputs with the backend session management so that the app will correctly store and retrieve the authentication state. I also built a Logout route which allows the user to end the session. 

Next, I made a symptom logging page. I developed a form that allows users to record symptoms they experienced which includes input fields like symptom name, severity, date, time, and optional notes. When submitted, these symptoms will display in a section called Symptom History. For this, I had to create a symptoms table in the schema. These symptoms are displayed in chronological order. To make this feature more useful, I added in a print option which allows the user to download or print a compilation of their symptoms as a PDF report that can be shared with their doctor.

The main feature I worked on was the dashboard. It provides the user with visual insights of their medication progress. Here, I implemented a seven-day calendar view which shows whether doses were taken, missed, or not scheduled yet. This was the most challenging as designing this required calculating the current week and mapping each medication schedule to the currrent day. It had to also account for different medication frequency patterns which required additional logic. In the dashboard, I also implemented an adherence streak counter, a monthly adherence progress line chart which I had to use JavaScript for, dashboard statistics which includes the user's current adherence percentage and the number of active medications. This provides better insight into medication habits.

To allow the users to interact with the system, I made a Log Medications page where users can mark medications as taken. They can only do this for previous and current days but not for the future. The logging system then updates the calendar view in the dashboard automatically.

In addition to the weekly tracking system, I created a full monthly view of the calendar which serves the same purpose of showing logged medication status but over longer periods. I put in a slider here so that the user can go back and forth between months to view the history of the full year.

Finally I worked on the profile and settings section of the app. The section allows users to view their account information such as the number of Medimates they have, and they can select a profile avatar. In settings, I added a functionality to allow users to change their email address and password, as well as update their privacy settings that allow users to pick whether they want their mates to see their activity or not.

Overall, my role focused on making the core user-facing features and ensuring the frontend, backend, and database worked together.

### Amina Baig - Frontend & UI Developer <a id="amina_baig"></a>
As the Frontend and UI Developer, my role involved designing the complete visual interface of MediMate. This involved using CSS, JavaScript and restructuring existing HTML and Jinja templates to ensure they work well with the styling and layout of the application. As a team, we decided to assign one member to focus mainly on the visual design of the system as this allowed the interface to remain visually consistent, while allowing the other team members to dedicate more time to developing the backend features. My work focused on improving overall usability, consistency, and improving the visual structure of the app so that the features could be easily understood by users.


Firstly, I created a prototype design of what I wanted the app to look like using <e.g Figma>. This allowed the team to visualise the structure and layout of the application before starting development.

I selected the theme colours of the app to be red and yellow. These colours were chosen because according to <insert research>, warm colours such as red and yellow have been shown to attract attention and support memory retention, which is relevant to MediMate where users are trying to keep track of their doses.
    
Following the protoype, I implemented the visual interface using CSS and restructuring HTML to work with the styling. As this app's target audience includes elderly people, I made sure to make the design as clear and consistent as possible.
    
Overall, my role focused on ensuring MediMate remained well-structured, user-friendly, and visually appealing which contributes to the overall user experience of the system.




## 6. Table of Contributions <a id="table_of_contributions"></a>


| Name  | Contribution |
|:-----:|:-------------|
| Mark  | **Medimates:**</br>- Created the medimates page</br>- Created the database schema to allow the join of two users through a duplicate relationship entry for each friendship </br>- Made multiple forms to handle all medimate actions.</br>- </br></br>**Privacy Settings**</br>-   |
| Sean  | **Project Setup and Infrastructure:**</br>- Created the initial Flask project structure and repository</br>- Set up the application environment and dependency management</br>- Helped manage the shared GitHub repository and resolve integration issues during development</br></br>**Authentication and User Management**</br>- Implemented secure user registration and login using Flask, WTForms and session authentication</br> - Implemented password hashing using Werkzeug</br>- Added email functionality and validation</br>- Implemented security improvements such as generic login error messages to prevent user enumeration</br></br>**Database Design and Backend Architecture:**</br> - Designed database schemas for users, medications, medication schedules, notification tracking and related tables</br>- Implemented backend logic for medication management and user-specific medication schedules</br>- Developed support for multiple medication intake times and configurable schedule frequencies (daily, weekly, monthly and as-needed)</br></br>**Medication Autocomplete System:**</br>- Researched medication datasets, including RxNorm and DrugBank</br>- Integrated a medication autcomplete system to improve user experience when adding medications</br>- Parsed and preprocessed the DrugBank dataset to extract relevant medication names</br>- Designed a database schema and initialisation logic so the dataset could be used without requiring manual setup by teammates</br></br>**Notification Infrastructure:**</br>- Researched and implemented push notifications using Firebase Cloud Messaging (FCM)</br>- Developed client-side JavaScript to request notification permissions, register service workers and synchronise device tokens</br>- Implemented backend logic to send push notifications and manage multiple tokens per user device</br>- Added automatic cleanup of invalid or expired tokens</br></br>**Reminder Scheduling System:**</br>- Implemented a background medication reminder scheduler using `APScheduler`</br>- Designed scheduling logic that checks medication schedules every minute and triggers reminders with minute-level precision</br>- Implemented timezone detection and conversion to ensure reminders occur at the correct local time for each user</br>- Built logic to detect overdue medications and notify Medimares when a medication is missed</br></br>**Email Notification System:**</br>- Implemented email notification functionality using `Flask-Mailman` and `Gmail SMTP`</br>- Created a dedicated email account for the application</br>- Integrated email reminders alongside push notifications to ensure reliable reminder delivery</br></br>**Notification Centre:**</br>- Implemented a notification centre where users can view and manage their notifications</br>- Implemented logic to store and retrieve notifications from the database</br></br>**AI Integration:**</br>- Implemented AI-generated health summaries using the OpenRouter API</br>- Designed prompts that summarise medication adherence and symptom logs in a supportive manner</br>- Ensured anonymised data was sent to the AI service to protect user privacy</br>- Implemented caching logic to reduce unnecessary API calls and improve application performance</br></br>**Debugging and Integration:**</br>- Debugged backend, database and frontend integration issues throughout development</br>- Ensured features remained stable when integrating new components |
| Tracy | </br>**Authentication:** </br> - Implemented a Logout route </br>- Created a 'Remember Me' option allowing users to stay signed in</br></br>**Symptom Logging System:**</br>- Made a form allowing users to log the symptoms they experienced </br> - Created a Symptom History section in the same page that displays all added symptoms</br> - Designed database schema for symptoms</br> - Implemented a Share Report option which allows the user to download or print the symptoms history as PDF</br></br>**Medication Management:**</br> - Added a history page of added medications called 'My Medications' which retrieves and displays added medications</br>- Created a Delete Medication option in My Medications which removes the added medication from the database </br></br>**Medication Tracking Dashboard:**</br> - Developed a colour-coded 7-day calendar view for scheduled medication to show the days where medications that were taken, not taken, and not scheduled</br> - Added a functionality to mark doses as taken and store logs in the database</br> - Implemented a streak counter for consecutive days of successful medication intake</br> - Developed monthly adherence progress chart, using JavaScript</br> - Added dashboard statistics which includes current adherence percentage and total active medications</br></br>**Calendar:** </br> - Created a full view monthly calendar which shows the status of whether medications were taken or not each day</br>- Added a slider to navigate between all of the months in the year</br></br> **Profile and Settings**</br> - Implemented a profile section showing account information such as number of mates and the ability to choose a profile picture</br> - Included an option to change email and password</br> - Added privacy settings which controls whether mates can view your activity</br></br>|
| Amina | - All Concept and Design of App</br>- All CSS and JavaScript</br>- Rewriting Jinja Templates/app.py to work with the styling|


## 7. Challenges & Lessons Learned <a id="challenges_and_lessons_learned"></a>

### Version Control <a id="version_control"></a>
The biggest problem we faced during the development of the project was using Git. As multiple team members were working on the same repository at the same time, merge conflicts occurred occasionally when changes were made to the same sections of code. At the beginning, it was tough as we all did not have much experience using Git in a collaborative space. Sometimes, when trying to solve a merge conflict, code would end up being removed accidentally. 

However, as time went on, we learned to review the code carefully to ensure no functionality was lost and we made sure to communicate to each other in the group chat or directly to the person who was in charge of that specific part of the code about what had happened.

### Allocating Work <a id="allocating_work"></a>
As the project started progressing and the number of features increased, it sometimes became unclear which tasks should be prioritised and who should be responsible for completing them. After we completed the main development tasks, there were still some smaller features and fixes. Without a clear allocation, there was a risk that some tasks would've been forgotton or multiple people would have worked on the same task unnecessarily.

To fix this problem, we used a shared task list on Google Docs containing all the remaining project tasks. We organised this checklist inspired by the **MoSCoW** method, where we categorised each task based on their importance. The tasks highlighted in green represented the must-do tasks that were essential for the application and the ones in orange represented the should-do or could-do tasks that could be completed if we had time left. We had a column beside each task where our team members could assign their names. This helped prevent working on the same code simultaneously.

### Time Management <a id="time_management"></a>
Another challenge we faced was arranging times for the team to meet. Although we met every Wednesday, we needed additional discussions to make decisions about the project. However, as team members had different schedules and academic commitments (in our case working on another team project), finding suitable times was slightly difficult.

To overcome this issue, we decided to schedule meetings online in advance a few times if we were unavailable to meet in person.

## 8. Areas for Improvement <a id="areas_for_improvement"></a>
Although MediMate successfully demonstrates the core features we thought were required, we had several more ideas that could have improved the app if we had more time. 

One important area is accessibility. Since the application is designed to support elderly users, additional features for accessibility such as a voice-over support, larger text mode or a dark/light theme toggle could have assisted users who may have visual impairements or difficulty navigating interfaces.

Another potential idea we had would be the addition of an in-built messaging feature between MediMates. This would allow caretakers or trusted mates to communicate directly within the application and send reminders or encouragement when the user's medications have not been logged. These messages could also trigger optional email notifications.


## 9. Conclusion <a id="conclusion"></a>
From a technical perspective, this project shows how multiple components can come together to make a cohesive system. The application combines a Flask-based backend, a relational database, a frontend interface, background scheduling for reminders, and services such as Firebase Cloud Messaging and AI APIs.

Beyond the technical aspect, the project provided us as a team, valuable experience in software development. We learned how to communicate effectively, manage version control, coordinate work, and organise tasks effectively.

Overall, MediMate shows how a software solution can help support healthier habits.

## 10. Use of Generative AI <a id="use_of_generative_ai"></a>
Generative AI tools such as ChatGPT were used during the development process for debugging purposes, when all team members did not know the issue. All final code, comments, and report were written and reviewed by the team.

## 11. References <a id="reference"></a>

### Competitors <a id="competitors"></a>
**MyTherapy** https://www.mytherapyapp.com/

**MediSafe** https://www.medisafe.com/

**CareClinic** https://careclinic.io/