from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Task, Category, User


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ('title', 'created','user')
    readonly_fields=('created',)


class CustomUserAdmin(BaseUserAdmin):
    model = User
    inlines = [TaskInline]
    list_display=('email','date_joined','is_active','is_staff')
    list_filter=('is_active','is_staff')
    ordering=('email',)
    search_fields=('email', 'name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('user', {'fields': ('name', 'avatar')}),
        ('Access', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
        ('date', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email','password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Category)




