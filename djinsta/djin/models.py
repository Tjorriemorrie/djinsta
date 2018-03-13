from django.db import models


class Account(models.Model):
    username = models.CharField(max_length=250)
    password = models.CharField(max_length=250, null=True)
    processing = models.BooleanField(default=False)
    cookies = models.TextField(max_length=1000, null=True, blank=True)
    tag = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f'{self.username}'
