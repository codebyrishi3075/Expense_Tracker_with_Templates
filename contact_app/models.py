from django.db import models


class ContactMessage(models.Model):
    full_name   = models.CharField(max_length=255)
    email       = models.EmailField()
    subject     = models.CharField(max_length=255)
    message     = models.TextField()
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.email}"