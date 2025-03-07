from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
import re  # Import regex module for phone number validation
from .models import UserProfile  # Import UserProfile for ProfileUpdateForm

User = get_user_model()

class RegistrationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=10, min_length=10, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit phone number'}),
        help_text="Enter a 10-digit phone number."
    )
    email = forms.EmailField(
        required=True, label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    first_name = forms.CharField(
        max_length=30, required=True, label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True, label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    country = forms.CharField(
        max_length=100, required=True, label="Country",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter country'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        required=True
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name', 'email', 'country', 'password1', 'password2']

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        
        # Ensure the phone number is exactly 10 digits and contains only numbers
        if not re.fullmatch(r'^\d{10}$', phone_number):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        # Ensure the phone number is not already registered
        if User.objects.filter(username=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["phone_number"]  # Set phone number as username
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=10, min_length=10, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit phone number'}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        required=True
    )

    def clean_username(self):
        phone_number = self.cleaned_data.get("username")
        
        # Ensure the phone number is exactly 10 digits and contains only numbers
        if not phone_number.isdigit() or len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        return phone_number

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=100, required=False, label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=100, required=False, label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=10, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number']

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        
        # Ensure the phone number is exactly 10 digits and contains only numbers
        if not re.fullmatch(r'^\d{10}$', phone_number):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Ensure phone number is unique, excluding the current user
        if User.objects.exclude(pk=self.instance.pk).filter(username=phone_number).exists():
            raise forms.ValidationError("This phone number is already in use.")

        return phone_number

# Fix for ProfileUpdateForm (if missing)
class ProfileUpdateForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False, label="Profile Picture",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['profile_picture']
