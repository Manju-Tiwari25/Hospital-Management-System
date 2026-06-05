#  Hospital Management System

A full-featured hospital management web application built with **Python Django**.
Supports two user roles  **Doctor** and **Patient**  with separate dashboards,
appointment booking with slot availability, and automated email notifications via Gmail SMTP.

---

##  Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Gmail SMTP Setup](#gmail-smtp-setup)
- [Running the Project](#running-the-project)
- [How to Use](#how-to-use)
- [URL Reference](#url-reference)
- [Database Models](#database-models)
- [Email Notifications](#email-notifications)
- [Screenshots Overview](#screenshots-overview)

---

##  Features

###  Authentication
- Separate registration for **Doctor** and **Patient**
- Role-based login  redirects to correct dashboard automatically
- Secure password hashing via Django's built-in `create_user()`
- Logout support

###  Doctor Features
- Personal dashboard with stats (today's appointments, total patients, upcoming)
- Set weekly availability (days + working hours)
- View and manage all appointments (confirm / complete / cancel)
- View full patient list with blood group, DOB, emergency contact
- Receive email notification when a patient cancels

###  Patient Features
- Personal dashboard with upcoming and past appointments
- Browse all available doctors
- Book appointments by selecting doctor → date → available time slot
- See real-time slot availability (🟢 Available / 🔴 Booked)
- Cancel upcoming appointments
- Receive email confirmation on booking, cancellation, and status updates

###  Email Notifications (Gmail SMTP)
- Welcome email on registration
- Appointment booking confirmation
- Cancellation email to both patient and doctor
- Status update email when doctor confirms or completes

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Django 6.x |
| Database | SQLite (development) |
| Frontend | HTML5, Bootstrap 5, JavaScript |
| Email | Gmail SMTP via Django `send_mail` |
| Environment | python-dotenv |
| Auth | Django built-in authentication |

---

##  Project Structure

```
hospital_project/
│
├── .env                        # Secret credentials (never commit)
├── .gitignore                  # Protects .env and venv
├── manage.py                   # Django management commands
├── requirements.txt            # All dependencies
│
├── hospital/                   # Project config folder
│   ├── settings.py             # Settings + SMTP config
│   ├── urls.py                 # Main URL routing
│   └── wsgi.py
│
└── accounts/                   # Main app
    ├── models.py               # UserProfile, DoctorProfile, PatientProfile,
    │                           # Appointment, DoctorAvailability
    ├── views.py                # All view functions + email logic
    ├── forms.py                # Registration forms
    ├── urls.py                 # App URL patterns
    ├── admin.py                # Admin panel registration
    └── templates/
        └── accounts/
            ├── base.html               # Master layout (navbar, Bootstrap)
            ├── register.html           # Doctor/Patient registration
            ├── login.html              # Login page
            ├── doctor_dashboard.html   # Doctor's dashboard
            ├── patient_dashboard.html  # Patient's dashboard
            ├── book_appointment.html   # Appointment booking page
            └── set_availability.html   # Doctor availability settings
```

---

##  Installation & Setup

### 1. Clone or download the project

```bash
git clone https://github.com/yourusername/hospital_project.git
cd hospital_project
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

```bash
# Windows:
venv\Scripts\activate

# Mac / Linux:
source venv/bin/activate
```

### 4. Install all dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist yet, install manually:

```bash
pip install django pillow python-dotenv
```

Then generate requirements.txt:

```bash
pip freeze > requirements.txt
```

### 5. Apply database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser (for Admin panel)

```bash
python manage.py createsuperuser
```

---

##  Environment Variables

Create a `.env` file in the project root (same folder as `manage.py`):

```
EMAIL_HOST_USER=youremail@gmail.com
EMAIL_HOST_PASSWORD=your16digitapppassword
```

>  Never commit `.env` to GitHub. It is already listed in `.gitignore`.

---

##  Gmail SMTP Setup

This project uses Gmail SMTP to send emails. Follow these steps:

**Step 1 — Enable 2-Step Verification**
```
Go to: https://myaccount.google.com/security
Enable: 2-Step Verification
```

**Step 2 — Generate App Password**
```
Go to: https://myaccount.google.com/apppasswords
App name: Django Hospital
Click: Create
Copy the 16-character password (no spaces)
```

**Step 3 — Add to .env**
```
EMAIL_HOST_USER=youremail@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

**Step 4 — Verify settings.py has these lines**

At the top of `hospital/settings.py`:
```python
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
```

At the bottom:
```python
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = f'Hospital App <{os.environ.get("EMAIL_HOST_USER")}>'
```

---

##  Running the Project

```bash
python manage.py runserver
```

Open your browser and visit:

```
http://127.0.0.1:8000/register/
```

---

##  How to Use

### Register as Doctor
```
1. Go to /register/
2. Select role → Doctor
3. Fill in: name, email, password, specialization, license number, experience
4. Click Register → redirected to login
5. Login → Doctor Dashboard
6. Click "Set Availability" → choose days and working hours
```

### Register as Patient
```
1. Go to /register/
2. Select role → Patient
3. Fill in: name, email, password, DOB, blood group, address, emergency contact
4. Click Register → redirected to login
5. Login → Patient Dashboard
```

### Book an Appointment (Patient)
```
1. Login as Patient
2. Click "Book Appointment"
3. Select a Doctor from dropdown
4. Choose a Date
5. Click "Check Available Slots"
6. Green slots (🟢) = available, Red slots (🔴) = already booked
7. Click a green slot to select it
8. Add reason (optional)
9. Click "Confirm Appointment"
10. Email confirmation sent automatically 
```

### Manage Appointments (Doctor)
```
1. Login as Doctor
2. Dashboard shows today's appointments
3. Change status using dropdown: Pending → Confirmed → Completed
4. Patient receives email notification on status change
5. "All My Patients" table shows complete patient list
```

---

##  URL Reference

| URL | View | Access |
|-----|------|--------|
| `/register/` | Register page | Public |
| `/login/` | Login page | Public |
| `/logout/` | Logout | Logged in |
| `/dashboard/doctor/` | Doctor dashboard | Doctor only |
| `/dashboard/patient/` | Patient dashboard | Patient only |
| `/book-appointment/` | Book appointment | Patient only |
| `/cancel-appointment/<id>/` | Cancel appointment | Patient only |
| `/appointment/<id>/status/` | Update status | Doctor only |
| `/set-availability/` | Set availability | Doctor only |
| `/admin/` | Django admin panel | Superuser only |

---

##  Database Models

### UserProfile
Extends Django's built-in User model with a role field.

| Field | Type | Description |
|-------|------|-------------|
| user | OneToOneField | Links to Django User |
| role | CharField | `doctor` or `patient` |
| phone | CharField | Optional phone number |


### DoctorProfile
| Field | Type | Description |
|-------|------|-------------|
| user_profile | OneToOneField | Links to UserProfile |
| specialization | CharField | e.g. Cardiology |
| license_number | CharField | Unique license ID |
| experience_years | IntegerField | Years of experience |
| bio | TextField | Doctor's description |

### PatientProfile
| Field | Type | Description |
|-------|------|-------------|
| user_profile | OneToOneField | Links to UserProfile |
| date_of_birth | DateField | Patient's DOB |
| blood_group | CharField | A+, B-, O+, etc. |
| address | TextField | Home address |
| emergency_contact | CharField | Emergency phone |

### DoctorAvailability
| Field | Type | Description |
|-------|------|-------------|
| doctor | ForeignKey | Links to DoctorProfile |
| day | CharField | Monday, Tuesday, etc. |
| start_hour | IntegerField | e.g. 9 (9:00 AM) |
| end_hour | IntegerField | e.g. 17 (5:00 PM) |

### Appointment
| Field | Type | Description |
|-------|------|-------------|
| patient | ForeignKey | Links to PatientProfile |
| doctor | ForeignKey | Links to DoctorProfile |
| date | DateField | Appointment date |
| hour | IntegerField | Hour slot (e.g. 10) |
| status | CharField | pending / confirmed / cancelled / completed |
| reason | TextField | Reason for visit |
| notes | TextField | Doctor's notes |
| created_at | DateTimeField | Auto timestamp |

---

##  Email Notifications

| Event | Who receives | Subject |
|-------|-------------|---------|
| Registration | New user | Welcome to Hospital App! |
| Appointment booked | Patient |  Appointment Booked Successfully! |
| Appointment cancelled | Patient + Doctor |  Appointment Cancelled |
| Status updated | Patient |  Appointment Confirmed/Completed |

---


##  Security Notes

- Passwords are hashed using Django's PBKDF2 algorithm
- CSRF protection enabled on all forms via `{% csrf_token %}`
- Role-based access control on every dashboard view
- `@login_required` decorator protects all authenticated pages
- Credentials stored in `.env` — never hardcoded
- `.env` excluded from version control via `.gitignore`

---


##  Built With

- [Django](https://www.djangoproject.com/) — Python web framework
- [Bootstrap 5](https://getbootstrap.com/) — Frontend styling
- [SQLite](https://www.sqlite.org/) — Development database
- [Gmail SMTP](https://support.google.com/mail/answer/7126229) — Email delivery
- [python-dotenv](https://pypi.org/project/python-dotenv/) — Environment variables

---

##  License

This project is built for learning purposes.
Feel free to use, modify, and extend it for your own projects.

---

