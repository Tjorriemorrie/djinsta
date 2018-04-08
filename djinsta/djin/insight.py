import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver
from elasticsearch_dsl import connections, Index, DocType, Integer, Keyword, Date, Text

from .models import Account


logger = logging.getLogger(__name__)
connections.create_connection(hosts=['localhost'], timeout=5)


class InsightError(Exception):
    """exception for errors with insights"""


###############################################################################
# Account
###############################################################################

class AccountInsightError(InsightError):
    """an error with account index"""


account_ix = Index('account')
if not account_ix.exists():
    account_ix.create()


class AccountDoc(DocType):
    username = Keyword(required=True, store=True)
    posts_count = Integer(store=True)
    followers_count = Integer(store=True)
    following_count = Integer(store=True)
    bio = Text(store=True)
    website = Keyword(store=True)
    joined_at = Date(store=True)

    class Meta:
        index = 'account'

    def __str__(self):
        return f'AccountDoc {self.username}'


AccountDoc.init()


def index_account(account):
    """Upsert account document"""
    doc = AccountDoc(
        meta={'id': account.pk},
        username=account.username,
        posts_count=account.posts_count,
        followers_count=account.followers_count,
        following_count=account.following_count,
        bio=account.bio,
        website=account.website,
        joined_at=account.created_at,

        # location=KEYWORD(stored=True, lowercase=True, commas=True),
        # tags=KEYWORD(stored=True, lowercase=True),
        # description=TEXT(stored=True),
        # count=NUMERIC(stored=True),
        # kind=KEYWORD(stored=True, lowercase=True),
        # created_at=DATETIME(stored=True),
    )
    logger.info(f'Indexing {doc}')
    return doc.save()


# def save_account_post_agg(account):
#     """updates aggregated data from posts onto account doc"""
#     writer = AsyncWriter(account_ix)
#     writer.update_document(
#         pk=str(account.pk),
#     )
#     writer.commit()


@receiver(post_delete, sender=Account)
def remove_account(sender, instance, **kwargs):
    """delete account and all the posts"""
    account_doc = AccountDoc.get(instance.pk)
    account_doc.delete()
    # post_docs = Post


def get_account(account, **kwargs):
    """Get account doc"""
    return AccountDoc.get(account.pk, **kwargs)


###############################################################################
# Post
###############################################################################

post_ix = Index('post')
if not post_ix.exists():
    post_ix.create()


class PostDoc(DocType):
    account_id = Integer(store=True)
    code = Keyword(store=True)
    location = Keyword(store=True)
    tags = Keyword(store=True)
    description = Text(store=True)
    count = Integer(store=True)
    kind = Keyword(store=True)
    posted_at = Date(store=True)

    class Meta:
        index = 'post'

    def __str__(self):
        return f'PostDoc {self.account_id} - {self.posted_at:%-d %b %Y}'


PostDoc.init()


def index_post(post):
    doc = PostDoc(
        meta={'id': post.pk},
        account_id=post.account.pk,
        code=post.code,
        location=post.location.name.lower() if post.location else None,
        tags=[t.word.lower() for t in post.tags.all()],
        description=post.description,
        count=post.count,
        kind=post.kind,
        posted_at=post.created_at,
    )
    logger.info(f'Indexing {doc}')
    return doc.save()


# @receiver(post_delete, sender=Post)
# def delete_pst(sender, instance, **kwargs):
#     writer = AsyncWriter(post_ix)
#     writer.delete_by_term('pk', instance.pk)
#     writer.commit()
#
#
# def get_post(post):
#     """Get post record"""
#     with post_ix.searcher() as searcher:
#         return searcher.document(pk=str(post.pk))
