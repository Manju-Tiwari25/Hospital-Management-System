from django.urls import path
from . import api_views

urlpatterns = [

    # ── Auth ──────────────────────────────────────────────
    # POST   /api/register/        Register new user
    # POST   /api/login/           Login → get token
    # POST   /api/logout/          Delete token
    # GET    /api/profile/         Get logged-in user profile
    path('register/', api_views.api_register, name='api_register'),
    path('login/',    api_views.api_login,    name='api_login'),
    path('logout/',   api_views.api_logout,   name='api_logout'),
    path('profile/',  api_views.api_profile,  name='api_profile'),

    # ── Dashboard ─────────────────────────────────────────
    # GET    /api/dashboard/       Get summary stats
    path('dashboard/', api_views.api_dashboard, name='api_dashboard'),

    # ── Doctors ───────────────────────────────────────────
    # GET    /api/doctors/                     List all doctors
    # GET    /api/doctors/<id>/slots/?date=... Get available slots
    path('doctors/',
         api_views.api_doctor_list, name='api_doctor_list'),
    path('doctors/<int:doctor_id>/slots/',
         api_views.api_doctor_slots, name='api_doctor_slots'),

    # ── Appointments ──────────────────────────────────────
    # GET    /api/appointments/        List appointments
    # POST   /api/appointments/        Book appointment
    # GET    /api/appointments/<id>/   View single appointment
    # PATCH  /api/appointments/<id>/   Update status
    path('appointments/',
         api_views.api_appointments, name='api_appointments'),
    path('appointments/<int:appointment_id>/',
         api_views.api_appointment_detail, name='api_appointment_detail'),

    # ── Prescriptions ─────────────────────────────────────
    # GET    /api/prescriptions/        List all prescriptions
    # GET    /api/prescriptions/<id>/   View single prescription
    path('prescriptions/',
         api_views.api_prescriptions, name='api_prescriptions'),
    path('prescriptions/<int:prescription_id>/',
         api_views.api_prescription_detail, name='api_prescription_detail'),

    # ── Medical Records ───────────────────────────────────
    # GET    /api/medical-records/        List all medical records
    # GET    /api/medical-records/<id>/   View single record
    path('medical-records/',
         api_views.api_medical_records, name='api_medical_records'),
    path('medical-records/<int:record_id>/',
         api_views.api_medical_record_detail, name='api_medical_record_detail'),
]