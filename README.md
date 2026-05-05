# Barangay San Isidro, Surigao City, Surigao del Norte EventCore

Barangay San Isidro EventCore is a beginner-friendly Django database management system for planning, organizing, and monitoring community events in Barangay San Isidro, Surigao City, Surigao del Norte.

## Concept

Barangay San Isidro EventCore helps barangay officials and organizers manage events such as:

- Clean-up drive
- Feeding program
- Medical mission
- Sports tournament
- Barangay assembly
- Disaster preparedness seminar

## Main Users

- Admin
- Barangay Organizer
- Volunteer
- Resident / Participant

## Main Features

- User authentication with login, logout, and registration
- Forgot password / password reset using Django's built-in reset flow
- Role-based access control for admins, organizers, volunteers, and residents
- Create, view, update, and delete barangay events
- Search and filter events by keyword, event type, status, timeframe, and sort order
- Add people as admins, barangay organizers, volunteers, or residents
- Assign organizers to events
- Assign volunteers and update their attendance
- Register participants, enforce event capacity, and add overflow registrations to a waitlist
- Track participant and volunteer attendance
- Manage event resources such as supplies, equipment, food, medicine, and venue needs
- Track event budget, estimated resource costs, and actual resource costs
- Collect participant feedback and ratings
- View dashboard statistics, active events, and past events that still need status review
- Receive basic in-app notifications
- Use system validations and database constraints for dates, capacity, ratings, quantities, and costs

## Database Tables / Models

The `events/models.py` file defines these main tables:

- `users`
- `events`
- `event_organizers`
- `volunteers`
- `participants`
- `resources`
- `feedback`
- `notifications`

Barangay San Isidro EventCore also links its `users` table to Django's built-in authentication table so users can log in with a username and password.

## Setup Instructions

1. Install Django if needed:

   ```bash
   pip install -r requirements.txt
   ```

2. Create migrations:

   ```bash
   python manage.py makemigrations
   ```

3. Apply migrations and create the SQLite database:

   ```bash
   python manage.py migrate
   ```

4. Create an admin account:

   ```bash
   python manage.py createsuperuser
   ```

5. Run the development server:

   ```bash
   python manage.py runserver
   ```

6. Open the system in a browser:

   ```text
   http://127.0.0.1:8000/
   ```

7. Open the admin login:

   ```text
   http://127.0.0.1:8000/admin/
   ```

## Deployment Notes

The repository ignores generated build files such as `__pycache__`, `.pyc`, logs, and the local SQLite database. Commit the `.gitignore` and staged deletions so deployment platforms receive only source files.

Set these environment variables on your deployment platform:

- `SECRET_KEY`: a private Django secret key
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: your deploy domain, for example `your-app.onrender.com`

The root `Procfile` starts the app with Gunicorn:

```text
web: gunicorn EventCore.wsgi:application
```

## Beginner Presentation Guide

- Use the login/register pages to demonstrate user authentication.
- Use different roles to explain access control: admins manage people, organizers manage events, volunteers can help track attendance, and residents can register for events.
- Use the dashboard to demonstrate statistics for events, participants, waitlists, budgets, resources, feedback, and notifications.
- Use the events page to demonstrate search, filtering, timeframe views, and sorting.
- Open an event's **Manage** page to demonstrate organizer assignment, volunteer assignment, participant registration, attendance tracking, resource management, and feedback collection.
- Set a small event capacity, then register more residents to demonstrate the waitlist system.
- Use the **People** page to add organizers, volunteers, and residents before assigning them to an event.
- Use the admin page to demonstrate the complete database tables and show that the web forms are stored in SQLite.
- Explain that SQLite stores the project data in `db.sqlite3`.
- Explain that Django migrations create the database tables from `models.py`.
- Explain that attendance is tracked using the `attendance_status` fields in `volunteers` and `participants`.
- Explain that resource and budget tracking uses `budget`, `estimated_cost`, and `actual_cost` fields.

## Useful Pages

- Login: `http://127.0.0.1:8000/login/`
- Register: `http://127.0.0.1:8000/register/`
- Forgot password: `http://127.0.0.1:8000/forgot-password/`
- Dashboard: `http://127.0.0.1:8000/`
- Events: `http://127.0.0.1:8000/events/`
- People management: `http://127.0.0.1:8000/people/`
- Notifications: `http://127.0.0.1:8000/notifications/`
- Admin login: `http://127.0.0.1:8000/admin/`

## Forgot Password Demo

The project uses Django's console email backend for beginner-friendly local testing. When a user requests a password reset, the reset email and link are printed in the terminal where `python manage.py runserver` is running.
