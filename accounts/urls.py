from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('cancel-appointment/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<int:appointment_id>/status/', views.update_appointment_status, name='update_appointment_status'),
    path('set-availability/', views.set_availability, name='set_availability'),
    path('prescriptions/create/', views.create_prescription,  name='create_prescription'),
    path('prescriptions/doctor/',views.doctor_prescriptions, name='doctor_prescriptions'),
    path('my-prescriptions/',views.patient_prescriptions,name='patient_prescriptions'),
    path('prescriptions/<int:prescription_id>/',views.prescription_detail,  name='prescription_detail'),
    path('medical-records/upload/', views.upload_medical_record, name='upload_medical_record'),
    path('medical-records/doctor/', views.doctor_medical_records, name='doctor_medical_records'),
    path('my-medical-records/', views.patient_medical_records, name='patient_medical_records'),
    path('medical-records/<int:record_id>/', views.medical_record_detail, name='medical_record_detail'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name          = 'accounts/password_reset/password_reset_form.html',
             email_template_name    = 'accounts/password_reset/password_reset_email.txt',
             subject_template_name  = 'accounts/password_reset/password_reset_subject.txt',
             success_url            = '/password-reset/done/',
         ),
         name='password_reset'),
 
    # Step 2: "Email has been sent" confirmation page
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name = 'accounts/password_reset/password_reset_done.html',
         ),
         name='password_reset_done'),
 
    # Step 3: User clicks link in email → enters new password
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name = 'accounts/password_reset/password_reset_confirm.html',
             success_url   = '/password-reset-complete/',
         ),
         name='password_reset_confirm'),
 
    # Step 4: "Password changed successfully" page
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name = 'accounts/password_reset/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]