from django.contrib import admin
from django.urls import path, include
from proj_expense_tracker import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',          views.homepage, name='home'),
    path('accounts/', include('accounts.urls')),
    path('expenses/', include('expenses.urls')),
    path('budget/', include('budget.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('contact/', include('contact_app.urls')),
    path('user-settings/', include('userSettings.urls')),
]



from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
