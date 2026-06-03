from django.urls import path
from . import views

urlpatterns = [
    path('register/',                           views.register_view,           name='register'),
    path('login/',                              views.login_view,              name='login'),
    path('logout/',                             views.logout_view,             name='logout'),
    path('profile/',                            views.profile_view,            name='profile'),
    path('change-password/',                    views.change_password_view,    name='change_password'),
    path('notifications/',                      views.notifications_view,      name='notifications'),
    path('notifications/<int:pk>/read/',        views.mark_notification_read,  name='mark_notification_read'),
    path('notifications/read-all/',             views.mark_all_read,           name='mark_all_read'),
]
