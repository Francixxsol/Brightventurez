from django.contrib.auth import get_user_model

User = get_user_model()

# Loop through all users
for user in User.objects.all():
    try:
        raw_password = user.password  # current value (plain text)
        
        # Skip if already hashed (Django hashes start with 'pbkdf2_')
        if raw_password.startswith("pbkdf2_"):
            continue
        
        user.set_password(raw_password)  # hashes the password
        user.save()
        print(f"Password for {user.username} hashed successfully.")
        
    except Exception as e:
        print(f"Could not update password for {user.username}: {e}")
