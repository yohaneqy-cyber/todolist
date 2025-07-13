from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from datetime import timedelta
from rest_framework import status 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from .models import Task, User
from .serializers import TaskSerializer
from .forms import CustomUserCreationForm

User = get_user_model()


@api_view(['GET'])
def task_detail(request, pk):
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return Response({'error':'Task Not Found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = TaskSerializer(task)
    return Response(serializer.data)


class ApiOverView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        return Response({'message': 'Welcome to the Task API'}, status=status.HTTP_200_OK)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    tasks = Task.objects.all()
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def task_create(request):
    serializer = TaskSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.data)

@login_required
def home(request):
    filter_type = request.GET.get('filter', 'all')
    today = now().date()

    def iranian_weekday(d):
        wd = d.weekday()
        return(wd + 2) % 7
    
    if filter_type == 'today':
        tasks = Task.objects.filter(user=request.user, created__date=today)
    
    elif filter_type == 'week':
        start_week = today - timedelta(days=iranian_weekday(today))
        end_week = start_week + timedelta(days=6)
        tasks = Task.objects.filter(user=request.user, created__date__range=[start_week, end_week])

    elif filter_type == 'done':
        tasks = Task.objects.filter(user=request.user ,completed=True)

    elif filter_type == 'pending':
        tasks = Task.objects.filter(user=request.user,completed=False)

    else:
        tasks = Task.objects.filter(user=request.user).order_by('-created')

    if filter_type == 'all':
        pending_tasks = tasks.filter(completed=False)
        completed_tasks = tasks.filter(completed=True)
    else:
        pending_tasks = tasks
        completed_tasks = []



    context = {'tasks': tasks, 'pending_tasks': pending_tasks, 'completed_tasks': completed_tasks}
    return render(request, 'base/home.html', context )

@login_required(login_url='/login')
def add_task(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        remainder_str = request.POST.get('remainder_datetime')
        reminder = None
        if remainder_str:
            reminder = parse_datetime(remainder_str)
        Task.objects.create(user = request.user, title=title, reminder_datetime=reminder)
        return redirect('home')
    return render(request, 'base/add_task.html')


def complete_task(request, pk):
    task = get_object_or_404(Task, id=pk, user = request.user)
    task.completed = True
    task.save()
    return redirect('home')

def update_task(request, pk):
    task = get_object_or_404(Task, id=pk, user = request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        task.title = title
        task.save()
        return redirect('home')
    else:
        context = {'task':task}
        return render(request, 'base/update_task.html', context)
    

def delete_task(request,pk):
    task = get_object_or_404(Task, id=pk, user = request.user)
    if request.method == 'POST':
        task.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'task':task})

from django.contrib.auth import get_user_model
User = get_user_model()

def LoginPage(request):
    page = 'login'

    if request.method == 'POST':
        email = request.POST.get('email')  
        password = request.POST.get('password')
         
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('home')
        else:
            messages.error(request, "Invalid email or password")

    return render(request, 'base/login_register.html', {'page': page})

def LogoutUser(request):
    logout(request)
    return redirect('home')

def RegisterPage(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            existing  = User.objects.filter(email=email, is_active=False).first()
            if existing:
                existing.delete()

            user = form.save(commit=False)
            user.is_active = False
            user.save()

            request.session['registered_email'] = user.email  

            current_site = get_current_site(request)
            mail_subject = 'Activate Your Account'
            message = render_to_string('base/activate_account_email.html', {
                'user': user, 
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            user.email_user(mail_subject, message)

            return redirect('email_verification_sent')  

    else:
        form = CustomUserCreationForm()

    return render(request, 'base/login_register.html', {'form': form, 'page': 'register'})
def activate_account(request,uidb64,token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(ValueError, TypeError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "Your Account is Activated")
        return redirect('home')
    else:
        messages.error(request, "Invalid Activation Link")
        return redirect("login")
    
def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_link  = request.build_absolute_uri(
        reverse('activate', kwargs={'uidb64':uid, 'token':token})
    )

    subject = "Activate your account"
    message = f"Click the link below to activate your account\n{activation_link}"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)


  
def resend_activation_email(request):
    first = request.session.get('registered_email')
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, 'User with this email already exist')
                return redirect('login')
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('activate', kwargs={'uidb64':uid, 'token':token})
            )
            subject_mail = "Activate Your Account"
            message = f"Click the link below to activate your account\n {activation_link}"

            send_mail(subject_mail, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            messages.success(request, 'We send another activation link to your email')
            return redirect('email_verification_sent')

        except User.DoesNotExist:
            messages.error(request, 'NO user with this email')
            return redirect('resend_activation')
    return render(request, 'base/resend_activation.html', {'first':first})


def email_verification_sent(request):
    email = request.session.get('registered_email')
    return render(request, 'base/email_verification_sent.html',{'email':email})


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'NO user with this email')
            return redirect('password_reset_request')

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64':uid,'token':token})
)


        email_subject = 'Reset Your Password'
        message = render_to_string('base/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
        })

        user.email_user(email_subject,message)
        messages.success(request, 'Resest password link sent to your email')
        return redirect('login')
    
    return render(request, 'base/password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password Chenged')
                return redirect('login')
        
        else:
            form = SetPasswordForm(user)
        return render(request, 'base/password_reset_confirm.html', {'form':form})
    
    else:
        messages.error(request, 'Link Is Invalid')
        return redirect('password_reset_request')