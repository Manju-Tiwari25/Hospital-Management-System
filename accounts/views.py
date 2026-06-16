import re
import uuid
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, DoctorRegistrationForm, PatientRegistrationForm
from .models import UserProfile, DoctorProfile, PatientProfile, Appointment, DoctorAvailability, Prescription, PrescriptionItem, MedicalRecord
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.core.mail import send_mail
from django.conf import settings


# ─────────────────────────────────────────
#  HELPER — Generate unique username
# ─────────────────────────────────────────
def generate_username(first_name, last_name, email):
    """
    Generates a unique username automatically.
    Strategy: firstname + lastname + random 4 digits
    Example: john_smith_4821
    Falls back to email prefix if name is empty.
    """
    first = re.sub(r'[^a-zA-Z0-9]', '', first_name).lower()
    last  = re.sub(r'[^a-zA-Z0-9]', '', last_name).lower()

    if first and last:
        base = f"{first}_{last}"
    elif first:
        base = first
    else:
        base = email.split('@')[0].lower()
        base = re.sub(r'[^a-zA-Z0-9]', '', base)

    username = f"{base}_{str(uuid.uuid4().int)[:4]}"

    while User.objects.filter(username=username).exists():
        username = f"{base}_{str(uuid.uuid4().int)[:4]}"

    return username


# ─────────────────────────────────────────
#  REGISTER VIEW
# ─────────────────────────────────────────
def register_view(request):
    user_form    = UserRegistrationForm()
    doctor_form  = DoctorRegistrationForm()
    patient_form = PatientRegistrationForm()

    if request.method == 'POST':
        role         = request.POST.get('role', 'patient')
        user_form    = UserRegistrationForm(request.POST)
        doctor_form  = DoctorRegistrationForm(request.POST)
        patient_form = PatientRegistrationForm(request.POST)

        user_form_valid = user_form.is_valid()

        if role == 'doctor':
            role_form_valid = doctor_form.is_valid()
        else:
            role_form_valid = patient_form.is_valid()

        if user_form_valid and role_form_valid:
            first_name = user_form.cleaned_data['first_name']
            last_name  = user_form.cleaned_data['last_name']
            email      = user_form.cleaned_data['email']
            phone      = user_form.cleaned_data.get('phone', '')
            password   = user_form.cleaned_data['password1']

            username = generate_username(first_name, last_name, email)

            user = User.objects.create_user(
                username   = username,
                first_name = first_name,
                last_name  = last_name,
                email      = email,
                password   = password,
            )

            profile = UserProfile.objects.create(
                user  = user,
                role  = role,
                phone = phone,
            )

            if role == 'doctor':
                DoctorProfile.objects.create(
                    user_profile     = profile,
                    specialization   = doctor_form.cleaned_data['specialization'],
                    license_number   = doctor_form.cleaned_data['license_number'],
                    experience_years = doctor_form.cleaned_data.get('experience_years', 0),
                    bio              = doctor_form.cleaned_data.get('bio', ''),
                )
            else:
                PatientProfile.objects.create(
                    user_profile      = profile,
                    date_of_birth     = patient_form.cleaned_data.get('date_of_birth'),
                    blood_group       = patient_form.cleaned_data.get('blood_group', ''),
                    address           = patient_form.cleaned_data.get('address', ''),
                    emergency_contact = patient_form.cleaned_data.get('emergency_contact', ''),
                )

            try:
                send_mail(
                    subject='Welcome to Hospital App — Your Login Details',
                    message=f'''
Hi {user.get_full_name()},

Your account has been created successfully!

Your Login Details:
  Email    : {email}
  Username : {username}
  Role     : {role.capitalize()}

{"You can now set your availability and manage patient appointments." if role == "doctor" else "You can now search for doctors and book appointments."}

Login here: http://127.0.0.1:8000/login/

- Hospital App Team
                    ''',
                    from_email     = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [email],
                    fail_silently  = False,
                )
            except Exception as e:
                print(f"Welcome email error: {e}")

            messages.success(
                request,
                f'✅ Account created! Your username is: {username} — Check your email for login details.'
            )
            return redirect('login')

    return render(request, 'accounts/register.html', {
        'user_form'   : user_form,
        'doctor_form' : doctor_form,
        'patient_form': patient_form,
    })


# ─────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('login_input', '').strip()
        password    = request.POST.get('password', '')

        # Try login with username first
        user = authenticate(request, username=login_input, password=password)

        # If that fails, try finding user by email
        if user is None:
            try:
                user_obj = User.objects.get(email=login_input.lower())
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None

        if user:
            login(request, user)
            if user.profile.role == 'doctor':
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(
                request,
                'Invalid email/username or password. Please try again.'
            )

    return render(request, 'accounts/login.html')


# ─────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
#  DOCTOR DASHBOARD
# ─────────────────────────────────────────
@login_required
def doctor_dashboard(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor = request.user.profile.doctor
    today  = timezone.now().date()

    today_appointments = Appointment.objects.filter(
        doctor=doctor, date=today
    ).exclude(status='cancelled')

    all_appointments = Appointment.objects.filter(
        doctor=doctor
    ).exclude(status='cancelled')

    patient_ids    = all_appointments.values_list('patient', flat=True).distinct()
    total_patients = patient_ids.count()

    upcoming = Appointment.objects.filter(
        doctor=doctor, date__gte=today, status='pending'
    ).order_by('date', 'hour')[:5]

    patient_list = PatientProfile.objects.filter(id__in=patient_ids)

    # Medical records count for stats card
    records_count = MedicalRecord.objects.filter(doctor=doctor).count()

    return render(request, 'accounts/doctor_dashboard.html', {
        'doctor'             : doctor,
        'today_appointments' : today_appointments,
        'total_patients'     : total_patients,
        'upcoming'           : upcoming,
        'patients_list'      : patient_list,
        'today'              : today,
        'records_count'      : records_count,
    })


# ─────────────────────────────────────────
#  PATIENT DASHBOARD
# ─────────────────────────────────────────
@login_required
def patient_dashboard(request):
    if request.user.profile.role != 'patient':
        return redirect('doctor_dashboard')

    patient = request.user.profile.patient
    today   = timezone.now().date()

    upcoming = Appointment.objects.filter(
        patient=patient, date__gte=today
    ).exclude(status='cancelled').order_by('date', 'hour')

    past = Appointment.objects.filter(
        patient=patient, date__lt=today
    ).order_by('-date', '-hour')[:5]

    all_doctors        = DoctorProfile.objects.all()
    prescription_count = Prescription.objects.filter(patient=patient).count()

    # Medical records count for stats card
    records_count = MedicalRecord.objects.filter(patient=patient).count()

    return render(request, 'accounts/patient_dashboard.html', {
        'patient'            : patient,
        'upcoming'           : upcoming,
        'past'               : past,
        'all_doctors'        : all_doctors,
        'today'              : today,
        'prescription_count' : prescription_count,
        'records_count'      : records_count,
    })


# ─────────────────────────────────────────
#  BOOK APPOINTMENT
# ─────────────────────────────────────────
@login_required
def book_appointment(request):
    if request.user.profile.role != 'patient':
        return redirect('doctor_dashboard')

    patient     = request.user.profile.patient
    all_doctors = DoctorProfile.objects.all()
    today       = timezone.now().date()

    selected_doctor = None
    available_slots = []
    selected_date   = None

    if request.method == 'GET' and request.GET.get('doctor_id'):
        doctor_id       = request.GET.get('doctor_id')
        selected_date   = request.GET.get('date', str(today))
        selected_doctor = get_object_or_404(DoctorProfile, id=doctor_id)

        try:
            date_obj = datetime.date.fromisoformat(selected_date)
        except ValueError:
            date_obj = today

        day_name = date_obj.strftime('%A')

        try:
            availability = DoctorAvailability.objects.get(
                doctor=selected_doctor, day=day_name
            )
            booked_hours = list(
                Appointment.objects.filter(
                    doctor=selected_doctor, date=date_obj
                ).exclude(status='cancelled').values_list('hour', flat=True)
            )
            for hour in range(availability.start_hour, availability.end_hour):
                available_slots.append({
                    'hour'   : hour,
                    'display': f"{hour}:00 {'AM' if hour < 12 else 'PM'}",
                    'booked' : hour in booked_hours,
                })
        except DoctorAvailability.DoesNotExist:
            available_slots = []

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        date_str  = request.POST.get('date')
        hour      = request.POST.get('hour')
        reason    = request.POST.get('reason', '')

        doctor = get_object_or_404(DoctorProfile, id=doctor_id)

        try:
            date_obj = datetime.date.fromisoformat(date_str)
            hour_int = int(hour)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date or hour.')
            return redirect('book_appointment')

        if Appointment.objects.filter(
            doctor=doctor, date=date_obj, hour=hour_int
        ).exclude(status='cancelled').exists():
            messages.error(request, '❌ This slot is already booked. Please choose another.')
            return redirect(f'/book-appointment/?doctor_id={doctor_id}&date={date_str}')

        appointment = Appointment.objects.create(
            patient = patient,
            doctor  = doctor,
            date    = date_obj,
            hour    = hour_int,
            reason  = reason,
            status  = 'pending',
        )

        try:
            send_mail(
                subject='✅ Appointment Booked Successfully!',
                message=f'''
Hi {patient.user_profile.user.get_full_name()},

Your appointment has been booked!

Doctor        : Dr. {doctor.user_profile.user.get_full_name()}
Specialization: {doctor.specialization}
Date          : {date_obj}
Time          : {appointment.get_time_display()}
Reason        : {reason or "Not specified"}
Status        : Pending

Please arrive 10 minutes before your appointment time.

- Hospital App Team
                ''',
                from_email     = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [patient.user_profile.user.email],
                fail_silently  = False,
            )
        except Exception as e:
            print(f"Booking email error: {e}")

        messages.success(request, f'✅ Appointment booked with Dr. {doctor.user_profile.user.get_full_name()} on {date_obj} at {hour_int}:00!')
        return redirect('patient_dashboard')

    return render(request, 'accounts/book_appointment.html', {
        'all_doctors'    : all_doctors,
        'selected_doctor': selected_doctor,
        'available_slots': available_slots,
        'selected_date'  : selected_date or str(today),
        'today'          : str(today),
    })


# ─────────────────────────────────────────
#  CANCEL APPOINTMENT
# ─────────────────────────────────────────
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.patient != request.user.profile.patient:
        messages.error(request, 'Not allowed.')
        return redirect('patient_dashboard')

    appointment.status = 'cancelled'
    appointment.save()

    try:
        patient_user = appointment.patient.user_profile.user
        doctor_user  = appointment.doctor.user_profile.user

        send_mail(
            subject='❌ Appointment Cancelled',
            message=f'''
Hi {patient_user.get_full_name()},

Your appointment has been cancelled.

Doctor : Dr. {doctor_user.get_full_name()}
Date   : {appointment.date}
Time   : {appointment.get_time_display()}

Book a new appointment: http://127.0.0.1:8000/book-appointment/

- Hospital App Team
            ''',
            from_email     = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [patient_user.email],
            fail_silently  = False,
        )

        send_mail(
            subject='❌ Appointment Cancelled by Patient',
            message=f'''
Hi Dr. {doctor_user.get_full_name()},

An appointment was cancelled by the patient.

Patient : {patient_user.get_full_name()}
Date    : {appointment.date}
Time    : {appointment.get_time_display()}

- Hospital App Team
            ''',
            from_email     = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [doctor_user.email],
            fail_silently  = False,
        )
    except Exception as e:
        print(f"Cancellation email error: {e}")

    messages.success(request, 'Appointment cancelled.')
    return redirect('patient_dashboard')


# ─────────────────────────────────────────
#  UPDATE APPOINTMENT STATUS
# ─────────────────────────────────────────
@login_required
def update_appointment_status(request, appointment_id):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['confirmed', 'cancelled', 'completed']:
            appointment.status = new_status
            appointment.notes  = request.POST.get('notes', appointment.notes)
            appointment.save()

            try:
                patient_user = appointment.patient.user_profile.user
                send_mail(
                    subject=f'📋 Appointment {new_status.capitalize()}',
                    message=f'''
Hi {patient_user.get_full_name()},

Your appointment status has been updated.

Doctor : Dr. {appointment.doctor.user_profile.user.get_full_name()}
Date   : {appointment.date}
Time   : {appointment.get_time_display()}
Status : {new_status.upper()}

{"Please arrive 10 minutes before your appointment time." if new_status == "confirmed" else ""}

- Hospital App Team
                    ''',
                    from_email     = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [patient_user.email],
                    fail_silently  = False,
                )
            except Exception as e:
                print(f"Status update email error: {e}")

            messages.success(request, f'Appointment marked as {new_status}.')

    return redirect('doctor_dashboard')


# ─────────────────────────────────────────
#  SET AVAILABILITY
# ─────────────────────────────────────────
@login_required
def set_availability(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor         = request.user.profile.doctor
    availabilities = DoctorAvailability.objects.filter(doctor=doctor)

    if request.method == 'POST':
        days       = request.POST.getlist('days')
        start_hour = int(request.POST.get('start_hour', 9))
        end_hour   = int(request.POST.get('end_hour', 17))

        DoctorAvailability.objects.filter(doctor=doctor).delete()
        for day in days:
            DoctorAvailability.objects.create(
                doctor=doctor, day=day,
                start_hour=start_hour, end_hour=end_hour
            )
        messages.success(request, '✅ Availability updated!')
        return redirect('doctor_dashboard')

    return render(request, 'accounts/set_availability.html', {
        'doctor'        : doctor,
        'availabilities': availabilities,
        'days'          : ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'hours'         : list(range(6, 21)),
    })


# ─────────────────────────────────────────
#  CREATE PRESCRIPTION
# ─────────────────────────────────────────
@login_required
def create_prescription(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor       = request.user.profile.doctor
    all_patients = PatientProfile.objects.filter(
        appointments__doctor=doctor    # ← uses your model's spelling
    ).distinct()

    if request.method == 'POST':
        patient_id     = request.POST.get('patient_id')
        appointment_id = request.POST.get('appointment_id', None)
        diagnosis      = request.POST.get('diagnosis', '')
        instructions   = request.POST.get('instructions', '')
        follow_up_date = request.POST.get('follow_up_date') or None

        patient = get_object_or_404(PatientProfile, id=patient_id)

        appointment = None
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id)
            except Appointment.DoesNotExist:
                pass

        prescription = Prescription.objects.create(
            doctor         = doctor,
            patient        = patient,
            appointment    = appointment,
            diagnosis      = diagnosis,
            instructions   = instructions,
            follow_up_date = follow_up_date,
        )

        medicine_names = request.POST.getlist('medicine_name')
        dosages        = request.POST.getlist('dosage')
        frequencies    = request.POST.getlist('frequency')
        durations      = request.POST.getlist('duration')
        timings        = request.POST.getlist('timing')
        med_notes      = request.POST.getlist('med_notes')

        for i in range(len(medicine_names)):
            if medicine_names[i].strip():
                PrescriptionItem.objects.create(
                    prescription  = prescription,
                    medicine_name = medicine_names[i].strip(),
                    dosage        = dosages[i]     if i < len(dosages)     else '',
                    frequency     = frequencies[i] if i < len(frequencies) else 'once',
                    duration      = durations[i]   if i < len(durations)   else '',
                    timing        = timings[i]     if i < len(timings)     else '',
                    notes         = med_notes[i]   if i < len(med_notes)   else '',
                )

        try:
            patient_user = patient.user_profile.user
            send_mail(
                subject='💊 New Prescription from Dr. ' + doctor.user_profile.user.get_full_name(),
                message=f'''
Hi {patient_user.get_full_name()},

Dr. {doctor.user_profile.user.get_full_name()} has created a new prescription for you.

Diagnosis    : {diagnosis}
Date         : {prescription.created_at.strftime("%d %B %Y")}
Follow-up    : {follow_up_date or "Not scheduled"}
Instructions : {instructions or "None"}

Login to view: http://127.0.0.1:8000/my-prescriptions/

- Hospital App Team
                ''',
                from_email     = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [patient_user.email],
                fail_silently  = False,
            )
        except Exception as e:
            print(f"Prescription email error: {e}")

        messages.success(request, '✅ Prescription created successfully!')
        return redirect('doctor_prescriptions')

    return render(request, 'accounts/create_prescription.html', {
        'doctor'      : doctor,
        'all_patients': all_patients,
        'frequencies' : PrescriptionItem.FREQUENCY_CHOICES,
        'timings'     : PrescriptionItem.TIMING_CHOICES,
    })


# ─────────────────────────────────────────
#  DOCTOR PRESCRIPTIONS LIST
# ─────────────────────────────────────────
@login_required
def doctor_prescriptions(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor        = request.user.profile.doctor
    prescriptions = Prescription.objects.filter(
        doctor=doctor
    ).prefetch_related('items').select_related('patient__user_profile__user')

    return render(request, 'accounts/doctor_prescriptions.html', {
        'doctor'       : doctor,
        'prescriptions': prescriptions,
    })


# ─────────────────────────────────────────
#  PATIENT PRESCRIPTIONS LIST
# ─────────────────────────────────────────
@login_required
def patient_prescriptions(request):
    if request.user.profile.role != 'patient':
        return redirect('doctor_dashboard')

    patient       = request.user.profile.patient
    prescriptions = Prescription.objects.filter(
        patient=patient
    ).prefetch_related('items').select_related('doctor__user_profile__user')

    return render(request, 'accounts/patient_prescriptions.html', {
        'patient'      : patient,
        'prescriptions': prescriptions,
    })


# ─────────────────────────────────────────
#  PRESCRIPTION DETAIL
# ─────────────────────────────────────────
@login_required
def prescription_detail(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    user_profile = request.user.profile

    if user_profile.role == 'doctor':
        if prescription.doctor != user_profile.doctor:
            messages.error(request, 'Not allowed.')
            return redirect('doctor_prescriptions')
    else:
        if prescription.patient != user_profile.patient:
            messages.error(request, 'Not allowed.')
            return redirect('patient_prescriptions')

    return render(request, 'accounts/prescription_detail.html', {
        'prescription': prescription,
        'items'       : prescription.items.all(),
    })


# ─────────────────────────────────────────
#  MEDICAL RECORDS — UPLOAD (Doctor)
# ─────────────────────────────────────────
@login_required
def upload_medical_record(request):
    """Doctor uploads a new medical record / lab report for a patient."""
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor       = request.user.profile.doctor
    all_patients = PatientProfile.objects.filter(
        appointments__doctor=doctor    # ← uses your model's spelling
    ).distinct()

    if request.method == 'POST':
        patient_id    = request.POST.get('patient_id')
        title         = request.POST.get('title', '').strip()
        record_type   = request.POST.get('record_type', 'lab_report')
        description   = request.POST.get('description', '').strip()
        record_date   = request.POST.get('record_date')
        uploaded_file = request.FILES.get('file')

        # Validate required fields
        errors = {}
        if not patient_id:
            errors['patient'] = 'Please select a patient.'
        if not title:
            errors['title'] = 'Title is required.'
        if not record_date:
            errors['record_date'] = 'Record date is required.'

        # Validate file type and size
        if uploaded_file:
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            if file_ext not in allowed_extensions:
                errors['file'] = 'Only PDF, JPG, and PNG files are allowed.'
            elif uploaded_file.size > 5 * 1024 * 1024:
                errors['file'] = 'File size must be under 5MB.'

        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'accounts/upload_medical_record.html', {
                'doctor'      : doctor,
                'all_patients': all_patients,
                'record_types': MedicalRecord.RECORD_TYPES,
                'form_data'   : request.POST,
            })

        patient        = get_object_or_404(PatientProfile, id=patient_id)
        appointment    = None
        appointment_id = request.POST.get('appointment_id')
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id)
            except Appointment.DoesNotExist:
                pass

        record = MedicalRecord.objects.create(
            doctor      = doctor,
            patient     = patient,
            appointment = appointment,
            title       = title,
            record_type = record_type,
            description = description,
            record_date = record_date,
            file        = uploaded_file,
        )

        # Email notification to patient
        try:
            patient_user = patient.user_profile.user
            send_mail(
                subject=f'📁 New Medical Record: {title}',
                message=f'''
Hi {patient_user.get_full_name()},

Dr. {doctor.user_profile.user.get_full_name()} has uploaded a new medical record for you.

Title       : {title}
Type        : {record.get_record_type_display()}
Date        : {record_date}
Description : {description or "No description provided"}

Login to view: http://127.0.0.1:8000/my-medical-records/

- Hospital App Team
                ''',
                from_email     = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [patient_user.email],
                fail_silently  = False,
            )
        except Exception as e:
            print(f"Medical record email error: {e}")

        messages.success(request, f'✅ Record "{title}" uploaded successfully!')
        return redirect('doctor_medical_records')

    return render(request, 'accounts/upload_medical_record.html', {
        'doctor'      : doctor,
        'all_patients': all_patients,
        'record_types': MedicalRecord.RECORD_TYPES,
        'form_data'   : {},
    })


# ─────────────────────────────────────────
#  MEDICAL RECORDS — DOCTOR LIST
# ─────────────────────────────────────────
@login_required
def doctor_medical_records(request):
    """Doctor views all medical records they have uploaded."""
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor         = request.user.profile.doctor
    patient_filter = request.GET.get('patient_id')
    type_filter    = request.GET.get('record_type')

    records = MedicalRecord.objects.filter(
        doctor=doctor
    ).select_related('patient__user_profile__user')

    if patient_filter:
        records = records.filter(patient_id=patient_filter)
    if type_filter:
        records = records.filter(record_type=type_filter)

    all_patients = PatientProfile.objects.filter(
        medical_records__doctor=doctor
    ).distinct()

    return render(request, 'accounts/doctor_medical_records.html', {
        'doctor'        : doctor,
        'records'       : records,
        'all_patients'  : all_patients,
        'record_types'  : MedicalRecord.RECORD_TYPES,
        'patient_filter': patient_filter,
        'type_filter'   : type_filter,
    })


# ─────────────────────────────────────────
#  MEDICAL RECORDS — PATIENT LIST
# ─────────────────────────────────────────
@login_required
def patient_medical_records(request):
    """Patient views all their medical records."""
    if request.user.profile.role != 'patient':
        return redirect('doctor_dashboard')

    patient     = request.user.profile.patient
    type_filter = request.GET.get('record_type')

    records = MedicalRecord.objects.filter(
        patient=patient
    ).select_related('doctor__user_profile__user')

    if type_filter:
        records = records.filter(record_type=type_filter)

    return render(request, 'accounts/patient_medical_records.html', {
        'patient'     : patient,
        'records'     : records,
        'record_types': MedicalRecord.RECORD_TYPES,
        'type_filter' : type_filter,
    })


# ─────────────────────────────────────────
#  MEDICAL RECORDS — DETAIL
# ─────────────────────────────────────────
@login_required
def medical_record_detail(request, record_id):
    """View a single medical record — accessible by the doctor who uploaded or the patient."""
    record       = get_object_or_404(MedicalRecord, id=record_id)
    user_profile = request.user.profile

    if user_profile.role == 'doctor':
        if record.doctor != user_profile.doctor:
            messages.error(request, 'You are not allowed to view this record.')
            return redirect('doctor_medical_records')
    else:
        if record.patient != user_profile.patient:
            messages.error(request, 'You are not allowed to view this record.')
            return redirect('patient_medical_records')

    return render(request, 'accounts/medical_record_detail.html', {
        'record': record,
    })