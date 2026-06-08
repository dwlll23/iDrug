from django.db import models

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=32, unique=True)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'user'

class PDBURL(models.Model):
    pdb_id = models.CharField(max_length=32, unique=True)
    url = models.CharField(max_length=256)

    class Meta:
        db_table = 'pdb_url'
