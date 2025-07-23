from django import forms
from django.forms import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
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
        fields = ('name', 'email', 'avatar', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')

        user_with_email = User.objects.filter(email=email, is_active=True).first()
        if user_with_email:
            raise forms.ValidationError('This email is already used by an active user.')

        inactive_users = User.objects.filter(email=email, is_active=False)
        if inactive_users.exists():
            inactive_users.delete()

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
        
class ChengeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar', 'name', 'email')

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
