from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class DoctorProfile(models.Model):
    user_profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name='doctor'
    )
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Dr. {self.user_profile.user.get_full_name()}"


class PatientProfile(models.Model):
    BLOOD_GROUPS = [
        ('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
        ('O+','O+'),('O-','O-'),('AB+','AB+'),('AB-','AB-'),
    ]
    user_profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name='patient'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS, blank=True)
    address = models.TextField(blank=True)                        
    emergency_contact = models.CharField(max_length=15, blank=True)  

    def __str__(self):
        return f"Patient: {self.user_profile.user.get_full_name()}"
    
    
class DoctorAvailability(models.Model):
    DAYS = [
        ('Monday','Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'),
        ('Saturday', 'Saturday'), ('Sunday', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name='availability'
    )   
    day = models.CharField(max_length=10, choices=DAYS)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()
    
    class Meta:
        unique_together = ('doctor', 'day')
        
    def __str__(self):
        return f"{self.doctor} - {self.day} ({self.start_hour}:00 - {self.end_hour}:00)"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('confirmed', 'confirmed'),
        ('cancelled', 'cancelled'),
        ('completed', 'completed'),
    ]
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='appointments'
    )
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name='Appointment'
    )
    date = models.DateField()
    hour = models.IntegerField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending'    
    )
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('doctor', 'date', 'hour')
    
    def __str__(self):
        return f"{self.patient} - Dr.{self.doctor} on {self.date} at {self.hour}:00"
    
    def get_time_display(self):
        suffix = 'AM' if self.hour < 12 else 'PM'
        h = self.hour if self.hour <= 12 else self.hour - 12
        return f"{h}:00 {suffix}"
    
class Prescription(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='prescriptions')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    diagnosis = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    follow_up_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']   # newest first

    def __str__(self):
        return f"Prescription #{self.id} - {self.patient} by {self.doctor}"


class PrescriptionItem(models.Model):
    FREQUENCY_CHOICES = [
        ('once',       'Once a day'),
        ('twice',      'Twice a day'),
        ('thrice',     'Three times a day'),
        ('four_times', 'Four times a day'),
        ('sos',        'SOS (as needed)'),
    ]

    TIMING_CHOICES = [
        ('before_food', 'Before Food'),
        ('after_food',  'After Food'),
        ('with_food',   'With Food'),
        ('empty_stomach', 'Empty Stomach'),
    ]

    prescription   = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name  = models.CharField(max_length=200)
    dosage         = models.CharField(max_length=100)   # e.g. "500mg", "10ml"
    frequency      = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    duration       = models.CharField(max_length=100)   # e.g. "5 days", "1 week"
    timing         = models.CharField(max_length=20, choices=TIMING_CHOICES, blank=True)
    notes          = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"