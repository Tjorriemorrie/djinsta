from django.db import models


class Account(models.Model):
    username = models.CharField(max_length=250, unique=True)
    password = models.CharField(max_length=250, null=True)
    processing = models.BooleanField(default=False, blank=True)
    cookies = models.TextField(max_length=1000, null=True, blank=True)

    posts_count = models.IntegerField(null=True, blank=True)
    followers_count = models.IntegerField(null=True, blank=True)
    following_count = models.IntegerField(null=True, blank=True)

    tag = models.CharField(max_length=30, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.username} with {self.followers_count} followers'


class Post(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='posts')
    hash = models.CharField(max_length=250)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
