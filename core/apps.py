from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Create superuser if it doesn't exist
        from . import create_superuser

        # Fix existing users whose passwords were stored in plain text
        from . import fix_user_passwords


