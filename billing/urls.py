from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('<int:pk>/', views.invoice_detail, name='detail'),
    path('<int:pk>/edit/', views.invoice_update, name='update'),
    path('<int:pk>/paid/', views.invoice_mark_paid, name='mark_paid'),
]
