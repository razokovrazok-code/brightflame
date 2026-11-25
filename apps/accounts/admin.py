from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SellerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('WMS Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('WMS Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'phone')}),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('seller_name', 'seller_code', 'user', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('seller_name', 'seller_code', 'user__username', 'user__email')
    ordering = ('seller_name',)
