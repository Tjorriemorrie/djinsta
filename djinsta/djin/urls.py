from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('account/<int:account_pk>', views.account_view, name='account'),
    path('login/<int:account_pk>', views.login_view, name='login'),
    path('process/<int:account_pk>', views.process_view, name='process'),
]
