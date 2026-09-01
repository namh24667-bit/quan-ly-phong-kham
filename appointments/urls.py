from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.appointment_list, name='list'),
    path('create/', views.appointment_create, name='create'),
    path('<int:pk>/', views.appointment_detail, name='detail'),
    path('<int:pk>/update/', views.appointment_update, name='update'),
    path('<int:pk>/confirm/', views.appointment_confirm, name='confirm'),
    path('<int:pk>/checkin/', views.appointment_checkin, name='checkin'),
    path('<int:pk>/done/', views.appointment_done, name='done'),
    path('<int:pk>/cancel/', views.appointment_cancel, name='cancel'),
    path('my-schedule/', views.my_schedule, name='my_schedule'),
]
