from paykit.providers.payme.config import defaults


def generate_paylink(
    amount: int,  # in tiyin (1 UZS = 100 tiyin)
    id: int,
    merchant_key: str = None,
    callback_link: str = None,
    language: str = None,
    **kwargs,
) -> str:
    import base64

    resolved_language = language or defaults.language
    callback_url = callback_link or defaults.callback_link
    merchant = merchant_key or defaults.merchant_key

    tiyin = amount * 100

    if not (merchant):
        raise ValueError("no merchant_key found in config or passed as param")

    params = f"m={merchant};ac.order_id={id};a={tiyin};l={resolved_language}"

    # Add dynamic ac. params from kwargs
    for key, value in kwargs.items():
        params += f";ac.{key}={value}"

    if callback_url:
        params += f";c={callback_url}"

    encoded = base64.b64encode(params.encode()).decode()

    # encoded = params
    return f"{defaults.request_link}/{encoded}"
