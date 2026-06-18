from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, DoctorProfile, PatientProfile,
    Appointment, DoctorAvailability,
    Prescription, PrescriptionItem,
    MedicalRecord,
)


# ─────────────────────────────────────────
#  USER & AUTH SERIALIZERS
# ─────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50)
    last_name  = serializers.CharField(max_length=50)
    email      = serializers.EmailField()
    password   = serializers.CharField(min_length=8, write_only=True)
    role       = serializers.ChoiceField(choices=['doctor', 'patient'])

    # Doctor fields (optional — only needed if role=doctor)
    specialization   = serializers.CharField(required=False, allow_blank=True)
    license_number   = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(required=False, default=0)
    bio              = serializers.CharField(required=False, allow_blank=True)

    # Patient fields (optional — only needed if role=patient)
    date_of_birth     = serializers.DateField(required=False, allow_null=True)
    blood_group       = serializers.CharField(required=False, allow_blank=True)
    address           = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                'This email is already registered.'
            )
        return value.lower()

    def validate(self, data):
        role = data.get('role')
        if role == 'doctor':
            if not data.get('specialization'):
                raise serializers.ValidationError(
                    {'specialization': 'Specialization is required for doctors.'}
                )
            if not data.get('license_number'):
                raise serializers.ValidationError(
                    {'license_number': 'License number is required for doctors.'}
                )
        return data


class LoginSerializer(serializers.Serializer):
    login_input = serializers.CharField()   # email or username
    password    = serializers.CharField(write_only=True)


# ─────────────────────────────────────────
#  PROFILE SERIALIZERS
# ─────────────────────────────────────────

class DoctorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email     = serializers.SerializerMethodField()

    class Meta:
        model  = DoctorProfile
        fields = [
            'id', 'full_name', 'email',
            'specialization', 'license_number',
            'experience_years', 'bio',
        ]

    def get_full_name(self, obj):
        return obj.user_profile.user.get_full_name()

    def get_email(self, obj):
        return obj.user_profile.user.email


class PatientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email     = serializers.SerializerMethodField()

    class Meta:
        model  = PatientProfile
        fields = [
            'id', 'full_name', 'email',
            'date_of_birth', 'blood_group',
            'address', 'emergency_contact',
        ]

    def get_full_name(self, obj):
        return obj.user_profile.user.get_full_name()

    def get_email(self, obj):
        return obj.user_profile.user.email


# ─────────────────────────────────────────
#  APPOINTMENT SERIALIZERS
# ─────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name        = serializers.SerializerMethodField()
    patient_name       = serializers.SerializerMethodField()
    doctor_specialization = serializers.SerializerMethodField()
    time_display       = serializers.SerializerMethodField()

    class Meta:
        model  = Appointment
        fields = [
            'id', 'date', 'hour', 'time_display',
            'status', 'reason', 'notes',
            'doctor', 'doctor_name', 'doctor_specialization',
            'patient', 'patient_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user_profile.user.get_full_name()}"

    def get_patient_name(self, obj):
        return obj.patient.user_profile.user.get_full_name()

    def get_doctor_specialization(self, obj):
        return obj.doctor.specialization

    def get_time_display(self, obj):
        return obj.get_time_display()


class BookAppointmentSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    date      = serializers.DateField()
    hour      = serializers.IntegerField(min_value=0, max_value=23)
    reason    = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        from .models import DoctorProfile, DoctorAvailability
        import datetime

        doctor_id = data.get('doctor_id')
        date      = data.get('date')
        hour      = data.get('hour')

        # Check doctor exists
        try:
            doctor = DoctorProfile.objects.get(id=doctor_id)
        except DoctorProfile.DoesNotExist:
            raise serializers.ValidationError({'doctor_id': 'Doctor not found.'})

        # Check doctor availability
        day_name = date.strftime('%A')
        try:
            availability = DoctorAvailability.objects.get(
                doctor=doctor, day=day_name
            )
            if not (availability.start_hour <= hour < availability.end_hour):
                raise serializers.ValidationError(
                    {'hour': f'Doctor is not available at {hour}:00 on {day_name}.'}
                )
        except DoctorAvailability.DoesNotExist:
            raise serializers.ValidationError(
                {'date': f'Doctor is not available on {day_name}.'}
            )

        # Check slot not already booked
        if Appointment.objects.filter(
            doctor=doctor, date=date, hour=hour
        ).exclude(status='cancelled').exists():
            raise serializers.ValidationError(
                {'hour': 'This time slot is already booked.'}
            )

        data['doctor'] = doctor
        return data


# ─────────────────────────────────────────
#  DOCTOR AVAILABILITY SERIALIZER
# ─────────────────────────────────────────

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model  = DoctorAvailability
        fields = ['id', 'day', 'start_hour', 'end_hour']


class SlotSerializer(serializers.Serializer):
    """Represents a single hourly time slot"""
    hour    = serializers.IntegerField()
    display = serializers.CharField()
    booked  = serializers.BooleanField()


# ─────────────────────────────────────────
#  PRESCRIPTION SERIALIZERS
# ─────────────────────────────────────────

class PrescriptionItemSerializer(serializers.ModelSerializer):
    frequency_display = serializers.SerializerMethodField()
    timing_display    = serializers.SerializerMethodField()

    class Meta:
        model  = PrescriptionItem
        fields = [
            'id', 'medicine_name', 'dosage',
            'frequency', 'frequency_display',
            'duration', 'timing', 'timing_display',
            'notes',
        ]

    def get_frequency_display(self, obj):
        return obj.get_frequency_display()

    def get_timing_display(self, obj):
        return obj.get_timing_display()


class PrescriptionSerializer(serializers.ModelSerializer):
    items        = PrescriptionItemSerializer(many=True, read_only=True)
    doctor_name  = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model  = Prescription
        fields = [
            'id', 'diagnosis', 'instructions',
            'follow_up_date', 'created_at',
            'doctor', 'doctor_name',
            'patient', 'patient_name',
            'items',
        ]
        read_only_fields = ['id', 'created_at']

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user_profile.user.get_full_name()}"

    def get_patient_name(self, obj):
        return obj.patient.user_profile.user.get_full_name()


# ─────────────────────────────────────────
#  MEDICAL RECORD SERIALIZER
# ─────────────────────────────────────────

class MedicalRecordSerializer(serializers.ModelSerializer):
    doctor_name       = serializers.SerializerMethodField()
    patient_name      = serializers.SerializerMethodField()
    record_type_label = serializers.SerializerMethodField()
    file_url          = serializers.SerializerMethodField()

    class Meta:
        model  = MedicalRecord
        fields = [
            'id', 'title', 'record_type', 'record_type_label',
            'description', 'record_date', 'created_at',
            'doctor', 'doctor_name',
            'patient', 'patient_name',
            'file_url',
        ]
        read_only_fields = ['id', 'created_at']

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user_profile.user.get_full_name()}"

    def get_patient_name(self, obj):
        return obj.patient.user_profile.user.get_full_name()

    def get_record_type_label(self, obj):
        return obj.get_record_type_display()

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None