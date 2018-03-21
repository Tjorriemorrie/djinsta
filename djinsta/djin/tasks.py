import wrapt
from background_task import background

from .instagram import Instagram
from .models import Account


@wrapt.decorator
def extract_account(wrapped, instance, args, kwargs):
    def _execute(account_pk, *_args, **_kwargs):
        account = Account.objects.get(pk=account_pk)
        if not account.processing:
            return
        return wrapped(account, *_args, **_kwargs)
    return _execute(*args, **kwargs)


@background
@extract_account
def my_profile(account):
    """parse my profile"""
    with Instagram(account) as insta:
        insta.upsert_profile()
        for post in account.posts.all():
            insta.upsert_post(post)
    finished(account.pk)


@background
@extract_account
def finished(account):
    """end processing for account"""
    account.processing = False
    account.save()


