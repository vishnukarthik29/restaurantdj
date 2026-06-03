from django.urls import path
from . import views

urlpatterns = [
    path('api/ai-recommend/',                         views.get_ai_recommendation,      name='ai_recommendation'),
    path("ai-recommend/", views.ai_recommend, name="ai_recommend"),
    path('<slug:restaurant_slug>/book/',               views.book_table,                 name='book_table'),
    path('<slug:restaurant_slug>/confirm/',            views.create_reservation,         name='create_reservation'),
    path('<str:reservation_id>/confirmation/',         views.reservation_confirmation,   name='reservation_confirmation'),
    path('<str:reservation_id>/cancel/',               views.cancel_reservation,         name='cancel_reservation'),
    path('<str:reservation_id>/',                      views.reservation_detail,         name='reservation_detail'),
]
