from django.urls import path
from . import views

app_name = 'budget'

urlpatterns = [
    # ── Categories ────────────────────────────────────────────
    # List all + Add new (GET + POST)
    path('categories/',                views.categories_view,       name='categories'),
    # Edit category (POST only — AJAX)
    path('categories/edit/<int:pk>/',  views.edit_category_view,    name='edit_category'),
    # Delete category (POST only — AJAX)
    path('categories/delete/<int:pk>/', views.delete_category_view, name='delete_category'),

    # ── Budgets ───────────────────────────────────────────────
    # List budgets with month/category filter
    path('',                           views.list_budgets_view,     name='list'),
    # Add new budget
    path('add/',                       views.add_budget_view,       name='add'),
    # Edit budget
    path('edit/<int:pk>/',             views.edit_budget_view,      name='edit'),
    # Delete budget (POST — AJAX)
    path('delete/<int:pk>/',           views.delete_budget_view,    name='delete'),

    # ── Utilization ───────────────────────────────────────────
    path('utilization/',               views.budget_utilization_view, name='utilization'),
]

# ── URL Reference ─────────────────────────────────────────────
# /budget/                          → List all budgets
# /budget/add/                      → Add new budget
# /budget/edit/<id>/                → Edit budget
# /budget/delete/<id>/              → Delete budget (POST)
# /budget/categories/               → List + Add categories
# /budget/categories/edit/<id>/     → Edit category (POST/AJAX)
# /budget/categories/delete/<id>/   → Delete category (POST/AJAX)
# /budget/utilization/              → Budget vs Expense utilization