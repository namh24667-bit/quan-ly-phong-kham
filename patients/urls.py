from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='list'),
    path('create/', views.patient_create, name='create'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/update/', views.patient_update, name='update'),
    path('<int:pk>/delete/', views.patient_delete, name='delete'),
]
