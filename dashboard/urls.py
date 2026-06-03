from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_dashboard, name='customer_dashboard'),
    path('history/', views.reservation_history, name='reservation_history'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/restaurants/', views.admin_restaurants, name='admin_restaurants'),
    path('admin/reservations/', views.admin_reservations, name='admin_reservations'),
    path('admin/reservations/<str:reservation_id>/status/', views.admin_update_reservation_status, name='admin_update_status'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
]
