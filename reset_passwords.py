from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Reset all user passwords"

    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            new_password = input(f"Enter new password for {user.username}: ")
            user.set_password(new_password)
            user.save()
            self.stdout.write(f"Password updated for {user.username}")
        self.stdout.write(self.style.SUCCESS("All user passwords updated successfully."))
