from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('logout', views.logout_view, name='logout'),
    path('login/<int:user_pk>', views.login_view, name='login'),
    path('dashboard', views.dashboard, name='dashboard'),
]
