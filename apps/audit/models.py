from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='Foydalanuvchi'
    )
    action = models.CharField(max_length=100, verbose_name='Amal')
    object_type = models.CharField(max_length=100, verbose_name='Obyekt turi')
    object_id = models.CharField(max_length=100, verbose_name='Obyekt ID')
    details = models.JSONField(default=dict, verbose_name='Tafsilotlar')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Audit jurnali'
        verbose_name_plural = 'Audit jurnallari'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f'{self.action} on {self.object_type}:{self.object_id} by {self.user}'
