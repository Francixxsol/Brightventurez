from django.contrib.auth import get_user_model

User = get_user_model()

username = "Bright"
email = "anebisunday986@gmail.com"
password = "Lordhavemercy#1"

if not User.objects.filter(username=username).exists():
    user = User(username=username, email=email, is_staff=True, is_superuser=True)
    user.set_password(password)
    user.save()
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
