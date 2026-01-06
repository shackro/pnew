from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'phone',
        'is_active',
        'is_verified',
        'date_joined',
    )
    search_fields = ('username', 'email', 'phone')
    list_filter = ('is_active', 'is_verified')
