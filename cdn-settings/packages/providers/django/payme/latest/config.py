from collections import namedtuple

fields = [
    "request_link",
    "merchant_key",
    "merchant_secret",
    "language",
    "callback_link",
]

request_link = "test.paycom.uz"
merchant_key = ""
merchant_secret = ""
language = "ru"
callback_link = ""

config_type = namedtuple("config_type", fields)
defaults = config_type(
    request_link, merchant_key, merchant_secret, language, callback_link
)
