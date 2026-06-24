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
