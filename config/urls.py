from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
import socket

from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Load balancer va Docker healthcheck uchun: replika va DB holati."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False
    return JsonResponse(
        {'status': 'ok' if db_ok else 'error', 'database': db_ok, 'instance': socket.gethostname()},
        status=200 if db_ok else 503,
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('catalog/', include('apps.catalog.urls', namespace='catalog')),
    path('warehouse/', include('apps.warehouse.urls', namespace='warehouse')),
    path('logistics/', include('apps.logistics.urls', namespace='logistics')),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('health/', health_check, name='health'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
