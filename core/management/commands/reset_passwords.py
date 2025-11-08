from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import secrets
import string

class Command(BaseCommand):
    help = "Reset all user passwords with secure temporary passwords"

    def handle(self, *args, **kwargs):
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        for user in User.objects.all():
            # Generate a 12-character secure password
            new_password = ''.join(secrets.choice(chars) for _ in range(12))
            user.set_password(new_password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"User: {user.username} | New Password: {new_password}")
            )

        self.stdout.write(self.style.SUCCESS("✅ All user passwords have been reset successfully."))
