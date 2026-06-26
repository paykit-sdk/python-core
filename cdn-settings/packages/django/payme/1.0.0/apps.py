from django.apps import AppConfig


class PaymeConfig(AppConfig):
    name = "paykit.providers.payme"
    label = "payme"
    verbose_name = "Payme"
    default_auto_field = "django.db.models.BigAutoField"
