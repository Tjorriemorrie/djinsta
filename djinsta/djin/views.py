from django.contrib.auth import login, logout
from django.core.cache import cache
from django.shortcuts import render, redirect

from .tasks import my_profile
from .models import Account
from .instagram import Instagram


def index(request):
    context = {
        'accounts': Account.objects.filter(password__isnull=False).all(),
    }
    return render(request, 'djin/index.html', context)


def account_view(request, account_pk):
    account = Account.objects.get(pk=account_pk)
    context = {
        'account': account,
    }
    return render(request, 'djin/account.html', context)


def login_view(request, account_pk):
    """log in to instagram"""
    account = Account.objects.get(pk=account_pk)
    with Instagram(account) as insta:
        insta.login()
    return redirect('account', account.pk)


def process_view(request, account_pk):
    account = Account.objects.get(pk=account_pk)
    account.processing = not account.processing
    account.save()
    if account.processing:
        my_profile(account_pk)
    return redirect('account', account_pk)
