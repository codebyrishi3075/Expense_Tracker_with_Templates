from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('expenses/', include('expenses.urls')),
    path('budget/', include('budget.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('contact_app/', include('contact_app.urls')),
    path('userSettings/', include('userSettings.urls')),
]



from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
