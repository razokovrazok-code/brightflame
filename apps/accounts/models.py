from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('warehouse_manager', 'Ombor Menejeri'),
        ('receiver', 'Qabul Operatori'),
        ('picker', "Yig'uvchi"),
        ('dispatcher', 'Dispetcher'),
        ('returns_operator', 'Qaytarish Operatori'),
        ('seller', 'Sotuvchi'),
    ]
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='picker')
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    def is_seller(self):
        return self.role == 'seller'

    def is_admin_or_manager(self):
        return self.role in ('admin', 'warehouse_manager')

    def has_seller_profile(self):
        return hasattr(self, 'seller_profile')


class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    seller_name = models.CharField(max_length=200, verbose_name='Sotuvchi nomi')
    seller_code = models.CharField(max_length=50, unique=True, verbose_name='Sotuvchi kodi')
    contact_info = models.TextField(blank=True, verbose_name='Aloqa ma\'lumotlari')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sotuvchi profili'
        verbose_name_plural = 'Sotuvchi profillari'
        ordering = ['seller_name']

    def __str__(self):
        return f'{self.seller_name} ({self.seller_code})'
