from django.urls import path
from . import views

app_name = 'userSettings'

urlpatterns = [
    # Settings page (GET = show, POST = update via AJAX)
    path('',            views.settings_view,         name='settings'),
    # Public endpoint — currency list (same as DRF AllowAny)
    path('currencies/', views.currency_options_view, name='currencies'),
]

# ── URL Reference ──────────────────────────────────────────
# /user-settings/            → GET: Settings page | POST: Update (AJAX)
# /user-settings/currencies/ → GET: Currency options JSON (public)