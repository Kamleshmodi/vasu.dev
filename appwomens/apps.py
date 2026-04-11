# appwomens/apps.py

from django.apps import AppConfig

class AppwomensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appwomens'

    def ready(self):
        import appwomens.signals
