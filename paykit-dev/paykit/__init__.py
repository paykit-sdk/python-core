"""
PayKit - Payment provider integration toolkit
"""

__version__ = "1.0.0"
__author__ = "Abror Kodirov"
__email__ = "splayerme@gmail.com"

from paykit.core.config import Config
from paykit.core.fetcher import ProviderFetcher

# from paykit.core.loader import ProviderLoader

# __all__ = ["Config", "ProviderFetcher", "ProviderLoader", "__version__"]

__all__ = ["Config", "ProviderFetcher", "__version__"]
