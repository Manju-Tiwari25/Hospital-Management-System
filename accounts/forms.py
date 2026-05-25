from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, DoctorProfile, PatientProfile


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    
    

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data


class DoctorRegistrationForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ['specialization', 'license_number', 'experience_years', 'bio']


class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ['date_of_birth', 'blood_group', 'address', 'emergency_contact']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    
        

