from django.urls import path
from . import api_views

urlpatterns = [

    # ── Auth ──────────────────────────────────────────────
    path('register/', api_views.api_register, name='api_register'),
    path('login/',    api_views.api_login,    name='api_login'),
    path('logout/',   api_views.api_logout,   name='api_logout'),
    path('profile/',  api_views.api_profile,  name='api_profile'),

    # ── Health Check ──────────────────────────────────────
    path('health/',   api_views.health_check, name='health_check'),

    # ── Dashboard ─────────────────────────────────────────
    path('dashboard/', api_views.api_dashboard, name='api_dashboard'),

    # ── Doctors ───────────────────────────────────────────
    path('doctors/',
         api_views.api_doctor_list, name='api_doctor_list'),
    path('doctors/<int:doctor_id>/slots/',
         api_views.api_doctor_slots, name='api_doctor_slots'),

    # ── Appointments ──────────────────────────────────────
    path('appointments/',
         api_views.api_appointments, name='api_appointments'),
    path('appointments/<int:appointment_id>/',
         api_views.api_appointment_detail, name='api_appointment_detail'),

    # ── Prescriptions ─────────────────────────────────────
    path('prescriptions/',
         api_views.api_prescriptions, name='api_prescriptions'),
    path('prescriptions/<int:prescription_id>/',
         api_views.api_prescription_detail, name='api_prescription_detail'),

    # ── Medical Records ───────────────────────────────────
    path('medical-records/',
         api_views.api_medical_records, name='api_medical_records'),
    path('medical-records/<int:record_id>/',
         api_views.api_medical_record_detail, name='api_medical_record_detail'),
]