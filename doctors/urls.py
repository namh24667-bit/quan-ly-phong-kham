from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),
    path('create/', views.doctor_create, name='create'),
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/update/', views.schedule_update, name='schedule_update'),
    path('schedules/<int:pk>/deactivate/', views.schedule_deactivate,
         name='schedule_deactivate'),
    path('<int:pk>/', views.doctor_detail, name='detail'),
    path('<int:pk>/update/', views.doctor_update, name='update'),
    path('<int:pk>/delete/', views.doctor_delete, name='delete'),
]
