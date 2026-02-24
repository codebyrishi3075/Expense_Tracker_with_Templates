from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard page
    path('', views.dashboard_view, name='home'),

    # AJAX endpoints (for charts & month switching)
    path('ajax/summary/',            views.dashboard_summary_ajax,   name='summary_ajax'),
    path('ajax/trends/',             views.spending_trends_ajax,      name='trends_ajax'),
    path('ajax/category-breakdown/', views.category_breakdown_ajax,   name='breakdown_ajax'),
]

# ── URL Reference ────────────────────────────────────────────
# /dashboard/                          → Main dashboard page
# /dashboard/ajax/summary/             → JSON summary (AJAX month switch)
# /dashboard/ajax/trends/              → JSON spending trends for Chart.js
# /dashboard/ajax/category-breakdown/  → JSON category pie chart data