from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile, DoctorProfile, PatientProfile


class UserRegistrationForm(forms.Form):
    # ── No username field — generated automatically ──

    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autofocus': True,
        }),
        error_messages={'required': 'First name is required.'}
    )

    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
        }),
        error_messages={'required': 'Last name is required.'}
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
        }),
        error_messages={
            'required': 'Email address is required.',
            'invalid' : 'Enter a valid email address.',
        }
    )

    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 9876543210 (optional)',
        })
    )

    role = forms.ChoiceField(
        choices=[('patient', 'Patient'), ('doctor', 'Doctor')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Please select a role.'}
    )

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
        }),
        error_messages={'required': 'Password is required.'}
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter your password',
        }),
        error_messages={'required': 'Please confirm your password.'}
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'This email address is already registered. Please login instead.'
            )
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data


class DoctorRegistrationForm(forms.ModelForm):
    class Meta:
        model  = DoctorProfile
        fields = ['specialization', 'license_number', 'experience_years', 'bio']
        widgets = {
            'specialization'  : forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Cardiology, Dermatology',
            }),
            'license_number'  : forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. MED-12345',
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Years of experience',
                'min': 0,
            }),
            'bio'             : forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description about yourself...',
                'rows': 3,
            }),
        }
        error_messages = {
            'specialization': {'required': 'Specialization is required.'},
            'license_number': {'required': 'License number is required.'},
        }

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number', '').strip()
        if DoctorProfile.objects.filter(license_number=license_number).exists():
            raise forms.ValidationError(
                'This license number is already registered.'
            )
        return license_number


class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model  = PatientProfile
        fields = ['date_of_birth', 'blood_group', 'address', 'emergency_contact']
        widgets = {
            'date_of_birth'    : forms.DateInput(attrs={
                'class': 'form-control',
                'type' : 'date',
            }),
            'blood_group'      : forms.Select(attrs={'class': 'form-select'}),
            'address'          : forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your address',
                'rows': 2,
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact number',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All patient fields are optional
        for field in self.fields.values():
            field.required = False