from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        # سجل السيجنالات عند بدء التشغيل
        import users.signals  # noqa