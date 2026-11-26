"""CI'da ishlaydigan asosiy smoke-testlar."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


class HealthCheckTests(TestCase):
    def test_health_reports_database(self):
        r = self.client.get('/health/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['database'])
        self.assertIn('instance', data)


class AccessTests(TestCase):
    def test_login_page_renders(self):
        self.assertEqual(self.client.get('/login/').status_code, 200)

    def test_anonymous_is_redirected_to_login(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])

    def test_admin_sees_main_pages(self):
        admin = get_user_model().objects.create_user(
            username='t_admin', password='x', role='admin', is_staff=True
        )
        self.client.force_login(admin)
        for url in ['/', '/catalog/', '/warehouse/', '/warehouse/inventory/',
                    '/logistics/orders/', '/logistics/picking/', '/logistics/reports/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_picker_cannot_open_user_management(self):
        picker = get_user_model().objects.create_user(username='t_picker', password='x', role='picker')
        self.client.force_login(picker)
        self.assertEqual(self.client.get('/accounts/users/').status_code, 403)


class EnsureAdminCommandTests(TestCase):
    @override_settings()
    def test_creates_admin_once(self):
        import os
        from django.core.management import call_command
        os.environ['DJANGO_ADMIN_PASSWORD'] = 'Secret-for-test-1'
        try:
            call_command('ensure_admin')
            call_command('ensure_admin')
        finally:
            del os.environ['DJANGO_ADMIN_PASSWORD']
        users = get_user_model().objects.filter(username='admin')
        self.assertEqual(users.count(), 1)
        self.assertTrue(users.first().is_superuser)

    def test_syncs_password_from_secret(self):
        import os
        from django.core.management import call_command
        get_user_model().objects.create_user(username='admin', password='old-password')
        os.environ['DJANGO_ADMIN_PASSWORD'] = 'New-secret-value-2'
        try:
            call_command('ensure_admin')
        finally:
            del os.environ['DJANGO_ADMIN_PASSWORD']
        admin = get_user_model().objects.get(username='admin')
        self.assertTrue(admin.check_password('New-secret-value-2'))
        self.assertTrue(admin.is_superuser and admin.is_staff and admin.role == 'admin')
