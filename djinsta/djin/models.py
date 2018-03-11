from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    insta_cookies = models.TextField(max_length=1000, null=True)
    insta_password = models.TextField(max_length=250, null=True)
    insta_tag = models.CharField(max_length=30, null=True)

    def __str__(self):
        return f'Profile {self.user.username} #{self.insta_tag}'
