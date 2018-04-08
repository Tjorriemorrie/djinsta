import logging

from django.shortcuts import render, redirect

from .tasks import my_profile
from .models import Account
from .instagram import Instagram
from .insight import get_account, get_post, AccountSearch

logger = logging.getLogger(__name__)


def index(request):
    context = {
        'accounts': Account.objects.filter(password__isnull=False).all(),
    }
    return render(request, 'djin/index.html', context)


def account_view(request, account_pk):
    account = Account.objects.get(pk=account_pk)
    logger.info(f'Viewing account {account}')
    context = {
        'account': account,
        'account_doc': get_account(account, ignore=404),
        'account_agg': AccountSearch().execute(),
        'posts': [(p, get_post(p, ignore=404)) for p in account.posts.all()],
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
