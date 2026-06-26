"""
PayKit - Payment provider integration toolkit
"""

import sys
from types import ModuleType

__version__ = "1.0.0"
__author__ = "Abror Kodirov"
__email__ = "splayerme@gmail.com"

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher

__all__ = ["Config", "ProviderFetcher", "__version__"]

try:
    import django

    class _PaykitModule(ModuleType):
        @property
        def apps(self):
            import pkgutil

            from paykit import providers

            result = ["paykit"]
            for _, name, _ in pkgutil.iter_modules(providers.__path__):
                result.append(f"paykit.providers.{name}")
            return result

    sys.modules[__name__].__class__ = _PaykitModule

except ImportError:
    pass
