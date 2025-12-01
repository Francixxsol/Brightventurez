# create_superuser.py
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brightventurez.settings")
django.setup()

from django.contrib.auth.models import User

username = "Bright"
email = "anebisunday986@gmail.com"
password = "Lordhavemercy#1"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
