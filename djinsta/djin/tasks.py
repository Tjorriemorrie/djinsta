import logging

import wrapt
from background_task import background

from .instagram import Instagram
from .models import Account, AccountHistory, PostHistory
from .insight import index_account, index_post

logger = logging.getLogger(__name__)


@wrapt.decorator
def extract_account(wrapped, instance, args, kwargs):
    def _execute(account_pk, *_args, **_kwargs):
        account = Account.objects.get(pk=account_pk)
        if not account.processing:
            return
        logger.info(f'Running task with account {account}')
        return wrapped(account, *_args, **_kwargs)
    return _execute(*args, **kwargs)


@background
@extract_account
def my_profile(account):
    """parse my profile"""
    logger.info(f'Running my profile for {account}')
    with Instagram(account) as insta:
        logger.info(f'Updating account {account}')
        insta.upsert_profile(account)
        for post in account.posts.all():
            logger.info(f'Updating post {post}')
            insta.upsert_post(post)
            PostHistory.upsert(post)
            index_post(post)

    AccountHistory.upsert(account)

    doc_created = index_account(account)
    logger.info(f'Created account doc? {doc_created}')

    finished(account.pk)


@background
@extract_account
def finished(account):
    """end processing for account"""
    account.processing = False
    account.save()
    logger.info(f'Account {account} finished processing')


