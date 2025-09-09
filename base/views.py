import json
from PIL import Image
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.db.models import Count
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Q
from datetime import timedelta, timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
from django.conf import settings
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import Task, User, Category, RecurringTask, TaskHistory, FriendRequest, Friendship, ChatMessage, Block
from .serializers import TaskSerializer, ChatMessageSerializers, UserSerializer
from .forms import CustomUserCreationForm, ReminderForm, ChengeForm, RecurringTaskForm, TaskForm, LoginForm, MySetPasswordForm
from PIL import Image
from pathlib import Path
import os

User = get_user_model()


@api_view(['GET'])
def task_detail(request, pk):
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return Response({'error':'Task Not Found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = TaskSerializer(task)
    return Response(serializer.data)


@api_view(['GET'])
def api(request):
    return Response('Welcome to api')



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
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



def home(request):
    filter_type = request.GET.get('filter', 'all')
    category_id = request.GET.get('category')
    query = request.GET.get('q', '').strip()
    today = now().date()
    categories = Category.objects.all()

    if request.user.is_authenticated:
        user = request.user
        own_tasks = Task.objects.filter(user=user)
        shared_tasks = Task.objects.filter(share_with=user)
        tasks = (own_tasks | shared_tasks).distinct()

        try:
            priority = int(request.GET.get('priority'))
            if priority not in [1, 2, 3]:
                priority = None
        except (ValueError, TypeError):
            priority = None

        def iranian_weekday(d):
            return (d.weekday() + 2) % 7

        if priority:
            tasks = tasks.filter(priority=priority)

        if query:
            tasks = tasks.filter(Q(title__icontains=query) | Q(bio__icontains=query))
            show_only = 'search'
        else:
            if filter_type == 'category' and category_id:
                try:
                    category_id_int = int(category_id)
                    tasks = tasks.filter(category_id=category_id_int)
                except (ValueError, TypeError):
                    pass
                show_only = 'category'

            elif filter_type == 'today':
                tasks = tasks.filter(due_date__date=today)
                show_only = 'today'

            elif filter_type == 'week':
                start_week = today - timedelta(days=iranian_weekday(today))
                end_week = start_week + timedelta(days=6)
                tasks = tasks.filter(due_date__date__range=[start_week, end_week])
                show_only = 'week'

            elif filter_type == 'tomorrow':
                tomorrow = today + timedelta(days=1)
                tasks = tasks.filter(due_date__date=tomorrow)
                show_only = 'tomorrow'

            elif filter_type == 'done':
                tasks = tasks.filter(completed=True, parent=None)
                show_only = 'done'

            elif filter_type == 'pending':
                tasks = tasks.filter(completed=False, parent=None)
                show_only = 'pending'

            else:
                show_only = 'all'

        tasks = tasks.annotate(priority_int=Cast('priority', IntegerField())).order_by('-priority_int', '-created')

        # Recurring tasks
        if priority:
            recurring_tasks = RecurringTask.objects.none()
        else:
            recurring_tasks = RecurringTask.objects.filter(user=user, active=True)

            if query:
                recurring_tasks = recurring_tasks.filter(title__icontains=query)

            if filter_type == 'today':
                recurring_tasks = recurring_tasks.filter(start_date__date=today)
            elif filter_type == 'tomorrow':
                tomorrow = today + timedelta(days=1)
                recurring_tasks = recurring_tasks.filter(start_date__date=tomorrow)
            elif filter_type == 'week':
                start_week = today - timedelta(days=iranian_weekday(today))
                end_week = start_week + timedelta(days=6)
                recurring_tasks = recurring_tasks.filter(start_date__date__range=[start_week, end_week])

        normal_tasks = tasks.filter(recurring_task__isnull=True, parent__isnull=True)
        for task in normal_tasks:
            task.has_subtask = task.subtasks.exists()
            task.progress = task.progress_percent(user=user)

        pending_tasks = tasks.filter(completed=False, parent=None)
        completed_tasks = tasks.filter(completed=True, parent=None)

    else:
        tasks = Task.objects.none()
        recurring_tasks = RecurringTask.objects.none()
        normal_tasks = []
        pending_tasks = Task.objects.none()
        completed_tasks = Task.objects.none()
        show_only = 'all'
        priority = None

    context = {
        'tasks': tasks,
        'pending_tasks': pending_tasks,
        'completed_tasks': completed_tasks,
        'categories': categories,
        'recurring_tasks': recurring_tasks,
        'normal_tasks': normal_tasks,
        'show_only': show_only,
        'priority': priority,
    }
    return render(request, 'base/home.html', context)



def view_task(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if not (task.user == request.user or request.user in task.share_with.all()):
        messages.error(request, 'You Dont Have Success')
        return redirect('home')
    return render(request, 'base/view_task.html', {'task':task})

@login_required
def add_task(request):
    categories = Category.objects.all()
    print("User friends count:", request.user.friends.count())  # <-- این را اضافه کن
    
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user

            reminder_minutes = request.POST.get('remind_in_minutes')
            if reminder_minutes:
                task.reminder_at = timezone.now() + timedelta(minutes=int(reminder_minutes))

            category_id = request.POST.get('category')
            task.category = Category.objects.get(id=category_id) if category_id else None

            time_to_do = request.POST.get('time_to_do')
            if time_to_do:
                task.time_to_do = time_to_do

            task.save()
            form.save_m2m()
            return redirect('home')
    else:
        form = TaskForm(user=request.user)

    return render(request, 'base/add_task.html', {
        'form': form,
        'categories': categories,
    })


def dashbord(request):
    user = request.user
    today = now().date()

    normal_tasks = Task.objects.filter(user=user, recurring_task__isnull=True)
    recurring_tasks_instance = Task.objects.filter(user=user, recurring_task__isnull=False)
    recurring_tasks = RecurringTask.objects.filter(user=user, active=True)

    total_recurring_definitions = RecurringTask.objects.filter(user=user).count()
    total_normal = Task.objects.filter(user=user).count()
    total = total_normal + total_recurring_definitions
    done_tasks = Task.objects.filter(user=user, completed=True).count()
    today_normal_tasks = Task.objects.filter(user=user, created__date=today).count()
    today_tasks = today_normal_tasks + total_recurring_definitions
    subtasks_count = Task.objects.filter(user=user).exclude(parent=None).count()
    subtasks_list = Task.objects.filter(user=user).exclude(parent=None).order_by('-created')

    context = {
        'total': total,
        'done_tasks': done_tasks,
        'today_tasks': today_tasks,
        'recurring_tasks': recurring_tasks,
        'normal_tasks': normal_tasks,
        'recurring_tasks_instance': recurring_tasks_instance,
        'total_normal':total_normal,
        'total_recurring_definitions':total_recurring_definitions,
        'subtasks_count':subtasks_count,
        'subtasks_list':subtasks_list
        
    }

    return render(request, 'base/dashbord.html', context)

def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        old_copleted = task.completed
        task.completed = True
        task.save()

        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action='Done',
            old_title=task.title,
            new_title=task.title
        )
        return redirect('home')
    return render(request, 'base/completed_task.html', {'task':task})

@login_required
def update_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    categories = Category.objects.all()

    if request.method == 'POST':
        form = TaskForm(request.POST,request.FILES,instance=task,user=request.user,)
        if form.is_valid():
            updated_task = form.save(commit=False)
            category_id = request.POST.get('category')
            if category_id:
                try:
                    updated_task.category = Category.objects.get(id=int(category_id))
                except Category.DoesNotExist:
                    updated_task.category = None
            else:
                updated_task.category = None

            updated_task.save()
            form.save_m2m()
            return redirect('home')
    else:
        form = TaskForm(instance=task, user=request.user)

    context = {'form': form, 'task': task, 'categories': categories}
    return render(request, 'base/update_task.html', context)

def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if request.method == "POST":
        task.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponse(status=204)
        return redirect('home')
    return render(request, 'base/delete.html', {'task': task})


def LoginPage(request):
    page = 'login'
    
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            login(request, form.cleaned_data['user'])
            return redirect('home')
    return render(request, 'base/login_register.html', {'page': page, 'form':form})

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = ChengeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ChengeForm(instance=request.user)
    return render(request, 'base/profile.html', {'form': form})

def LogoutUser(request):
    logout(request)
    return redirect('home')

from django.contrib.auth import get_user_model
User = get_user_model()

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings

def RegisterPage(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            User.objects.filter(email=email, is_active=False).delete()

            user = form.save(commit=False)
            user.is_active = False
            user.save()

            request.session['registered_email'] = user.email

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('activate', kwargs={'uidb64': uid, 'token': token})
            )

            html_content = render_to_string('base/activate_account_email.html', {
                'user': user,
                'activation_link': activation_link,
            })
            text_content = strip_tags(html_content)

            subject = 'Activate Your Account'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, 'text/html')
            msg.send()

            return redirect('email_verification_sent')
        else:
            return render(request, 'base/login_register.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'base/login_register.html', {'form': form})


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
    

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings
from django.http import HttpRequest
from django.contrib.auth.tokens import default_token_generator


def send_activation_email(request: HttpRequest, user):
    try:
        # ایجاد uid و توکن فعال‌سازی
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # ساخت لینک فعال‌سازی
        url_path = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        activation_link = request.build_absolute_uri(url_path)

        print('[DEBUG] Activation link:', activation_link)

        # بارگذاری و رندر قالب HTML
        html_content = render_to_string('base/activate_account_email.html', {
            'user': user,
            'activation_link': activation_link,
        })

        # تبدیل HTML به متن ساده
        text_content = strip_tags(html_content)

        # اطلاعات ایمیل
        subject = "Activate your account"
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        # ایجاد و ارسال ایمیل
        msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        msg.attach_alternative(html_content, 'text/html')
        msg.send()

        print("[✅] Activation email sent successfully to:", user.email)

    except Exception as e:
        print("[❌ ERROR] Failed to send activation email:", str(e))




  
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
            messages.error(request, 'No user with this email')
            return redirect('password_reset_request')

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )

        email_subject = 'Reset Your Password'
        message = render_to_string('base/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
        })

        email_msg = EmailMessage(
            subject=email_subject,
            body=message,
            from_email='no-reply@example.com',
            to=[user.email],
        )
        email_msg.content_subtype = 'html'  # 👈 این خط باعث میشه ایمیل به صورت HTML ارسال بشه
        email_msg.send()

        messages.success(request, 'Reset password link sent to your email')
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
            form = MySetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password Chenged')
                return redirect('login')
        
        else:
            form = MySetPasswordForm(user)
        return render(request, 'base/password_reset_confirm.html', {'form':form})
    
    else:
        messages.error(request, 'Link Is Invalid')
        return redirect('password_reset_request')
    
def create_reminder(request):
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            remind_at = timezone.now() + timedelta(minutes=form.cleaned_data['remind_in_minutes'])
            Task.objects.create(
                user=request.user,
                title=form.cleaned_data['task_title'], 
                reminder_at=remind_at,
            )
            return redirect('home')
    else:
        form = ReminderForm()
    return render(request, 'base/create_reminder.html', {'form': form})


@login_required
def cerate_recurring_task(request):
    if request.method == 'POST':
        form = RecurringTaskForm(request.POST)
        if form.is_valid():
            recurring_task = form.save(commit=False)
            recurring_task.user = request.user
            recurring_task.save()
            return redirect('home')
    else:
        form = RecurringTaskForm()
    return render(request, 'base/create_recurring_task.html', {'form':form})

def update_recurring_task(request, pk):
    recurring_task = get_object_or_404(RecurringTask, id=pk ,user=request.user)

    if request.method == 'POST':
        form = RecurringTaskForm(request.POST, instance=recurring_task)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RecurringTaskForm(instance=recurring_task)

    return render(request, 'base/update_recurring_task.html', {'form':form})
    
def delete_recurring_task(request, pk):
    recurring_task = get_object_or_404(RecurringTask, id=pk ,user=request.user)

    if request.method == 'POST':
        recurring_task.delete()
        return redirect('home')
    return render(request, 'base/delete_recurring_task.html', {'recurring_task':recurring_task})

def add_subtask(request, task_id):
    parent = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            subtask = form.save(commit=False)
            subtask.user = request.user

            parent_from_form = form.cleaned_data.get('parent')
            if parent_from_form and parent_from_form.user == request.user:
                subtask.parent = parent_from_form
            else:
                subtask.parent = parent  

            subtask.save()
            return redirect('home')
    else:
        form = TaskForm(user=request.user, initial={'parent': parent})

    return render(request, 'base/add_subtask.html', {
        'form': form,
        'parent': parent
    })

def task_history(request):
    user = request.user
    tasks = Task.objects.filter(user=user).order_by('-created')
    return render(request, 'base/task_history.html', {'tasks': tasks})

@login_required
def calendar(request):
    tasks = Task.objects.filter(user=request.user).values('title', 'id', 'due_date')
    task_list = list(tasks)

    for t in task_list:
        if t['due_date']:
            t['due_date'] = t['due_date'].isoformat()
        else:
            t['due_date'] = None

    tasks_json = json.dumps(task_list)

    return render(request, 'base/calendar.html', {'tasks_json':tasks_json})

def complete_subtask(request, subtask_id):
    subtask = get_object_or_404(Task, id=subtask_id, user=request.user)
    subtask.completed = True
    subtask.save()
    return redirect('home')

def friend_requests(request):
    recived_request = FriendRequest.objects.filter(user_to=request)
    return render(request, 'base/friend_request_modal.html', {'recived_request':recived_request})

@login_required
@login_required
def friend_requests_api(request):
    incoming_requests = FriendRequest.objects.filter(to_user=request.user, is_accepted=False)
    requests_data = []

    for fr in incoming_requests:
        user = fr.from_user
        requests_data.append({
            "id": fr.id,
            "from_user_id": user.id,
            "from_user_name": getattr(user, "name", "Unknown"),
            "from_user_email": getattr(user, "email", ""),
            "from_user_avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None
        })

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"requests": requests_data})

    return render(request, "base/friend_requests.html", {"requests": requests_data})


@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    
    if query:
        users = User.objects.exclude(id=request.user.id).filter(name__icontains=query, is_active=True)
    else:
        users = User.objects.exclude(id=request.user.id).filter(is_active=True)[:5]  
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        users_data = []
        for u in users:
            avatar_url = u.avatar.url if u.avatar else None
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            users_data.append({
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'avatar': avatar_url
            })
        return JsonResponse({'users': users_data})

    context = {
        'users': users,
        'query': query,
    }
    return render(request, 'base/search_users.html', context)


@login_required
@require_POST
def send_friend_request(request, user_id):
    try:
        to_user = User.objects.get(id=user_id)

        if to_user == request.user:
            return JsonResponse({
                'success': False,
                'error': 'You cannot send a friend request to yourself.',
                'code': 'self_request'
            })

        already_friends = Friendship.objects.filter(
            user1=min(request.user, to_user, key=lambda u: u.id),
            user2=max(request.user, to_user, key=lambda u: u.id)
        ).exists()
        if already_friends:
            return JsonResponse({
                'success': False,
                'error': 'You are already friends.',
                'code': 'already_friends'
            })

        already_requested = FriendRequest.objects.filter(
            Q(from_user=request.user, to_user=to_user) |
            Q(from_user=to_user, to_user=request.user)
        ).exists()

        if already_requested:
            return JsonResponse({
                'success': False,
                'error': 'Friend request already exists.',
                'code': 'already_requested'
            })

        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        return JsonResponse({'success': True, 'message': 'Friend request sent successfully.'})

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found.',
            'code': 'not_found'
        }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'server_error'
        }, status=400)

@login_required
@require_POST
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)

    Friendship.objects.get_or_create(
        user1=min(friend_request.from_user, friend_request.to_user, key=lambda u: u.id),
        user2=max(friend_request.from_user, friend_request.to_user, key=lambda u: u.id)
    )
    friend_request.delete()
    return JsonResponse({'success': True, 'message': 'Friend request accepted.'})


@login_required
@require_POST
def decline_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    friend_request.delete()
    return JsonResponse({'success': True, 'message': 'Friend request declined.'})


@login_required
def friends_list_api(request):
    friendships = Friendship.objects.filter(user1=request.user) | Friendship.objects.filter(user2=request.user)
    friends = []

    for friendship in friendships:
        friend = friendship.user2 if friendship.user1 == request.user else friendship.user1

        name = getattr(friend, "name", "Unknown")
        email = getattr(friend, "email", "")
        avatar = None
        if hasattr(friend, "avatar") and friend.avatar:
            avatar = request.build_absolute_uri(friend.avatar.url)
        elif hasattr(friend, "profile") and getattr(friend.profile, "avatar", None):
            avatar = request.build_absolute_uri(friend.profile.avatar.url)

        friends.append({
            "id": friend.id,
            "name": name,
            "email": email,
            "avatar": avatar,
        })

    return JsonResponse({"friends": friends})



from django.db import transaction

@login_required
@require_POST
def unfriend(request, user_id):
    try:
        other_user = User.objects.get(id=user_id)

        with transaction.atomic():
            # حذف رابطه در Friendship (اگر هست)
            friendship = Friendship.objects.filter(
                Q(user1=request.user, user2=other_user) |
                Q(user1=other_user, user2=request.user)
            ).first()
            if friendship:
                friendship.delete()

            # حذف از فیلد friends هر دو کاربر
            request.user.friends.remove(other_user)
            other_user.friends.remove(request.user)

            # حذف دوست از تمام تسک‌هایی که با او به اشتراک گذاشته شده
            tasks_with_friend = Task.objects.filter(share_with=other_user)
            for task in tasks_with_friend:
                task.share_with.remove(other_user)

        return JsonResponse({'success': True, 'message': 'Unfriended successfully.'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found.'})


def user_profile_ajax(request, user_id):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse(status=400)    
    
    user = get_object_or_404(User, id=user_id)
    return render(request, 'base/user_profile.html', {'user': user})    


@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageApi(View):

    def get(self, request):
        sender_id = request.GET.get('sender_id')
        receiver_id = request.GET.get('receiver_id')

        if not sender_id or not receiver_id:
            return JsonResponse({"error": "sender_id and receiver_id required"}, status=400)

        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        messages = ChatMessage.objects.filter(
            Q(sender=sender, receiver=receiver, hidden_for_sender=False) |
            Q(sender=receiver, receiver=sender, hidden_for_receiver=False)
        ).order_by('timestamp')

        data = []
        for msg in messages:
            local_time = timezone.localtime(msg.timestamp) if msg.timestamp else None
            data.append({
                'id': msg.id,
                'sender': msg.sender.email,
                'receiver': msg.receiver.email,
                'message': msg.message,
                'timestamp': local_time.strftime("%H:%M:%S") if local_time else '',
                'is_read': msg.is_read,
            })

        # ✅ تعداد پیام‌های خوانده نشده فقط برای گیرنده
        unread_count = messages.filter(receiver=receiver, is_read=False).count()

        return JsonResponse({'messages': data, 'unread_count': unread_count}, safe=False)

    def post(self, request):
        try:
            data = json.loads(request.body)
            sender_id = data.get('sender_id')
            receiver_id = data.get('receiver_id')
            content = data.get('message', '').strip()

            if not sender_id or not receiver_id:
                return JsonResponse({"error": "sender_id and receiver_id required"}, status=400)
            if not content:
                return JsonResponse({"error": "Empty message"}, status=400)

            try:
                sender = User.objects.get(id=sender_id)
                receiver = User.objects.get(id=receiver_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            if Block.objects.filter(blocker=receiver, blocked=sender).exists():
                return JsonResponse({"error": "You are blocked by this user"}, status=403)

            msg = ChatMessage.objects.create(
                sender=sender, receiver=receiver, message=content, is_read=False
            )

            local_time = timezone.localtime(msg.timestamp) if msg.timestamp else None

            return JsonResponse({
                'id': msg.id,
                'sender': msg.sender.email,
                'receiver': msg.receiver.email,
                'message': msg.message,
                'timestamp': local_time.strftime("%H:%M:%S") if local_time else '',
                'is_read': msg.is_read,
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        

@csrf_exempt
def block_user(request, user_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    # بررسی لاگین بودن کاربر
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    try:
        blocked_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    # بلاک کردن کاربر با استفاده از مدل Block
    block, created = Block.objects.get_or_create(
        blocker=request.user,
        blocked=blocked_user
    )

    if not created:
        return JsonResponse({"success": False, "message": "User already blocked"})

    return JsonResponse({"success": True})


@csrf_exempt
def unblock_user(request, user_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    try:
        blocked_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    Block.objects.filter(blocker=request.user, blocked=blocked_user).delete()
    return JsonResponse({'success': True})

from django.http import JsonResponse
from .models import Block

@csrf_exempt
def send_message(request, user_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    try:
        receiver = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    # 👇 چک بلاک شدن
    if Block.objects.filter(blocker=request.user, blocked=receiver).exists():
        return JsonResponse({"error": "You blocked this user"}, status=403)

    if Block.objects.filter(blocker=receiver, blocked=request.user).exists():
        return JsonResponse({"error": "You are blocked by this user"}, status=403)

    # اینجا کد ذخیره پیام
    message = ChatMessage.objects.create(
        sender=request.user,
        receiver=receiver,
        text=request.POST.get("text", "")
    )

    return JsonResponse({
        "success": True,
        "message": {
            "id": message.id,
            "text": message.text,
            "sender": request.user.username
        }
    })

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class MessageUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializers
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # فقط پیام‌هایی که کاربر فرستاده یا دریافت کرده
        return ChatMessage.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        message_text = request.data.get('message', '').strip()

        if not message_text:
            return Response({'error': 'متن پیام خالی است.'}, status=400)

        instance.message = message_text
        instance.edited = True
        instance.save()
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_for_all = request.query_params.get('delete_for_all', 'false').lower() == 'true'

        if delete_for_all:
            # Delete message completely for everyone
            instance.delete()
            return Response({'success': True, 'message': 'پیام برای همه حذف شد'}, status=status.HTTP_204_NO_CONTENT)
        
        # Delete only for the current user
        if instance.sender == request.user:
            # Sender deletes for self only: mark hidden_for_sender
            instance.hidden_for_sender = True  # Make sure this field exists in model
            instance.save()
            return Response({'success': True, 'message': 'پیام فقط برای شما حذف شد'})
        elif instance.receiver == request.user:
            # Receiver deletes for self only: mark hidden_for_receiver
            instance.hidden_for_receiver = True  # Make sure this field exists in model
            instance.save()
            return Response({'success': True, 'message': 'پیام فقط برای شما حذف شد'})
        else:
            return Response({'error': 'شما اجازه حذف این پیام را ندارید'}, status=403)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    serializer = UserSerializer(user, context={'request': request})
    return Response(serializer.data)



def save_resized_avatars(image_path, user_id):
    sizes = [56, 112]
    avatars_dir = Path("media/avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")

    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    img = img.crop((left, top, left + min_side, top + min_side))

    base_name = f"user-avatar-{user_id}"

    for size in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        new_filename = f"{base_name}-{size}.webp"
        new_path = avatars_dir / new_filename
        resized.save(new_path, format='WEBP', quality=85, method=6)
    
    return base_name


from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def chats_list(request):
    user = request.user

    # همه کاربرانی که با این کاربر چت کردند
    sent_to = ChatMessage.objects.filter(sender=user).values_list("receiver", flat=True)
    received_from = ChatMessage.objects.filter(receiver=user).values_list("sender", flat=True)

    chat_user_ids = set(list(sent_to) + list(received_from))

    chats = []
    for uid in chat_user_ids:
        try:
            other = User.objects.get(id=uid)
            
            # مسیر آواتار
            avatar_url = other.avatar.url if other.avatar else None
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            
            # آخرین پیام بین دو کاربر
            last_msg_obj = ChatMessage.objects.filter(
                Q(sender=user, receiver=other) | Q(sender=other, receiver=user)
            ).order_by("-timestamp").first()

            if last_msg_obj:
                last_message = last_msg_obj.message
                timestamp = timezone.localtime(last_msg_obj.timestamp)
                now = timezone.localtime(timezone.now())

                # اگر پیام امروز باشد فقط ساعت:دقیقه
                if timestamp.date() == now.date():
                    last_message_time = timestamp.strftime("%H:%M")
                else:
                    last_message_time = timestamp.strftime("%d/%m")
            else:
                last_message = "پیامی وجود ندارد"
                last_message_time = ""

            chats.append({
                "id": other.id,
                "name": other.name,
                "avatar": avatar_url,
                "last_message": last_message,
                "last_message_time": last_message_time
            })
        except User.DoesNotExist:
            continue

    return JsonResponse({"chats": chats})



from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Block  # مدل بلاک خودت

@csrf_exempt
def check_block_status(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    blocked_by_me = Block.objects.filter(blocker=request.user, blocked=other_user).exists()
    blocked_by_other = Block.objects.filter(blocker=other_user, blocked=request.user).exists()

    return JsonResponse({
        "blockedByMe": blocked_by_me,
        "blockedByOther": blocked_by_other
    })


@csrf_exempt
@login_required
def unread_message_count(request):
    unread_counts = (
        ChatMessage.objects
        .filter(receiver=request.user, is_read=False)
        .values("sender_id")
        .annotate(count=Count("id"))
    )

    unread_by_user = {item["sender_id"]: item["count"] for item in unread_counts}
    total_count = sum(unread_by_user.values())

    return JsonResponse({
        "unread_count": total_count,   # برای هر جای قدیمی که هنوز data.unread_count استفاده می‌کنه
        "unread_by_user": unread_by_user  # برای فیلتر پیام‌های میوت شده
    })

@login_required
def friend_requests_count(request):
    count = FriendRequest.objects.filter(to_user=request.user, is_accepted=False).count()
    return JsonResponse({'count':count})

@login_required
def unread_message_count_each(request):
    counts = ChatMessage.objects.filter(
        receiver=request.user, is_read=False
    ).values('sender').annotate(unread_count=Count('id'))

    # ساخت دیکشنری با کلید sender_id و مقدار تعداد پیام‌های خوانده نشده
    result = {str(item['sender']): item['unread_count'] for item in counts}

    return JsonResponse(result)


@login_required
def mark_messages_read(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sender_id = data.get('sender_id')
        except:
            sender_id = None

        receiver = request.user

        if not sender_id:
            return JsonResponse({'error':'sender id required'}, status=400)
        
        try:
            sender = User.objects.get(id=sender_id)
        except User.DoesNotExist:
            return JsonResponse({'error':'user not found'}, status=404)

        ChatMessage.objects.filter(sender=sender, receiver=receiver, is_read=False).update(is_read=True)
        return JsonResponse({"success": True})
    
    return JsonResponse({"error": "POST required"}, status=405)


@method_decorator(csrf_exempt, name='dispatch')
class DeleteChatApi(View):
    def post(self, request, user_id):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Login required"}, status=403)
        
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # حذف همه پیام‌ها بین کاربر و کاربر مقابل
        ChatMessage.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user)
        ).delete()

        return JsonResponse({"success": True, "message": "Chat deleted"})


def delete_avatar(request):
    if request.method == 'POST':
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "No avatar set"})
    return JsonResponse({"success": False, "error": "Invalid request"})