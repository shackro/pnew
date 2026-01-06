# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)  # Changed from phone_number

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
    
    def clean_phone(self):  # Changed from clean_phone_number
        phone = self.cleaned_data['phone']
        if User.objects.filter(phone=phone).exists():  # Changed from phone_number
            raise forms.ValidationError("This phone number is already registered.")
        return phone

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label='Email or Phone')
    
    class Meta:
        model = User
        fields = ['username', 'password']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'currency_preference', 'theme_preference']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email read-only if needed
        self.fields['email'].disabled = True

class ProfileUpdateForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'address', 'date_of_birth', 'occupation', 
                  'monthly_income', 'risk_tolerance', 'investment_goals']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes for crispy forms
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            

                  
class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if new_password != confirm_password:
            raise forms.ValidationError("New passwords do not match.")
        
        if len(new_password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        return cleaned_data
    
    
