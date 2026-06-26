try:
    from django.apps import AppConfig

    class PaykitConfig(AppConfig):
        name = "paykit"

        def ready(self):
            _autodiscover_providers()

except ImportError:
    PaykitConfig = None


def _autodiscover_providers():
    import importlib
    import pkgutil

    from paykit import providers

    for _, name, _ in pkgutil.iter_modules(providers.__path__):
        importlib.import_module(f"paykit.providers.{name}")
