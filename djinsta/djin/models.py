from django.db import models


class Account(models.Model):
    username = models.CharField(max_length=250, unique=True)
    password = models.CharField(max_length=250, null=True)
    processing = models.BooleanField(default=False, blank=True)
    cookies = models.TextField(max_length=1000, null=True, blank=True)

    bio = models.TextField(null=True, blank=True)
    website = models.CharField(max_length=250, null=True, blank=True)
    posts_count = models.IntegerField(null=True, blank=True)
    followers_count = models.IntegerField(null=True, blank=True)
    following_count = models.IntegerField(null=True, blank=True)

    # ignore
    tag = models.CharField(max_length=30, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.username} with {self.followers_count} followers'


class Tag(models.Model):
    word = models.CharField(max_length=250)


class Location(models.Model):
    code = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    minor = models.CharField(max_length=250)
    major = models.CharField(max_length=250)

    def parts(self):
        try:
            return [l.lower().strip() for l in self.name.split(',')]
        except ValueError:
            return []

    def save(self, *args, **kwargs):
        try:
            self.minor, self.major = [l.strip() for l in self.name.split(',')]
        except ValueError:
            self.minor = self.name

        super().save(*args, **kwargs)


class Post(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='posts')
    code = models.CharField(max_length=250)

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag)

    description = models.CharField(max_length=1000, null=True, blank=True)
    count = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=50, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Post {self.account.username} - {self.created_at:%-d %b %Y}'


class Media(models.Model):
    IMG = 'img'
    VID = 'vid'
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')

    kind = models.CharField(max_length=3)
    source = models.CharField(max_length=250)

    size = models.IntegerField(null=True, blank=True)
    poster = models.CharField(max_length=250, null=True, blank=True)
    extension = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['size']


class AccountHistory(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='histories')

    class Meta:
        verbose_name_plural = 'AccountHistories'
