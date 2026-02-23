from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # List all expenses (with search, filter, pagination)
    path('',                    views.list_expenses_view,   name='list'),

    # Add new expense
    path('add/',                views.add_expense_view,     name='add'),

    # Edit existing expense
    path('edit/<int:pk>/',      views.edit_expense_view,    name='edit'),

    # Delete expense
    path('delete/<int:pk>/',    views.delete_expense_view,  name='delete'),

    # Expense detail (AJAX or full page)
    path('<int:pk>/',           views.expense_detail_view,  name='detail'),

    # Export PDF (same as DRF)
    path('export/pdf/',         views.export_expenses_pdf,  name='export_pdf'),
]

# ── URL Reference ──────────────────────────────────────────
# /expenses/                   → List with filter/search/pagination
# /expenses/add/               → Add new expense form
# /expenses/edit/<id>/         → Edit expense form
# /expenses/delete/<id>/       → Delete expense (POST)
# /expenses/<id>/              → Detail view
# /expenses/export/pdf/        → Download PDF report