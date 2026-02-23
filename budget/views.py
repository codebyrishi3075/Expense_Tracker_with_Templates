from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from .models import BudgetCategory, Budget
from expenses.models import Expense
from accounts.decorators import jwt_required


# ─────────────────────────────────────────────────────────────
# HELPERS — Validation (replaces DRF Serializers)
# ─────────────────────────────────────────────────────────────
def validate_category_name(name, user, exclude_pk=None):
    """Same rules as BudgetCategorySerializer."""
    errors = {}
    if not name or not name.strip():
        errors['name'] = 'Category name cannot be empty.'
    elif len(name) > 100:
        errors['name'] = 'Category name cannot exceed 100 characters.'
    else:
        qs = BudgetCategory.objects.filter(user=user, name__iexact=name.strip())
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if qs.exists():
            errors['name'] = 'A category with this name already exists.'
    return name.strip() if not errors else None, errors


def validate_budget_data(data, user):
    """Same rules as BudgetSerializer."""
    errors = {}

    # ── Amount ──────────────────────────────────────────────
    amount_raw = data.get('amount', '').strip()
    if not amount_raw:
        errors['amount'] = 'Amount is required.'
    else:
        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                errors['amount'] = 'Budget amount must be greater than zero.'
            elif amount > Decimal('9999999.99'):
                errors['amount'] = 'Budget amount exceeds maximum allowed value.'
        except InvalidOperation:
            errors['amount'] = 'Enter a valid amount.'

    # ── Month ────────────────────────────────────────────────
    month_raw = data.get('month', '').strip()
    if not month_raw:
        errors['month'] = 'Month is required.'
    else:
        try:
            # Accept YYYY-MM or YYYY-MM-DD
            if len(month_raw) == 7:
                month_raw = month_raw + '-01'
            month_date = datetime.strptime(month_raw, '%Y-%m-%d').date().replace(day=1)

            # Allow past 12 months and future 24 months (same as DRF)
            today      = date.today()
            month_obj  = date(month_date.year, month_date.month, 1)
            diff       = (month_obj.year - today.year) * 12 + (month_obj.month - today.month)
            if diff < -12:
                errors['month'] = 'Cannot create budgets older than 12 months.'
            elif diff > 24:
                errors['month'] = 'Cannot create budgets more than 24 months in the future.'
        except ValueError:
            errors['month'] = 'Invalid month format. Use YYYY-MM.'

    # ── Category ─────────────────────────────────────────────
    cat_id = data.get('category', '').strip()
    cat_obj = None
    if not cat_id:
        errors['category'] = 'Category is required.'
    else:
        try:
            cat_obj = BudgetCategory.objects.get(id=int(cat_id), user=user)
        except (BudgetCategory.DoesNotExist, ValueError):
            errors['category'] = 'Category not found or does not belong to you.'

    if errors:
        return None, errors

    return {
        'amount'  : amount,
        'month'   : month_date,
        'category': cat_obj,
    }, None


def category_to_dict(cat):
    return {'id': cat.id, 'name': cat.name, 'created_at': str(cat.created_at.date())}


def budget_to_dict(b):
    return {
        'id'           : b.id,
        'category_id'  : b.category.id,
        'category_name': b.category.name,
        'month'        : str(b.month),
        'amount'       : str(b.amount),
        'created_at'   : str(b.created_at.date()),
    }


# ═════════════════════════════════════════════════════════════
# CATEGORIES — LIST + ADD PAGE
# ═════════════════════════════════════════════════════════════
@jwt_required
def categories_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        cats = BudgetCategory.objects.filter(user=request.user).order_by('name')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'count': cats.count(),
                'data' : [category_to_dict(c) for c in cats]
            })

        return render(request, 'budget/categories.html', {
            'categories': cats,
            'count'     : cats.count(),
        })

    # POST — Create category
    elif request.method == 'POST':
        try:
            name_raw    = request.POST.get('name', '')
            clean_name, errors = validate_category_name(name_raw, request.user)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            cat = BudgetCategory.objects.create(user=request.user, name=clean_name)
            return JsonResponse({
                'success': True,
                'message': 'Category created successfully!',
                'data'   : category_to_dict(cat),
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# CATEGORY — EDIT
# ═════════════════════════════════════════════════════════════
@jwt_required
def edit_category_view(request: HttpRequest, pk: int) -> HttpResponse:

    cat = BudgetCategory.objects.filter(pk=pk, user=request.user).first()
    if not cat:
        return JsonResponse({'error': 'Category not found or permission denied.'}, status=404)

    if request.method == 'POST':
        try:
            name_raw    = request.POST.get('name', '')
            clean_name, errors = validate_category_name(name_raw, request.user, exclude_pk=pk)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            cat.name = clean_name
            cat.save()
            return JsonResponse({
                'success': True,
                'message': 'Category updated successfully!',
                'data'   : category_to_dict(cat),
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# CATEGORY — DELETE
# ═════════════════════════════════════════════════════════════
@jwt_required
def delete_category_view(request: HttpRequest, pk: int) -> HttpResponse:

    if request.method == 'POST':
        cat = BudgetCategory.objects.filter(pk=pk, user=request.user).first()
        if not cat:
            return JsonResponse({'error': 'Category not found or permission denied.'}, status=404)

        # Same check as DRF — cannot delete if budgets or expenses exist
        has_budgets  = Budget.objects.filter(category=cat).exists()
        has_expenses = Expense.objects.filter(category=cat).exists()

        if has_budgets or has_expenses:
            return JsonResponse({
                'error'  : 'Cannot delete category with existing budgets or expenses.',
                'details': {'has_budgets': has_budgets, 'has_expenses': has_expenses}
            }, status=400)

        cat.delete()
        return JsonResponse({'success': True, 'message': 'Category deleted successfully!'})

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# BUDGETS — LIST PAGE
# ═════════════════════════════════════════════════════════════
@jwt_required
def list_budgets_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        budgets_qs = Budget.objects.filter(user=request.user).select_related('category')

        # Filter by month
        month_param = request.GET.get('month', '').strip()
        if month_param:
            try:
                month_date = datetime.strptime(month_param + '-01', '%Y-%m-%d').date()
                budgets_qs = budgets_qs.filter(month=month_date)
            except ValueError:
                return JsonResponse({'error': 'Invalid month format. Use YYYY-MM.'}, status=400)

        # Filter by category
        cat_id = request.GET.get('category', '').strip()
        if cat_id:
            try:
                budgets_qs = budgets_qs.filter(category_id=int(cat_id))
            except ValueError:
                return JsonResponse({'error': 'Category ID must be a valid integer.'}, status=400)

        budgets_qs  = budgets_qs.order_by('-month', 'category__name')
        total_budget = budgets_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        categories   = BudgetCategory.objects.filter(user=request.user).order_by('name')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'count'       : budgets_qs.count(),
                'total_budget': str(total_budget),
                'data'        : [budget_to_dict(b) for b in budgets_qs],
            })

        return render(request, 'budget/budget_list.html', {
            'budgets'     : budgets_qs,
            'categories'  : categories,
            'total_budget': total_budget,
            'month_param' : month_param,
            'cat_id'      : cat_id,
        })

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# BUDGET — ADD
# ═════════════════════════════════════════════════════════════
@jwt_required
def add_budget_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        categories = BudgetCategory.objects.filter(user=request.user).order_by('name')
        # Default month = current month in YYYY-MM
        current_month = timezone.now().date().strftime('%Y-%m')
        return render(request, 'budget/budget_form.html', {
            'categories'   : categories,
            'current_month': current_month,
            'action'       : 'Add',
        })

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_budget_data(request.POST, request.user)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            # Duplicate check (same as DRF)
            if Budget.objects.filter(
                user     = request.user,
                category = cleaned['category'],
                month    = cleaned['month']
            ).exists():
                return JsonResponse({
                    'error': 'Budget already exists for this category and month.'
                }, status=400)

            budget = Budget.objects.create(user=request.user, **cleaned)
            return JsonResponse({
                'success': True,
                'message': 'Budget created successfully!',
                'data'   : budget_to_dict(budget),
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# BUDGET — EDIT
# ═════════════════════════════════════════════════════════════
@jwt_required
def edit_budget_view(request: HttpRequest, pk: int) -> HttpResponse:

    budget = Budget.objects.filter(pk=pk, user=request.user).select_related('category').first()
    if not budget:
        return JsonResponse({'error': 'Budget not found or permission denied.'}, status=404)

    if request.method == 'GET':
        categories = BudgetCategory.objects.filter(user=request.user).order_by('name')
        return render(request, 'budget/budget_form.html', {
            'budget'    : budget,
            'categories': categories,
            'action'    : 'Edit',
        })

    elif request.method == 'POST':
        try:
            cleaned, errors = validate_budget_data(request.POST, request.user)
            if errors:
                return JsonResponse({'error': errors}, status=400)

            # Duplicate check (exclude self)
            if Budget.objects.filter(
                user     = request.user,
                category = cleaned['category'],
                month    = cleaned['month']
            ).exclude(pk=pk).exists():
                return JsonResponse({
                    'error': 'Budget already exists for this category and month.'
                }, status=400)

            for field, val in cleaned.items():
                setattr(budget, field, val)
            budget.save()

            return JsonResponse({
                'success': True,
                'message': 'Budget updated successfully!',
                'data'   : budget_to_dict(budget),
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# BUDGET — DELETE
# ═════════════════════════════════════════════════════════════
@jwt_required
def delete_budget_view(request: HttpRequest, pk: int) -> HttpResponse:

    if request.method == 'POST':
        budget = Budget.objects.filter(pk=pk, user=request.user).first()
        if not budget:
            return JsonResponse({'error': 'Budget not found or permission denied.'}, status=404)

        budget.delete()
        return JsonResponse({'success': True, 'message': 'Budget deleted successfully!'})

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


# ═════════════════════════════════════════════════════════════
# BUDGET UTILIZATION — Exact same logic as DRF
# ═════════════════════════════════════════════════════════════
@jwt_required
def budget_utilization_view(request: HttpRequest) -> HttpResponse:

    if request.method == 'GET':
        user = request.user

        month_param = request.GET.get('month', '').strip()
        if month_param:
            try:
                target_month = datetime.strptime(month_param + '-01', '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid month format. Use YYYY-MM.'}, status=400)
        else:
            target_month = timezone.now().date().replace(day=1)

        budgets = Budget.objects.filter(
            user=user, month=target_month
        ).select_related('category')

        if not budgets.exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'message': 'No budgets found for this month.',
                    'month'  : target_month.strftime('%Y-%m'),
                    'data'   : []
                })
            return render(request, 'budget/utilization.html', {
                'target_month'    : target_month,
                'utilization_data': [],
                'summary'         : None,
            })

        utilization_data = []
        total_budget     = Decimal('0.00')
        total_spent      = Decimal('0.00')

        for budget in budgets:
            expenses = Expense.objects.filter(
                user           = user,
                category       = budget.category,
                date__year     = target_month.year,
                date__month    = target_month.month,
            )
            spent       = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            remaining   = budget.amount - spent
            util_pct    = round((spent / budget.amount) * 100, 2) if budget.amount > 0 else 0

            total_budget += budget.amount
            total_spent  += spent

            # Status same as DRF
            if util_pct >= 100:
                status_text = 'over_budget'
            elif util_pct >= 90:
                status_text = 'critical'
            elif util_pct >= 75:
                status_text = 'warning'
            else:
                status_text = 'good'

            utilization_data.append({
                'category_id'        : budget.category.id,
                'category_name'      : budget.category.name,
                'budget'             : budget.amount,
                'spent'              : spent,
                'remaining'          : remaining,
                'utilization_percent': util_pct,
                'status'             : status_text,
                'expense_count'      : expenses.count(),
            })

        # Sort by utilization % descending (same as DRF)
        utilization_data.sort(key=lambda x: x['utilization_percent'], reverse=True)

        overall_util = round((total_spent / total_budget) * 100, 2) if total_budget > 0 else 0

        summary = {
            'total_budget'      : total_budget,
            'total_spent'       : total_spent,
            'total_remaining'   : total_budget - total_spent,
            'overall_utilization': overall_util,
            'categories_count'  : len(utilization_data),
            'over_budget_count' : len([d for d in utilization_data if d['status'] == 'over_budget']),
            'critical_count'    : len([d for d in utilization_data if d['status'] == 'critical']),
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'month'     : target_month.strftime('%Y-%m'),
                'month_name': target_month.strftime('%B %Y'),
                'summary'   : {k: str(v) if isinstance(v, Decimal) else v for k, v in summary.items()},
                'data'      : [{**d, 'budget': str(d['budget']), 'spent': str(d['spent']),
                                'remaining': str(d['remaining'])} for d in utilization_data],
            })

        return render(request, 'budget/utilization.html', {
            'target_month'    : target_month,
            'utilization_data': utilization_data,
            'summary'         : summary,
            'month_param'     : target_month.strftime('%Y-%m'),
        })

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)