from django.apps import AppConfig

class AppmensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appmens'

    def ready(self):
        import appmens.signals
