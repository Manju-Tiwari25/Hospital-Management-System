import re
import uuid
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework                 import status
from rest_framework.decorators      import api_view, permission_classes
from rest_framework.permissions     import IsAuthenticated, AllowAny
from rest_framework.response        import Response
from rest_framework.authtoken.models import Token

from .models import (
    UserProfile, DoctorProfile, PatientProfile,
    Appointment, DoctorAvailability,
    Prescription, PrescriptionItem,
    MedicalRecord,
)
from .serializers import (
    RegisterSerializer, LoginSerializer,
    DoctorProfileSerializer, PatientProfileSerializer,
    AppointmentSerializer, BookAppointmentSerializer,
    DoctorAvailabilitySerializer, SlotSerializer,
    PrescriptionSerializer,
    MedicalRecordSerializer,
)


# ─────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────
def generate_username(first_name, last_name, email):
    first = re.sub(r'[^a-zA-Z0-9]', '', first_name).lower()
    last  = re.sub(r'[^a-zA-Z0-9]', '', last_name).lower()
    base  = f"{first}_{last}" if first and last else email.split('@')[0]
    base  = re.sub(r'[^a-zA-Z0-9_]', '', base)
    username = f"{base}_{str(uuid.uuid4().int)[:4]}"
    while User.objects.filter(username=username).exists():
        username = f"{base}_{str(uuid.uuid4().int)[:4]}"
    return username


# ─────────────────────────────────────────
#  AUTH ENDPOINTS
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """
    POST /api/register/
    Register a new doctor or patient.
    Returns auth token + user info.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    data       = serializer.validated_data
    role       = data['role']
    email      = data['email']
    first_name = data['first_name']
    last_name  = data['last_name']

    username = generate_username(first_name, last_name, email)

    user = User.objects.create_user(
        username   = username,
        first_name = first_name,
        last_name  = last_name,
        email      = email,
        password   = data['password'],
    )

    profile = UserProfile.objects.create(user=user, role=role)

    if role == 'doctor':
        DoctorProfile.objects.create(
            user_profile     = profile,
            specialization   = data.get('specialization', ''),
            license_number   = data.get('license_number', ''),
            experience_years = data.get('experience_years', 0),
            bio              = data.get('bio', ''),
        )
    else:
        PatientProfile.objects.create(
            user_profile      = profile,
            date_of_birth     = data.get('date_of_birth'),
            blood_group       = data.get('blood_group', ''),
            address           = data.get('address', ''),
            emergency_contact = data.get('emergency_contact', ''),
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'success'  : True,
        'message'  : 'Account created successfully.',
        'token'    : token.key,
        'username' : username,
        'role'     : role,
        'full_name': user.get_full_name(),
        'email'    : email,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    POST /api/login/
    Login with email or username + password.
    Returns auth token + user info.
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    login_input = serializer.validated_data['login_input'].strip()
    password    = serializer.validated_data['password']

    # Try username first
    user = authenticate(request, username=login_input, password=password)

    # If that fails try email
    if user is None:
        try:
            user_obj = User.objects.get(email=login_input.lower())
            user = authenticate(
                request, username=user_obj.username, password=password
            )
        except User.DoesNotExist:
            pass

    if user is None:
        return Response(
            {'success': False, 'message': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'success'  : True,
        'message'  : 'Login successful.',
        'token'    : token.key,
        'username' : user.username,
        'role'     : user.profile.role,
        'full_name': user.get_full_name(),
        'email'    : user.email,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """
    POST /api/logout/
    Deletes the auth token — user must re-login.
    """
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({'success': True, 'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_profile(request):
    """
    GET /api/profile/
    Returns the logged-in user's full profile.
    """
    user    = request.user
    profile = user.profile

    if profile.role == 'doctor':
        data = DoctorProfileSerializer(profile.doctor).data
    else:
        data = PatientProfileSerializer(profile.patient).data

    return Response({
        'success': True,
        'role'   : profile.role,
        'profile': data,
    })


# ─────────────────────────────────────────
#  DOCTOR ENDPOINTS
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_doctor_list(request):
    """
    GET /api/doctors/
    Returns all doctors (used by patients to choose a doctor).
    Optional filter: ?specialization=Cardiology
    """
    doctors = DoctorProfile.objects.select_related('user_profile__user').all()

    specialization = request.GET.get('specialization')
    if specialization:
        doctors = doctors.filter(specialization__icontains=specialization)

    serializer = DoctorProfileSerializer(doctors, many=True)
    return Response({
        'success': True,
        'count'  : doctors.count(),
        'doctors': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_doctor_slots(request, doctor_id):
    """
    GET /api/doctors/<doctor_id>/slots/?date=2026-06-20
    Returns available and booked slots for a doctor on a date.
    """
    import datetime

    try:
        doctor = DoctorProfile.objects.get(id=doctor_id)
    except DoctorProfile.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Doctor not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'success': False, 'message': 'date parameter is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        return Response(
            {'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    day_name = date_obj.strftime('%A')

    try:
        availability = DoctorAvailability.objects.get(
            doctor=doctor, day=day_name
        )
    except DoctorAvailability.DoesNotExist:
        return Response({
            'success'  : True,
            'available': False,
            'message'  : f'Doctor is not available on {day_name}.',
            'slots'    : [],
        })

    booked_hours = list(
        Appointment.objects.filter(
            doctor=doctor, date=date_obj
        ).exclude(status='cancelled').values_list('hour', flat=True)
    )

    slots = []
    for hour in range(availability.start_hour, availability.end_hour):
        suffix  = 'AM' if hour < 12 else 'PM'
        display = f"{hour if hour <= 12 else hour - 12}:00 {suffix}"
        slots.append({
            'hour'   : hour,
            'display': display,
            'booked' : hour in booked_hours,
        })

    return Response({
        'success'    : True,
        'available'  : True,
        'doctor_name': f"Dr. {doctor.user_profile.user.get_full_name()}",
        'date'       : date_str,
        'day'        : day_name,
        'slots'      : slots,
    })


# ─────────────────────────────────────────
#  APPOINTMENT ENDPOINTS
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_appointments(request):
    """
    GET  /api/appointments/  — list appointments for logged-in user
    POST /api/appointments/  — book a new appointment (patient only)
    """
    profile = request.user.profile

    # ── GET: list appointments ──
    if request.method == 'GET':
        if profile.role == 'doctor':
            appointments = Appointment.objects.filter(
                doctor=profile.doctor
            ).order_by('-date', '-hour')
        else:
            appointments = Appointment.objects.filter(
                patient=profile.patient
            ).order_by('-date', '-hour')

        # Optional status filter: ?status=pending
        status_filter = request.GET.get('status')
        if status_filter:
            appointments = appointments.filter(status=status_filter)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response({
            'success'     : True,
            'count'       : appointments.count(),
            'appointments': serializer.data,
        })

    # ── POST: book appointment ──
    if profile.role != 'patient':
        return Response(
            {'success': False, 'message': 'Only patients can book appointments.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = BookAppointmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data
    appointment = Appointment.objects.create(
        patient = profile.patient,
        doctor  = data['doctor'],
        date    = data['date'],
        hour    = data['hour'],
        reason  = data.get('reason', ''),
        status  = 'pending',
    )

    return Response({
        'success'    : True,
        'message'    : 'Appointment booked successfully.',
        'appointment': AppointmentSerializer(appointment).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def api_appointment_detail(request, appointment_id):
    """
    GET   /api/appointments/<id>/  — view single appointment
    PATCH /api/appointments/<id>/  — update status (doctor only)
                                   — cancel (patient only)
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Appointment not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    profile = request.user.profile

    # Security check
    if profile.role == 'doctor' and appointment.doctor != profile.doctor:
        return Response(
            {'success': False, 'message': 'Not allowed.'},
            status=status.HTTP_403_FORBIDDEN
        )
    if profile.role == 'patient' and appointment.patient != profile.patient:
        return Response(
            {'success': False, 'message': 'Not allowed.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'GET':
        return Response({
            'success'    : True,
            'appointment': AppointmentSerializer(appointment).data,
        })

    # PATCH
    new_status = request.data.get('status')

    if profile.role == 'doctor':
        allowed = ['confirmed', 'cancelled', 'completed']
    else:
        allowed = ['cancelled']   # patients can only cancel

    if new_status not in allowed:
        return Response(
            {'success': False, 'message': f'Invalid status. Allowed: {allowed}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    appointment.status = new_status
    if request.data.get('notes'):
        appointment.notes = request.data['notes']
    appointment.save()

    return Response({
        'success'    : True,
        'message'    : f'Appointment marked as {new_status}.',
        'appointment': AppointmentSerializer(appointment).data,
    })


# ─────────────────────────────────────────
#  PRESCRIPTION ENDPOINTS
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_prescriptions(request):
    """
    GET /api/prescriptions/
    Doctor → sees all prescriptions they wrote
    Patient → sees all their prescriptions
    """
    profile = request.user.profile

    if profile.role == 'doctor':
        prescriptions = Prescription.objects.filter(
            doctor=profile.doctor
        ).prefetch_related('items')
    else:
        prescriptions = Prescription.objects.filter(
            patient=profile.patient
        ).prefetch_related('items')

    serializer = PrescriptionSerializer(prescriptions, many=True)
    return Response({
        'success'      : True,
        'count'        : prescriptions.count(),
        'prescriptions': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_prescription_detail(request, prescription_id):
    """
    GET /api/prescriptions/<id>/
    View a single prescription with all medicines.
    """
    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except Prescription.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Prescription not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    profile = request.user.profile
    if profile.role == 'doctor' and prescription.doctor != profile.doctor:
        return Response({'success': False, 'message': 'Not allowed.'}, status=403)
    if profile.role == 'patient' and prescription.patient != profile.patient:
        return Response({'success': False, 'message': 'Not allowed.'}, status=403)

    serializer = PrescriptionSerializer(prescription)
    return Response({'success': True, 'prescription': serializer.data})


# ─────────────────────────────────────────
#  MEDICAL RECORDS ENDPOINTS
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_medical_records(request):
    """
    GET /api/medical-records/
    Doctor → sees all records they uploaded
    Patient → sees all their records
    Optional filter: ?record_type=lab_report
    """
    profile     = request.user.profile
    type_filter = request.GET.get('record_type')

    if profile.role == 'doctor':
        records = MedicalRecord.objects.filter(doctor=profile.doctor)
    else:
        records = MedicalRecord.objects.filter(patient=profile.patient)

    if type_filter:
        records = records.filter(record_type=type_filter)

    serializer = MedicalRecordSerializer(
        records, many=True, context={'request': request}
    )
    return Response({
        'success': True,
        'count'  : records.count(),
        'records': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_medical_record_detail(request, record_id):
    """
    GET /api/medical-records/<id>/
    View a single medical record.
    """
    try:
        record = MedicalRecord.objects.get(id=record_id)
    except MedicalRecord.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Record not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    profile = request.user.profile
    if profile.role == 'doctor' and record.doctor != profile.doctor:
        return Response({'success': False, 'message': 'Not allowed.'}, status=403)
    if profile.role == 'patient' and record.patient != profile.patient:
        return Response({'success': False, 'message': 'Not allowed.'}, status=403)

    serializer = MedicalRecordSerializer(record, context={'request': request})
    return Response({'success': True, 'record': serializer.data})


# ─────────────────────────────────────────
#  DASHBOARD SUMMARY ENDPOINT
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    """
    GET /api/dashboard/
    Returns summary stats for the logged-in user's dashboard.
    Used by mobile app home screen.
    """
    profile = request.user.profile
    today   = timezone.now().date()

    if profile.role == 'doctor':
        doctor = profile.doctor

        today_count    = Appointment.objects.filter(
            doctor=doctor, date=today
        ).exclude(status='cancelled').count()

        upcoming_count = Appointment.objects.filter(
            doctor=doctor, date__gte=today, status='pending'
        ).count()

        patient_ids    = Appointment.objects.filter(
            doctor=doctor
        ).exclude(status='cancelled').values_list(
            'patient', flat=True
        ).distinct()
        total_patients = patient_ids.count()

        records_count  = MedicalRecord.objects.filter(doctor=doctor).count()

        upcoming = Appointment.objects.filter(
            doctor=doctor, date__gte=today, status='pending'
        ).order_by('date', 'hour')[:5]

        return Response({
            'success': True,
            'role'   : 'doctor',
            'stats'  : {
                'today_appointments': today_count,
                'upcoming'          : upcoming_count,
                'total_patients'    : total_patients,
                'records_uploaded'  : records_count,
            },
            'upcoming_appointments': AppointmentSerializer(upcoming, many=True).data,
        })

    else:
        patient = profile.patient

        upcoming_count = Appointment.objects.filter(
            patient=patient, date__gte=today
        ).exclude(status='cancelled').count()

        past_count = Appointment.objects.filter(
            patient=patient, date__lt=today
        ).count()

        prescription_count = Prescription.objects.filter(
            patient=patient
        ).count()

        records_count = MedicalRecord.objects.filter(
            patient=patient
        ).count()

        upcoming = Appointment.objects.filter(
            patient=patient, date__gte=today
        ).exclude(status='cancelled').order_by('date', 'hour')[:5]

        return Response({
            'success': True,
            'role'   : 'patient',
            'stats'  : {
                'upcoming_appointments': upcoming_count,
                'past_appointments'    : past_count,
                'prescriptions'        : prescription_count,
                'medical_records'      : records_count,
            },
            'upcoming_appointments': AppointmentSerializer(upcoming, many=True).data,
        })
        
# ─────────────────────────────────────────
#  HEALTH CHECK (keeps Render app awake)
# ─────────────────────────────────────────

@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok'}, status=200)