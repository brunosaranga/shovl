from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):
    tos_agreed = models.BooleanField(default=False)
    tos_agreed_at = models.DateTimeField(null=True, blank=True)