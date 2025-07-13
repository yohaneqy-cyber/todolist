from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('login/', views.LoginPage, name='login'),
    path('logout/', views.LogoutUser, name='logout'),
    path('register/', views.RegisterPage, name='register'),
    path('', views.home, name='home'),
    path('add_task/', views.add_task, name='add_task'),
    path('complete/<int:pk>/', views.complete_task, name='complete_task'),
    path('delete_task/<int:pk>/', views.delete_task, name='delete_task'),
    path('update_task/<int:pk>/', views.update_task, name='update_task'),
    path('api/tasks/', views.task_list, name='task-list'),
    path('api/tasks/<int:pk>/', views.task_detail, name='task-detail'),
    path('api/task-create/', views.task_create, name='task-create'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('activate/<uidb64>/<token>', views.activate_account, name="activate"),
    path('resend-activation/', views.resend_activation_email, name='resend_activation'),
    path('email-verification-sent/', views.email_verification_sent, name='email_verification_sent'),
    path('reset-password/', views.password_reset_request, name='password_reset_request'),
    path('reset-password/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),

]
