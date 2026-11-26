"""Productionda admin foydalanuvchini yaratadi (idempotent).

Parol koddan emas, DJANGO_ADMIN_PASSWORD muhit o'zgaruvchisidan olinadi —
AWS'da u Secrets Manager'dan EC2 ishga tushganda o'qiladi.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from decouple import config


class Command(BaseCommand):
    help = "DJANGO_ADMIN_USERNAME / DJANGO_ADMIN_PASSWORD asosida admin yaratadi"

    def handle(self, *args, **options):
        username = config('DJANGO_ADMIN_USERNAME', default='admin')
        password = config('DJANGO_ADMIN_PASSWORD', default='')
        if not password:
            raise CommandError('DJANGO_ADMIN_PASSWORD berilmagan')

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'role': 'admin', 'is_staff': True, 'is_superuser': True},
        )
        # Secrets Manager — yagona manba: parol farq qilsa, sinxronlanadi
        changed = created or not user.check_password(password)
        if changed:
            user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.role = 'admin'
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Admin '{username}' yaratildi"))
        elif changed:
            self.stdout.write(self.style.SUCCESS(f"Admin '{username}' paroli Secrets Manager bilan sinxronlandi"))
        else:
            self.stdout.write(f"Admin '{username}' allaqachon mavjud va paroli mos")
