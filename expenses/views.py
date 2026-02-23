from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import json

from .models import Expense
from budget.models import BudgetCategory
from accounts.decorators import jwt_required

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO


# ─────────────────────────────────────────────────────────────
# HELPER — Validate expense fields (replaces DRF Serializer)
# ─────────────────────────────────────────────────────────────
def validate_expense_data(data, user):
    """
    Manual validation — same rules as DRF ExpenseSerializer.
    Returns (cleaned_data dict, error string or None)
    """
    errors = {}

    # ── Amount ──────────────────────────────────────────────
    amount_raw = data.get('amount', '').strip()
    if not amount_raw:
        errors['amount'] = 'Amount is required.'
    else:
        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                errors['amount'] = 'Amount must be greater than zero.'
            elif amount > Decimal('9999999.99'):
                errors['amount'] = 'Amount exceeds maximum allowed value.'
        except InvalidOperation:
            errors['amount'] = 'Enter a valid amount.'

    # ── Date ────────────────────────────────────────────────
    date_raw = data.get('date', '').strip()
    if not date_raw:
        errors['date'] = 'Date is required.'
    else:
        try:
            expense_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
            if expense_date > date.today():
                errors['date'] = 'Expense date cannot be in the future.'
        except ValueError:
            errors['date'] = 'Invalid date format. Use YYYY-MM-DD.'

    # ── Category ────────────────────────────────────────────
    category_id = data.get('category', '').strip()
    category_obj = None
    if not category_id:
        errors['category'] = 'Category is required.'
    else:
        try:
            category_obj = BudgetCategory.objects.get(id=int(category_id), user=user)
        except (BudgetCategory.DoesNotExist, ValueError):
            errors['category'] = 'Invalid category selected.'

    # ── Notes ────────────────────────────────────────────────
    notes = data.get('notes', '').strip()
    if len(notes) > 255:
        errors['notes'] = 'Notes cannot exceed 255 characters.'

    # ── Expense Type ─────────────────────────────────────────
    expense_type = data.get('expense_type', 'variable').strip()
    if expense_type not in ['fixed', 'variable']:
        expense_type = 'variable'

    # ── is_recurring ─────────────────────────────────────────
    is_recurring = data.get('is_recurring') in ['on', 'true', 'True', True, '1']

    # ── due_date (optional) ───────────────────────────────────
    due_date_raw = data.get('due_date', '').strip()
    due_date_obj = None
    if due_date_raw:
        try:
            due_date_obj = datetime.strptime(due_date_raw, '%Y-%m-%d').date()
        except ValueError:
            errors['due_date'] = 'Invalid due date format.'

    # ── auto_pay ─────────────────────────────────────────────
    auto_pay = data.get('auto_pay') in ['on', 'true', 'True', True, '1']

    if errors:
        return None, errors

    cleaned = {
        'amount'       : amount,
        'date'         : expense_date,
        'category'     : category_obj,
        'notes'        : notes,
        'expense_type' : expense_type,
        'is_recurring' : is_recurring,
        'due_date'     : due_date_obj,
        'auto_pay'     : auto_pay,
    }
    return cleaned, None


# ─────────────────────────────────────────────────────────────
# HELPER — Expense to dict (replaces Serializer .data)
# ─────────────────────────────────────────────────────────────
def expense_to_dict(expense):
    return {
        'id'           : expense.id,
        'amount'       : str(expense.amount),
        'category_id'  : expense.category.id   if expense.category else None,
        'category_name': expense.category.name if expense.category else 'Uncategorized',
        'notes'        : expense.notes,
        'date'         : str(expense.date),
        'expense_type' : expense.expense_type,
        'is_recurring' : expense.is_recurring,
        'due_date'     : str(expense.due_date) if expense.due_date else None,
        'auto_pay'     : expense.auto_pay,
        'created_at'   : expense.created_at.strftime('%Y-%m-%d %H:%M'),
    }


# ─────────────────────────────────────────────────────────────
# HELPER — Pagination (same as DRF helper)
# ─────────────────────────────────────────────────────────────
def paginate_results(queryset, page_number, page_size=10):
    try:
        paginator = Paginator(queryset, page_size)
        page      = paginator.get_page(page_number)
        return page, paginator, None
    except Exception as e:
        return None, None, str(e)


# ═════════════════════════════════════════════════════════════
# LIST EXPENSES  (GET /expenses/)
# Supports: search, category filter, amount range, date range,
#           sorting, pagination — exact same as DRF
# ═════════════════════════════════════════════════════════════
@jwt_required
def list_expenses_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        user        = request.user
        expenses_qs = Expense.objects.filter(user=user).select_related('category')

        # ── Search ──────────────────────────────────────────
        search = request.GET.get('search', '').strip()
        if search:
            if len(search) > 255:
                return JsonResponse({'error': 'Search query too long (max 255 chars)'}, status=400)
            expenses_qs = expenses_qs.filter(
                Q(notes__icontains=search) |
                Q(category__name__icontains=search)
            )

        # ── Category filter ──────────────────────────────────
        category_id = request.GET.get('category', '').strip()
        if category_id:
            try:
                expenses_qs = expenses_qs.filter(category_id=int(category_id))
            except ValueError:
                return JsonResponse({'error': 'Category ID must be a valid integer.'}, status=400)

        # ── Amount range ─────────────────────────────────────
        amount_min = request.GET.get('amount_min', '').strip()
        amount_max = request.GET.get('amount_max', '').strip()
        if amount_min or amount_max:
            try:
                if amount_min and amount_max:
                    mn, mx = Decimal(amount_min), Decimal(amount_max)
                    if mn < 0 or mx < 0:
                        return JsonResponse({'error': 'Amount values must be positive.'}, status=400)
                    if mn > mx:
                        return JsonResponse({'error': 'Minimum amount must be less than maximum.'}, status=400)
                    expenses_qs = expenses_qs.filter(amount__gte=mn, amount__lte=mx)
                elif amount_min:
                    expenses_qs = expenses_qs.filter(amount__gte=Decimal(amount_min))
                elif amount_max:
                    expenses_qs = expenses_qs.filter(amount__lte=Decimal(amount_max))
            except InvalidOperation:
                return JsonResponse({'error': 'Invalid amount values.'}, status=400)

        # ── Date range ───────────────────────────────────────
        from_date = request.GET.get('from', '').strip()
        to_date   = request.GET.get('to',   '').strip()
        if from_date or to_date:
            if not from_date or not to_date:
                return JsonResponse({'error': 'Both "from" and "to" dates are required.'}, status=400)
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
                to_dt   = datetime.strptime(to_date,   '%Y-%m-%d').date()
                if from_dt > to_dt:
                    return JsonResponse({'error': 'Start date must be before or equal to end date.'}, status=400)
                expenses_qs = expenses_qs.filter(date__range=[from_dt, to_dt])
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        # ── Sorting ──────────────────────────────────────────
        sort_by       = request.GET.get('sort_by', '-date')
        allowed_sorts = ['date', '-date', 'amount', '-amount', 'created_at', '-created_at']
        expenses_qs   = expenses_qs.order_by(sort_by if sort_by in allowed_sorts else '-date')

        # ── Pagination ───────────────────────────────────────
        page_number = request.GET.get('page', 1)
        try:
            page_size = int(request.GET.get('page_size', 10))
            if page_size < 1 or page_size > 100:
                page_size = 10
        except ValueError:
            page_size = 10

        # ── Summary totals ───────────────────────────────────
        total_amount = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # AJAX request → return JSON (for dynamic filtering)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if not expenses_qs.exists():
                return JsonResponse({
                    'count': 0, 'num_pages': 0, 'current_page': 1,
                    'has_next': False, 'has_previous': False,
                    'total_amount': '0.00', 'data': []
                })

            page, paginator, error = paginate_results(expenses_qs, page_number, page_size)
            if error:
                return JsonResponse({'error': error}, status=400)

            return JsonResponse({
                'count'        : paginator.count,
                'num_pages'    : paginator.num_pages,
                'current_page' : page.number,
                'has_next'     : page.has_next(),
                'has_previous' : page.has_previous(),
                'page_size'    : page_size,
                'total_amount' : str(total_amount),
                'data'         : [expense_to_dict(e) for e in page],
            })

        # Normal page load → render template
        page, paginator, error = paginate_results(expenses_qs, page_number, page_size)
        categories = BudgetCategory.objects.filter(user=request.user).order_by('name')

        context = {
            'expenses'     : page,
            'paginator'    : paginator,
            'total_amount' : total_amount,
            'categories'   : categories,
            'search'       : search,
            'from_date'    : from_date,
            'to_date'      : to_date,
            'category_id'  : category_id,
            'sort_by'      : sort_by,
        }
        return render(request, 'expense/expense_list.html', context)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# ADD EXPENSE  (GET + POST /expenses/add/)
# ═════════════════════════════════════════════════════════════
@jwt_required
def add_expense_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        categories = BudgetCategory.objects.filter(user=request.user).order_by('name')
        return render(request, 'expense/expense_form.html', {
            'categories' : categories,
            'today'      : date.today().isoformat(),
            'action'     : 'Add',
        })

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_expense_data(request.POST, request.user)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            expense = Expense.objects.create(user=request.user, **cleaned)

            return JsonResponse({
                'success' : True,
                'message' : 'Expense added successfully!',
                'data'    : expense_to_dict(expense),
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# EDIT EXPENSE  (GET + POST /expenses/edit/<pk>/)
# ═════════════════════════════════════════════════════════════
@jwt_required
def edit_expense_view(request: HttpRequest, pk: int) -> HttpResponse:

    expense = Expense.objects.filter(pk=pk, user=request.user).first()
    if not expense:
        return JsonResponse({'error': 'Expense not found or permission denied.'}, status=404)

    if request.method == 'GET':
        categories = BudgetCategory.objects.filter(user=request.user).order_by('name')
        return render(request, 'expense/expense_form.html', {
            'expense'    : expense,
            'categories' : categories,
            'today'      : date.today().isoformat(),
            'action'     : 'Edit',
        })

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_expense_data(request.POST, request.user)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            for field, value in cleaned.items():
                setattr(expense, field, value)
            expense.save()

            return JsonResponse({
                'success' : True,
                'message' : 'Expense updated successfully!',
                'data'    : expense_to_dict(expense),
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# DELETE EXPENSE  (POST /expenses/delete/<pk>/)
# ═════════════════════════════════════════════════════════════
@jwt_required
def delete_expense_view(request: HttpRequest, pk: int) -> HttpResponse:

    if request.method == 'POST':
        expense = Expense.objects.filter(pk=pk, user=request.user).first()
        if not expense:
            return JsonResponse({'error': 'Expense not found or permission denied.'}, status=404)

        expense.delete()
        return JsonResponse({'success': True, 'message': 'Expense deleted successfully!'})

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# EXPENSE DETAIL  (GET /expenses/<pk>/)
# ═════════════════════════════════════════════════════════════
@jwt_required
def expense_detail_view(request: HttpRequest, pk: int) -> HttpResponse:

    expense = Expense.objects.filter(pk=pk, user=request.user).select_related('category').first()
    if not expense:
        return JsonResponse({'error': 'Expense not found.'}, status=404)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'data': expense_to_dict(expense)})

    return render(request, 'expense/expense_detail.html', {'expense': expense})


# ═════════════════════════════════════════════════════════════
# EXPORT PDF  (GET /expenses/export/pdf/)
# Exact same logic as DRF project
# ═════════════════════════════════════════════════════════════
@jwt_required
def export_expenses_pdf(request: HttpRequest) -> HttpResponse:

    user       = request.user
    from_param = request.GET.get('from')
    to_param   = request.GET.get('to')

    if from_param and to_param:
        try:
            start_date = date.fromisoformat(from_param)
            end_date   = date.fromisoformat(to_param)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    else:
        today      = date.today()
        start_date = date(today.year, today.month, 1)
        end_date   = today

    expenses = Expense.objects.filter(
        user       = user,
        date__range = [start_date, end_date]
    ).select_related('category').order_by('date')

    # ── Build PDF ────────────────────────────────────────────
    buffer = BytesIO()
    p      = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "FinPocket — Expense Report")

    y -= 22
    p.setFont("Helvetica", 10)
    p.setFillColorRGB(.4, .4, .4)
    p.drawString(50, y, f"Period: {start_date}  to  {end_date}   |   User: {user.email}")

    # Divider line
    y -= 12
    p.setStrokeColorRGB(.8, .8, .8)
    p.line(50, y, width - 50, y)

    # Column headers
    y -= 20
    p.setFont("Helvetica-Bold", 9)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(50,  y, "Date")
    p.drawString(130, y, "Category")
    p.drawString(280, y, "Type")
    p.drawString(350, y, "Amount (₹)")
    p.drawString(440, y, "Notes")

    y -= 5
    p.line(50, y, width - 50, y)

    # Rows
    total = Decimal('0')
    p.setFont("Helvetica", 9)

    for exp in expenses:
        if y < 60:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 9)

        y -= 16
        p.setFillColorRGB(0, 0, 0)
        p.drawString(50,  y, str(exp.date))
        p.drawString(130, y, (exp.category.name if exp.category else 'Uncategorized')[:22])
        p.drawString(280, y, exp.expense_type.capitalize())
        p.drawString(350, y, f"{exp.amount:,.2f}")
        p.drawString(440, y, (exp.notes or '')[:25])
        total += exp.amount

    # Total row
    y -= 20
    p.setStrokeColorRGB(.8, .8, .8)
    p.line(50, y, width - 50, y)
    y -= 16
    p.setFont("Helvetica-Bold", 10)
    p.drawString(280, y, "TOTAL")
    p.drawString(350, y, f"₹{total:,.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="expenses_{start_date}_to_{end_date}.pdf"'
    )
    return response