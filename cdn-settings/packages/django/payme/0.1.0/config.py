"""
Payme provider configuration.

Loads provider settings from the global paykit.json config,
falling back to hardcoded defaults if not set.

Attributes:
    request_link (str): Payme checkout URL.
    language (str): Default UI language (e.g. ``"uz"``, ``"ru"``, ``"en"``).
    callback_link (str): URL Payme redirects to after payment.

Example: paykit.json
```json
    {
        "framework": "django",
        "providers": {
            "payme": "latest"
        },
        "defaults": {
            "payme": {
                "request_link": "https://test.paycom.uz",
                "language": "uz",
                "callback_link": "https://men.uz/thanks"
            }
        }
    }
```

"""

from collections import namedtuple
from pathlib import Path

from paykit.core.config import config

fields = ("request_link", "language", "callback_link")
raw_defaults = {
    "request_link": "https://checkout.paycom.uz",
    "language": "ru",
    "callback_link": "https://hello.world",
}

provider_name = Path(__file__).resolve().parent.name
paykit = config.get_provider_defaults(provider_name)

ProviderConfig = namedtuple("ProviderConfig", fields)
defaults = ProviderConfig(**{k: paykit.get(k, raw_defaults[k]) for k in fields})

request_link, language, callback_link = defaults
