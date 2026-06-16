from django.contrib import admin
from .models import (
    UserProfile, DoctorProfile, PatientProfile,
    Appointment, DoctorAvailability,
    Prescription, PrescriptionItem, MedicalRecord   
)

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1   # shows 1 empty form by default

class PrescriptionAdmin(admin.ModelAdmin):
    inlines = [PrescriptionItemInline]
    list_display  = ['id', 'doctor', 'patient', 'diagnosis', 'created_at']
    list_filter   = ['created_at', 'doctor']
    search_fields = ['diagnosis', 'patient__user_profile__user__username']
    
@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display  = ['title', 'record_type', 'patient', 'doctor', 'record_date']
    list_filter   = ['record_type', 'record_date']
    search_fields = ['title', 'patient__user_profile__user__username']

admin.site.register(UserProfile)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)
admin.site.register(Appointment)
admin.site.register(DoctorAvailability)
admin.site.register(Prescription, PrescriptionAdmin)
admin.site.register(PrescriptionItem)