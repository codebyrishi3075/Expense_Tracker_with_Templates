from django.urls import path
from . import views

app_name = 'contact_app'

urlpatterns = [
    path('', views.contact_view, name='contact'),
]

# ── URL Reference ──────────────────────────────────────────
# /contact/    → GET: Show contact form | POST: Submit (AJAX)