from django.db import models

# Create your models here.

class Account(models.Model):
    userName = models.CharField(max_length=255,unique=True,null=False,blank=False)
    email = models.EmailField(blank=False,null=False,unique=True)
    password = models.CharField(max_length=255,blank=False,null=False);
    eccPart1 = models.CharField(max_length=255)
    eccPart2 = models.CharField(max_length=255)
    eccPart3 = models.CharField(max_length=255)
    eccPart4 = models.CharField(max_length=255)

class LogIn(models.Model):
    email = models.EmailField(blank=False,null=False,unique=True)
    password = models.CharField(max_length=255,blank=False,null=False);
