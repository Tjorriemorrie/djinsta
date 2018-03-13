from background_task import background

from .instagram import Instagram
from .models import Account


@background(schedule=1)
def my_profile(account_pk):
    account = Account.objects.get(pk=account_pk)
    with Instagram(account) as insta:
        insta.get_profile()
