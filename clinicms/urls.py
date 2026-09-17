from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from appointments.views import create_medical_record

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('appointments/', include('appointments.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('medical-records/create/', create_medical_record, name='medical_record_create'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]
