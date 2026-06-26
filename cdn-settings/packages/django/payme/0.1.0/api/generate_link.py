from paykit.providers.payme.config import defaults


def generate_paylink(
    amount: int,  # in tiyin (1 UZS = 100 tiyin)
    merchant: "str | PaymeMerchant | None" = None,
    callback_link: str = None,
    language: str = None,
    **kwargs,
) -> str:
    import base64

    from paykit.providers.payme.models import PaymeMerchant

    resolved_language = language or defaults.language
    callback_url = callback_link or defaults.callback_link

    if merchant is None:
        obj = PaymeMerchant.objects.filter(is_enabled=True).first()
        if not obj:
            raise ValueError("No active merchant found in DB")
        merchant_key = obj.merchant_key
    elif isinstance(merchant, str):
        obj = PaymeMerchant.objects.filter(name=merchant, is_enabled=True).first()
        if not obj:
            raise ValueError(f"No active merchant found with name '{merchant}'")
        merchant_key = obj.merchant_key
    elif isinstance(merchant, PaymeMerchant):
        merchant_key = merchant.merchant_key
    else:
        raise TypeError("merchant must be a str, PaymeMerchant instance, or None")

    if not merchant_key:
        raise ValueError("No merchant_key found")

    tiyin = amount * 100
    params = f"m={merchant_key};a={tiyin};l={resolved_language}"

    for key, value in kwargs.items():
        params += f";ac.{key}={value}"

    if callback_url:
        params += f";c={callback_url}"

    encoded = base64.b64encode(params.encode()).decode()
    return f"{defaults.request_link}/{encoded}"
