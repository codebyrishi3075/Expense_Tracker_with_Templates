from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse

from .models import ContactMessage
from accounts.decorators import jwt_required


# ─────────────────────────────────────────────────────────────
# HELPER — Validate contact form (replaces DRF Serializer)
# ─────────────────────────────────────────────────────────────
def validate_contact_data(data):
    """Same rules as ContactMessageSerializer."""
    errors = {}

    full_name = data.get('full_name', '').strip()
    if not full_name:
        errors['full_name'] = 'Full name is required.'
    elif len(full_name) > 255:
        errors['full_name'] = 'Name cannot exceed 255 characters.'

    email = data.get('email', '').strip()
    if not email:
        errors['email'] = 'Email is required.'
    elif '@' not in email or '.' not in email.split('@')[-1]:
        errors['email'] = 'Enter a valid email address.'

    subject = data.get('subject', '').strip()
    if not subject:
        errors['subject'] = 'Subject is required.'
    elif len(subject) > 255:
        errors['subject'] = 'Subject cannot exceed 255 characters.'

    message = data.get('message', '').strip()
    if not message:
        errors['message'] = 'Message is required.'
    elif len(message) < 10:
        # Same rule as DRF serializer
        errors['message'] = 'Message must be at least 10 characters.'

    if errors:
        return None, errors

    return {
        'full_name': full_name,
        'email'    : email,
        'subject'  : subject,
        'message'  : message,
    }, None


# ─────────────────────────────────────────────────────────────
# HELPER — Get client IP (same as DRF get_client_ip)
# ─────────────────────────────────────────────────────────────
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ═════════════════════════════════════════════════════════════
# CONTACT PAGE  (GET + POST /contact/)
# Public — no login required (same as DRF authentication_classes=[])
# ═════════════════════════════════════════════════════════════
def contact_view(request: HttpRequest) -> HttpResponse:

    # Pre-fill name/email if user is logged in
    prefill = {}
    if request.user.is_authenticated:
        prefill = {
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip()
                         or request.user.username,
            'email'    : request.user.email,
        }

    if request.method == 'GET':
        return render(request, 'contact_app/contact.html', {'prefill': prefill})

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_contact_data(request.POST)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            ContactMessage.objects.create(
                **cleaned,
                ip_address = get_client_ip(request),
                user_agent = request.META.get('HTTP_USER_AGENT', ''),
            )

            return JsonResponse({
                'success': True,
                'message': 'Your message has been sent successfully! We\'ll get back to you soon.',
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)