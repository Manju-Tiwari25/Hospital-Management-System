from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, DoctorRegistrationForm, PatientRegistrationForm
from .models import UserProfile, DoctorProfile, PatientProfile, Appointment, DoctorAvailability, Prescription, PrescriptionItem
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.core.mail import send_mail
from django.conf import settings

def register_view(request):
    if request.method == 'POST':
        # Get basic data
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')

        # Validate passwords
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')

        # Check username not taken
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return redirect('register')

        # Create user
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        # Create profile
        profile = UserProfile.objects.create(user=user, role=role)

        # Create role-specific profile
        if role == 'doctor':           
            DoctorProfile.objects.create(
                user_profile=profile,
                specialization=request.POST.get('specialization', ''),
                license_number=request.POST.get('license_number', ''),
                experience_years=request.POST.get('experience_years', 0),
                bio=request.POST.get('bio', ''),
            )
        else:
            dob = request.POST.get('date_of_birth')
            PatientProfile.objects.create(
                user_profile=profile,
                date_of_birth=dob,
                blood_group=request.POST.get('blood_group', ''),
                address=request.POST.get('address', ''),
                emergency_contact=request.POST.get('emergency_contact', ''),
            )

        messages.success(request, 'Account created! Please login.')
        
        # ── SMTP: Welcome Email ──
        try:
            send_mail(
                subject='Welcome to Hospital App!',
                message=f'''
                    Hi {user.get_full_name()},

                    Your account has been created successfully as a {role}.

                    {"You can now set your availability and manage appointments." if role == "doctor" else "You can now search doctors and book appointments."}

                    Login here: http://127.0.0.1:8000/login/

                    - Hospital App Team
                                    ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Welcome email error: {e}")
        # ── END Email ──

        return redirect('login')

    return render(request, 'accounts/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.profile.role == 'doctor':
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def doctor_dashboard(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')
    
    doctor = request.user.profile.doctor
    today = timezone.now().date()
    
    today_appointments = Appointment.objects.filter(
        doctor=doctor, date=today
    ).exclude(status='cancelled')
    
    all_appointments = Appointment.objects.filter(
        doctor=doctor
    ).exclude(status='cancelled')
    
    patient_ids = all_appointments.values_list('patient', flat=True).distinct()
    total_patients = patient_ids.count()
    
    upcoming = Appointment.objects.filter(
        doctor=doctor, date__gte=today, status='pending'
    ).order_by('date', 'hour')[:5]
    
    patient_list = PatientProfile.objects.filter(
        id__in=patient_ids
    )
    return render(request, 'accounts/doctor_dashboard.html',{
        'doctor' : doctor,
        'today_appointments' : today_appointments,
        'total_patients' : total_patients,
        'upcoming' : upcoming,
        'patients_list' : patient_list,
        'today' : today
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

    # All doctors for booking
    all_doctors = DoctorProfile.objects.all()
    prescription_count = Prescription.objects.filter(patient=patient).count()

    return render(request, 'accounts/patient_dashboard.html', {
        'patient'    : patient,
        'upcoming'   : upcoming,
        'past'       : past,
        'all_doctors': all_doctors,
        'today'      : today,
        'prescription_count' : prescription_count,
    })


# ─────────────────────────────────────────
#  BOOK APPOINTMENT (Patient)
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

        # Get day name e.g. "Monday"
        day_name = date_obj.strftime('%A')

        # Check doctor availability for that day
        try:
            availability = DoctorAvailability.objects.get(
                doctor=selected_doctor, day=day_name
            )
            # Build hour slots
            booked_hours = list(
                Appointment.objects.filter(
                    doctor=selected_doctor, date=date_obj
                ).exclude(status='cancelled').values_list('hour', flat=True)
            )
            for hour in range(availability.start_hour, availability.end_hour):
                available_slots.append({
                    'hour'    : hour,
                    'display' : f"{hour}:00 {'AM' if hour < 12 else 'PM'}",
                    'booked'  : hour in booked_hours,
                })
        except DoctorAvailability.DoesNotExist:
            available_slots = []  # doctor not available on this day

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

        # Check if slot is already taken
        if Appointment.objects.filter(
            doctor=doctor, date=date_obj, hour=hour_int
        ).exclude(status='cancelled').exists():
            messages.error(request, '❌ This slot is already booked. Please choose another.')
            return redirect(f'/book-appointment/?doctor_id={doctor_id}&date={date_str}')
    
        
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date_obj,
            hour=hour_int,
            reason=reason,
            status='pending',
        )

        # ── SMTP: Booking Confirmation Email ──
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
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient.user_profile.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Booking email error: {e}")
        # ── END Email ──

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
#  CANCEL APPOINTMENT (Patient)
# ─────────────────────────────────────────
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    # Only the patient who booked can cancel
    if appointment.patient != request.user.profile.patient:
        messages.error(request, 'Not allowed.')
        return redirect('patient_dashboard')
    
    appointment.status = 'cancelled'
    appointment.save()

    # ── SMTP: Cancellation Email ──
    try:
        patient_user = appointment.patient.user_profile.user
        doctor_user  = appointment.doctor.user_profile.user

        # Email to patient
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
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_user.email],
            fail_silently=False,
        )

        # Email to doctor
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
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[doctor_user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Cancellation email error: {e}")
    # ── END Email ──

    messages.success(request, 'Appointment cancelled.')
    return redirect('patient_dashboard')


# ─────────────────────────────────────────
#  UPDATE APPOINTMENT STATUS (Doctor)
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

            # ── SMTP: Status Update Email ──
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
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[patient_user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Status update email error: {e}")
            # ── END Email ──

            messages.success(request, f'Appointment marked as {new_status}.')
    return redirect('doctor_dashboard')


# ─────────────────────────────────────────
#  SET DOCTOR AVAILABILITY
# ─────────────────────────────────────────
@login_required
def set_availability(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor = request.user.profile.doctor
    availabilities = DoctorAvailability.objects.filter(doctor=doctor)

    if request.method == 'POST':
        days = request.POST.getlist('days')
        start_hour = int(request.POST.get('start_hour', 9))
        end_hour   = int(request.POST.get('end_hour', 17))

        # Remove old and recreate
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
        'days'          : ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
        'hours'         : list(range(6, 21)),
    })
    
# ── 1. Doctor creates a new prescription ──
@login_required
def create_prescription(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor = request.user.profile.doctor
    all_patients = PatientProfile.objects.filter(
        appointments__doctor=doctor
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

        # Create the prescription
        prescription = Prescription.objects.create(
            doctor       = doctor,
            patient      = patient,
            appointment  = appointment,
            diagnosis    = diagnosis,
            instructions = instructions,
            follow_up_date = follow_up_date,
        )

        # Get medicine lists from form
        medicine_names = request.POST.getlist('medicine_name')
        dosages        = request.POST.getlist('dosage')
        frequencies    = request.POST.getlist('frequency')
        durations      = request.POST.getlist('duration')
        timings        = request.POST.getlist('timing')
        med_notes      = request.POST.getlist('med_notes')

        # Save each medicine as PrescriptionItem
        for i in range(len(medicine_names)):
            if medicine_names[i].strip():   # skip empty rows
                PrescriptionItem.objects.create(
                    prescription  = prescription,
                    medicine_name = medicine_names[i].strip(),
                    dosage        = dosages[i] if i < len(dosages) else '',
                    frequency     = frequencies[i] if i < len(frequencies) else 'once',
                    duration      = durations[i] if i < len(durations) else '',
                    timing        = timings[i] if i < len(timings) else '',
                    notes         = med_notes[i] if i < len(med_notes) else '',
                )

        # Send email to patient
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

                    Please log in to view your complete prescription details.
                    http://127.0.0.1:8000/my-prescriptions/

                    - Hospital App Team
                                    ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient_user.email],
                fail_silently=False,
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


# ── 2. Doctor views all prescriptions they wrote ──
@login_required
def doctor_prescriptions(request):
    if request.user.profile.role != 'doctor':
        return redirect('patient_dashboard')

    doctor = request.user.profile.doctor

    prescriptions = Prescription.objects.filter(
        doctor=doctor
    ).prefetch_related('items').select_related(
        'patient__user_profile__user'
    )

    return render(request, 'accounts/doctor_prescriptions.html', {
        'doctor'       : doctor,
        'prescriptions': prescriptions,
    })


# ── 3. Patient views all their prescriptions ──
@login_required
def patient_prescriptions(request):
    if request.user.profile.role != 'patient':
        return redirect('doctor_dashboard')

    patient = request.user.profile.patient

    prescriptions = Prescription.objects.filter(
        patient=patient
    ).prefetch_related('items').select_related(
        'doctor__user_profile__user'
    )

    return render(request, 'accounts/patient_prescriptions.html', {
        'patient'      : patient,
        'prescriptions': prescriptions,
    })


# ── 4. View single prescription detail (both doctor and patient) ──
@login_required
def prescription_detail(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Security — only the doctor who wrote it or the patient can view
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