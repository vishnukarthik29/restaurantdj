### core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]


### accounts/urls.py

# from django.urls import path
# from . import views
# 
# urlpatterns = [
#     path('register/', views.register_view, name='register'),
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
#     path('profile/', views.profile_view, name='profile'),
#     path('notifications/', views.notifications_view, name='notifications'),
#     path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
#     path('notifications/unread-count/', views.get_unread_count, name='unread_count'),
# ]


### restaurants/urls.py

# from django.urls import path
# from . import views
# 
# urlpatterns = [
#     path('', views.RestaurantListView.as_view(), name='restaurant_list'),
#     path('<slug:slug>/', views.RestaurantDetailView.as_view(), name='restaurant_detail'),
#     path('api/availability/', views.check_availability, name='check_availability'),
#     path('api/time-slots/', views.get_time_slots, name='get_time_slots'),
#     path('<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
# ]


### reservations/urls.py

# from django.urls import path
# from . import views
# 
# urlpatterns = [
#     path('<slug:restaurant_slug>/book/', views.book_table, name='book_table'),
#     path('<slug:restaurant_slug>/confirm/', views.create_reservation, name='create_reservation'),
#     path('<str:reservation_id>/', views.reservation_detail, name='reservation_detail'),
#     path('<str:reservation_id>/confirmation/', views.reservation_confirmation, name='reservation_confirmation'),
#     path('<str:reservation_id>/cancel/', views.cancel_reservation, name='cancel_reservation'),
#     path('api/ai-recommend/', views.get_ai_recommendation, name='ai_recommendation'),
#     path('api/notifications/read-all/', views.mark_notifications_read, name='mark_all_read'),
# ]


### dashboard/urls.py

# from django.urls import path
# from . import views
# 
# urlpatterns = [
#     path('', views.customer_dashboard, name='customer_dashboard'),
#     path('history/', views.reservation_history, name='reservation_history'),
#     path('admin/', views.admin_dashboard, name='admin_dashboard'),
#     path('admin/restaurants/', views.admin_restaurants, name='admin_restaurants'),
#     path('admin/reservations/', views.admin_reservations, name='admin_reservations'),
#     path('admin/reservations/<str:reservation_id>/status/', views.admin_update_reservation_status, name='admin_update_status'),
#     path('admin/users/', views.admin_users, name='admin_users'),
#     path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
# ]
