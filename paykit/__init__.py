"""
PayKit - Payment provider integration toolkit
"""

__version__ = "1.0.0"
__author__ = "Abror Kodirov"
__email__ = "splayerme@gmail.com"

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher

__all__ = ["Config", "ProviderFetcher", "__version__", "setup"]


# django specific stuff
def setup():
    """For non-Django frameworks."""
    from paykit.apps import _autodiscover_providers

    _autodiscover_providers()
