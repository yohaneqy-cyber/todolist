from django import forms
from django.forms import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from .models import User, RecurringTask, Task, Friendship

User = get_user_model()

def get_user_friends(user):
    friendships = Friendship.objects.filter(user1=user) | Friendship.objects.filter(user2=user)
    friends = []
    for friendship in friendships:
        if friendship.user1 == user:
            friends.append(friendship.user2)
        else:
            friends.append(friendship.user1)
    return User.objects.filter(id__in=[friend.id for friend in friends])

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('name', 'email', 'avatar', 'bio', 'password1', 'password2')
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'auth-input',
                'rows': 2,
                'style': 'min-height:50px; max-height:80px; resize: vertical;',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # چک کردن اینکه آیا کاربر فعال با این ایمیل وجود دارد یا خیر
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError('This Email is Already Taken')
        
        # اگر کاربر غیر فعالی با این ایمیل هست، حذفش کن (برای پاکسازی)
        User.objects.filter(email=email, is_active=False).delete()

        return email


class RecurringTaskForm(forms.ModelForm):
    class Meta:
        model = RecurringTask
        fields = ['title', 'interval_type', 'interval', 'start_date', 'end_date', 'active']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interval_type'].required = True
        self.fields['interval'].required = True
        self.fields['start_date'].required = True
        
from django import forms

class ChengeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar', 'name', 'email', 'bio')
        widgets = {
            'name': forms.TextInput(attrs={'autofocus': 'autofocus'}),
        }

from django import forms
from .models import User

class ChengeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar', 'name', 'email', 'bio')
        widgets = {
            'name': forms.TextInput(attrs={'autofocus': 'autofocus'}),
            'name': forms.TextInput(attrs={'autofocus': True}),
            'email': forms.EmailInput(attrs={'autofocus': False}),
            # می‌تونی بقیه ویجت‌ها رو هم اینجا اضافه کنی
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')

        inactive_users = User.objects.filter(email=email, is_active=False)
        if inactive_users.exists():
            inactive_users.delete()

        user_with_email = User.objects.filter(email=email, is_active=True).first()
        if user_with_email and user_with_email.pk != self.instance.pk:
            raise forms.ValidationError('This email is already in use.')

        return email



class ReminderForm(forms.Form):
    title = forms.CharField(max_length=200)
    reminder_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

class TaskForm(forms.ModelForm):
    share_with = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Share With Friends'
    )

    class Meta:
        model = Task
        fields = ['title', 'priority', 'completed', 'parent', 'due_date', 'bio', 'attachment', 'share_with']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            queryset = Task.objects.filter(user=user, parent__isnull=True)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields['parent'].queryset = queryset

            self.fields['share_with'].queryset = get_user_friends(user)
        else:
            self.fields['share_with'].queryset = User.objects.none()

    def clean_parent(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')

        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise ValidationError('A task cannot be its own parent')
        
        return parent
    


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'auth-input',
        'autofocus': True,
        'id': 'email',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'auth-input',
        'id': 'password',
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                raise forms.ValidationError('Invalid Email or Password')
            if not user.is_active:
                raise forms.ValidationError('User account is inactive.')

            cleaned_data['user'] = user
        return cleaned_data

class MySetPasswordForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class':'auth-input'})
