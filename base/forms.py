from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User  

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_qs = User.objects.filter(email=email)
        if user_qs.exists():
            if user_qs.filter(is_active=False).exists():
                # حذف کاربر غیرفعال
                user_qs.filter(is_active=False).delete()
            else:
                raise forms.ValidationError("User with this Email already exists.")
        return email