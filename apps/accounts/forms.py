from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SellerProfile


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'phone', 'role', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'phone', 'role', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }


class SellerProfileForm(forms.ModelForm):
    class Meta:
        model = SellerProfile
        fields = ['seller_name', 'seller_code', 'contact_info', 'is_active']
        widgets = {
            'seller_name': forms.TextInput(attrs={'class': 'form-input'}),
            'seller_code': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_info': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }
