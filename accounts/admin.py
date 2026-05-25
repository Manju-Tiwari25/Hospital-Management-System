from django.contrib import admin
from .models import UserProfile, DoctorProfile, PatientProfile, Appointment, DoctorAvailability

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)
admin.site.register(Appointment)
admin.site.register(DoctorAvailability)