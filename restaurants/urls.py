from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.RestaurantListView.as_view(), name='restaurant_list'),
    path('api/availability/',             views.check_availability,          name='check_availability'),
    path('api/time-slots/',               views.get_time_slots,              name='get_time_slots'),
    path('<slug:slug>/favourite/',        views.toggle_favourite,            name='toggle_favourite'),
    path('<slug:slug>/',                  views.RestaurantDetailView.as_view(), name='restaurant_detail'),
]
