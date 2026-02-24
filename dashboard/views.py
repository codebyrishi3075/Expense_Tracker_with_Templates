"""
Dashboard Views - DRF to Templates Conversion
Expense Tracker & Budget Planner
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.db.models import Sum, Count, Avg, Min, Max, Q
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from expenses.models import Expense
from budget.models import Budget, BudgetCategory
from accounts.decorators import jwt_required


# ─────────────────────────────────────────────────────────────
# HELPER — expense to simple dict (replaces ExpenseSerializer)
# ─────────────────────────────────────────────────────────────
def expense_to_dict(e):
    return {
        'id'           : e.id,
        'amount'       : str(e.amount),
        'category_name': e.category.name if e.category else 'Uncategorized',
        'notes'        : e.notes,
        'date'         : str(e.date),
        'expense_type' : e.expense_type,
    }


# ═════════════════════════════════════════════════════════════
# MAIN DASHBOARD VIEW  (GET /dashboard/)
# Combines: summary + recent expenses + stats for template
# ═════════════════════════════════════════════════════════════
@jwt_required
def dashboard_view(request: HttpRequest) -> HttpResponse:

    user = request.user

    # ── Month param (same as DRF) ──────────────────────────
    month_param = request.GET.get('month', '').strip()
    if month_param:
        try:
            current_month = datetime.strptime(month_param, '%Y-%m').date().replace(day=1)
        except ValueError:
            current_month = timezone.now().date().replace(day=1)
    else:
        current_month = timezone.now().date().replace(day=1)

    previous_month = current_month - relativedelta(months=1)

    # ── Current month expenses ─────────────────────────────
    expenses = Expense.objects.filter(
        user        = user,
        date__year  = current_month.year,
        date__month = current_month.month
    ).select_related('category')

    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # ── Current month budgets ──────────────────────────────
    budgets = Budget.objects.filter(
        user  = user,
        month = current_month
    ).select_related('category')

    total_budget = budgets.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # ── Key metrics ────────────────────────────────────────
    remaining           = total_budget - total_expenses
    savings             = remaining if remaining > 0 else Decimal('0.00')
    utilization_percent = round((total_expenses / total_budget) * 100, 2) if total_budget > 0 else 0
    budget_status       = 'over_budget' if total_expenses > total_budget else 'on_track'

    # ── Category breakdown (same as DRF) ──────────────────
    categories_data = []
    for budget in budgets:
        spent = expenses.filter(category=budget.category).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        cat_remaining = budget.amount - spent
        cat_percent   = round((spent / budget.amount) * 100, 2) if budget.amount > 0 else 0

        categories_data.append({
            'category_id'  : budget.category.id,
            'category_name': budget.category.name,
            'budget'       : budget.amount,
            'spent'        : spent,
            'remaining'    : cat_remaining,
            'percentage'   : cat_percent,
            'status'       : 'over_budget' if spent > budget.amount else 'on_track',
        })

    categories_data.sort(key=lambda x: x['spent'], reverse=True)
    top_categories = categories_data[:5]

    # ── Recent expenses (last 10 — same as DRF) ───────────
    recent_expenses = expenses.order_by('-date', '-created_at')[:10]

    # ── Expense statistics (same as DRF expense_statistics) ─
    stats = expenses.aggregate(
        total      = Sum('amount'),
        count      = Count('id'),
        average    = Avg('amount'),
        max_amount = Max('amount'),
        min_amount = Min('amount'),
    )
    total_days  = (timezone.now().date() - current_month).days + 1
    avg_per_day = (stats['total'] / total_days) if (stats['total'] and total_days > 0) else Decimal('0.00')

    most_expensive_cat = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total').first()

    # ── Month comparison (same as DRF month_comparison) ───
    prev_expenses = Expense.objects.filter(
        user        = user,
        date__year  = previous_month.year,
        date__month = previous_month.month,
    )
    prev_total         = prev_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    month_diff         = total_expenses - prev_total
    month_pct_change   = round((month_diff / prev_total) * 100, 2) if prev_total > 0 else 0
    month_trend        = 'increased' if month_diff > 0 else 'decreased' if month_diff < 0 else 'same'

    # ── Budget adherence score (same as DRF budget_adherence) ─
    total_score    = 0
    category_scores = []
    for budget in budgets:
        spent = expenses.filter(category=budget.category).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        if spent == 0:
            score = 100
        elif spent <= budget.amount:
            score = int(100 - ((spent / budget.amount) * 50))
        else:
            over_pct = ((spent - budget.amount) / budget.amount) * 100
            score    = max(0, int(50 - over_pct))

        total_score += score
        category_scores.append({'category': budget.category.name, 'score': score, 'spent': spent})

    overall_score = int(total_score / budgets.count()) if budgets.count() > 0 else 0
    grade = 'A+' if overall_score >= 90 else 'A' if overall_score >= 80 else \
            'B'  if overall_score >= 70 else 'C' if overall_score >= 60 else 'D'

    # ── Spending trends — last 6 months (same as DRF) ─────
    today        = timezone.now().date()
    trends_data  = []
    for i in range(5, -1, -1):
        m_date    = today - relativedelta(months=i)
        m_start   = m_date.replace(day=1)
        m_expense = Expense.objects.filter(
            user=user, date__year=m_start.year, date__month=m_start.month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        m_budget  = Budget.objects.filter(
            user=user, month=m_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        trends_data.append({
            'period'    : m_start.strftime('%b %Y'),
            'month'     : m_start.strftime('%Y-%m'),
            'expenses'  : float(m_expense),
            'budget'    : float(m_budget),
            'difference': float(m_budget - m_expense),
        })

    # ── Context ───────────────────────────────────────────
    context = {
        'user'              : user,
        'current_month'     : current_month,
        'month_param'       : current_month.strftime('%Y-%m'),

        # Summary metrics
        'total_budget'      : total_budget,
        'total_expenses'    : total_expenses,
        'remaining'         : remaining,
        'savings'           : savings,
        'utilization_percent': utilization_percent,
        'budget_status'     : budget_status,
        'expense_count'     : expenses.count(),

        # Categories
        'categories_data'   : categories_data,
        'top_categories'    : top_categories,

        # Recent expenses
        'recent_expenses'   : recent_expenses,

        # Statistics
        'stats_total'       : stats['total'] or Decimal('0.00'),
        'stats_count'       : stats['count'] or 0,
        'stats_average'     : round(float(stats['average'] or 0), 2),
        'stats_max'         : stats['max_amount'] or Decimal('0.00'),
        'stats_min'         : stats['min_amount'] or Decimal('0.00'),
        'avg_per_day'       : round(float(avg_per_day), 2),
        'most_expensive_cat': most_expensive_cat,

        # Month comparison
        'prev_total'        : prev_total,
        'month_diff'        : month_diff,
        'month_pct_change'  : month_pct_change,
        'month_trend'       : month_trend,
        'previous_month'    : previous_month,

        # Budget adherence
        'overall_score'     : overall_score,
        'grade'             : grade,

        # Trends (JSON for charts)
        'trends_data'       : trends_data,
    }

    return render(request, 'dashboard/dashboard.html', context)


# ═════════════════════════════════════════════════════════════
# AJAX — Dashboard Summary JSON  (for AJAX refresh)
# ═════════════════════════════════════════════════════════════
@jwt_required
def dashboard_summary_ajax(request: HttpRequest) -> JsonResponse:
    """Returns JSON summary — used for month switcher AJAX refresh."""

    user        = request.user
    month_param = request.GET.get('month', '').strip()

    if month_param:
        try:
            current_month = datetime.strptime(month_param, '%Y-%m').date().replace(day=1)
        except ValueError:
            return JsonResponse({'error': 'Invalid month format. Use YYYY-MM.'}, status=400)
    else:
        current_month = timezone.now().date().replace(day=1)

    expenses     = Expense.objects.filter(user=user, date__year=current_month.year, date__month=current_month.month)
    budgets      = Budget.objects.filter(user=user, month=current_month).select_related('category')
    total_exp    = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_bud    = budgets.aggregate(total=Sum('amount'))['total']  or Decimal('0.00')
    remaining    = total_bud - total_exp
    util_pct     = round((total_exp / total_bud) * 100, 2) if total_bud > 0 else 0

    categories_data = []
    for b in budgets:
        spent = expenses.filter(category=b.category).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        categories_data.append({
            'category_name': b.category.name,
            'budget'       : str(b.amount),
            'spent'        : str(spent),
            'remaining'    : str(b.amount - spent),
            'percentage'   : round((spent / b.amount) * 100, 2) if b.amount > 0 else 0,
            'status'       : 'over_budget' if spent > b.amount else 'on_track',
        })

    recent = expenses.select_related('category').order_by('-date', '-created_at')[:10]

    return JsonResponse({
        'month'              : current_month.strftime('%Y-%m'),
        'month_name'         : current_month.strftime('%B %Y'),
        'total_budget'       : str(total_bud),
        'total_expenses'     : str(total_exp),
        'remaining'          : str(remaining),
        'utilization_percent': util_pct,
        'budget_status'      : 'over_budget' if total_exp > total_bud else 'on_track',
        'expense_count'      : expenses.count(),
        'categories'         : categories_data,
        'recent_expenses'    : [expense_to_dict(e) for e in recent],
    })


# ═════════════════════════════════════════════════════════════
# AJAX — Spending Trends  (for Chart.js line chart)
# ═════════════════════════════════════════════════════════════
@jwt_required
def spending_trends_ajax(request: HttpRequest) -> JsonResponse:
    """Same as DRF spending_trends — returns JSON for charts."""

    user   = request.user
    period = request.GET.get('period', 'monthly')
    today  = timezone.now().date()

    if period == 'monthly':
        months = int(request.GET.get('months', 6))
        if months < 1 or months > 24:
            months = 6

        trends_data = []
        for i in range(months - 1, -1, -1):
            m_date    = today - relativedelta(months=i)
            m_start   = m_date.replace(day=1)
            m_expense = Expense.objects.filter(
                user=user, date__year=m_start.year, date__month=m_start.month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            m_budget  = Budget.objects.filter(
                user=user, month=m_start
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            trends_data.append({
                'period'    : m_start.strftime('%b %Y'),
                'month'     : m_start.strftime('%Y-%m'),
                'expenses'  : float(m_expense),
                'budget'    : float(m_budget),
                'difference': float(m_budget - m_expense),
            })

        return JsonResponse({'period': 'monthly', 'data': trends_data})

    elif period == 'weekly':
        trends_data = []
        for i in range(7, -1, -1):
            w_start   = today - timedelta(weeks=i)
            w_end     = w_start + timedelta(days=6)
            w_expense = Expense.objects.filter(
                user=user, date__gte=w_start, date__lte=w_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            trends_data.append({
                'period'    : f"Week {w_start.strftime('%d %b')}",
                'week_start': w_start.isoformat(),
                'week_end'  : w_end.isoformat(),
                'expenses'  : float(w_expense),
            })

        return JsonResponse({'period': 'weekly', 'data': trends_data})

    return JsonResponse({'error': 'Invalid period. Use: weekly, monthly'}, status=400)


# ═════════════════════════════════════════════════════════════
# AJAX — Category Breakdown  (for Chart.js pie/donut chart)
# ═════════════════════════════════════════════════════════════
@jwt_required
def category_breakdown_ajax(request: HttpRequest) -> JsonResponse:
    """Same as DRF category_breakdown — returns JSON for charts."""

    user        = request.user
    month_param = request.GET.get('month', '').strip()

    if month_param:
        try:
            target_month = datetime.strptime(month_param, '%Y-%m').date().replace(day=1)
        except ValueError:
            return JsonResponse({'error': 'Invalid month format. Use YYYY-MM.'}, status=400)
    else:
        target_month = timezone.now().date().replace(day=1)

    categories  = BudgetCategory.objects.filter(user=user)
    breakdown   = []
    total_spent = Decimal('0.00')

    for cat in categories:
        spent = Expense.objects.filter(
            user=user, category=cat,
            date__year=target_month.year, date__month=target_month.month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_spent += spent

        budget = Budget.objects.filter(user=user, category=cat, month=target_month).first()
        if spent > 0:
            breakdown.append({
                'category_id'    : cat.id,
                'category_name'  : cat.name,
                'amount'         : float(spent),
                'budget'         : float(budget.amount) if budget else 0,
                'budget_percent' : round((spent / budget.amount) * 100, 2) if budget and budget.amount > 0 else 0,
            })

    for item in breakdown:
        item['percentage'] = round((item['amount'] / float(total_spent)) * 100, 2) if total_spent > 0 else 0

    breakdown.sort(key=lambda x: x['amount'], reverse=True)

    return JsonResponse({
        'month'      : target_month.strftime('%Y-%m'),
        'total_spent': float(total_spent),
        'data'       : breakdown,
    })