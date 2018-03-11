from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.shortcuts import render, redirect

from .instagram import Instagram


def index(request):
    User.objects.filter(groups__name__exact='instagram').all()
    context = {
        'users': User.objects.all(),
    }
    return render(request, 'djin/index.html', context)


def login_view(request, user_pk):
    user = User.objects.get(pk=user_pk)
    login(request, user)
    with Instagram(user) as insta:
        insta.login()
    return redirect('dashboard')


def logout_view(request):
    logout(request)
    browser = cache.get('browser')
    if browser:
        browser.delete_all_cookies()
        browser.quit()
    return redirect('index')


def dashboard(request):
    context = {
        'user': request.user,
    }
    return render(request, 'djin/dashboard.html', context)
