from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from decimal import Decimal, InvalidOperation

from .models import UserSettings
from accounts.decorators import jwt_required


# ─────────────────────────────────────────────────────────────
# HELPER — Validate settings (replaces DRF UserSettingsSerializer)
# ─────────────────────────────────────────────────────────────
def validate_settings_data(data):
    errors  = {}
    cleaned = {}

    # ── Currency ─────────────────────────────────────────────
    currency = data.get('currency', '').strip()
    valid_currencies = [c[0] for c in UserSettings.CURRENCY_CHOICES]
    if currency and currency not in valid_currencies:
        errors['currency'] = 'Invalid currency selected.'
    elif currency:
        cleaned['currency'] = currency

    # ── Monthly Budget Limit (optional) ──────────────────────
    limit_raw = data.get('monthly_budget_limit', '').strip()
    if limit_raw:
        try:
            limit = Decimal(limit_raw)
            if limit <= 0:
                errors['monthly_budget_limit'] = 'Budget limit must be greater than zero.'
            elif limit > Decimal('9999999.99'):
                errors['monthly_budget_limit'] = 'Budget limit is too large.'
            else:
                cleaned['monthly_budget_limit'] = limit
        except InvalidOperation:
            errors['monthly_budget_limit'] = 'Enter a valid amount.'
    else:
        # Empty = clear the limit
        cleaned['monthly_budget_limit'] = None

    if errors:
        return None, errors
    return cleaned, None


# ═════════════════════════════════════════════════════════════
# SETTINGS PAGE  (GET + POST /user-settings/)
# ═════════════════════════════════════════════════════════════
@jwt_required
def settings_view(request: HttpRequest) -> HttpResponse:

    # get_or_create — same as DRF (auto-creates settings for new users)
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return render(request, 'userSettings/settings.html', {
            'settings'   : settings_obj,
            'currencies' : UserSettings.CURRENCY_CHOICES,
        })

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_settings_data(request.POST)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            for field, value in cleaned.items():
                setattr(settings_obj, field, value)
            settings_obj.save()

            return JsonResponse({
                'success' : True,
                'message' : 'Settings updated successfully!',
                'data'    : {
                    'currency'            : settings_obj.currency,
                    'monthly_budget_limit': str(settings_obj.monthly_budget_limit or ''),
                }
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# AJAX — Get currency options (replaces DRF get_currency_options)
# Public — no login required (same as DRF AllowAny)
# ═════════════════════════════════════════════════════════════
def currency_options_view(request: HttpRequest) -> JsonResponse:
    currencies = [
        {'code': code, 'label': label}
        for code, label in UserSettings.CURRENCY_CHOICES
    ]
    return JsonResponse({
        'data' : currencies,
        'count': len(currencies),
    })