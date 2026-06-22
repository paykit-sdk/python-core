import base64
import time

from paykit.providers.payme import config
from paykit.providers.payme.models import PaymeMerchant


def get_active_merchant(merchant_id=None):
    """
    Resolve a PaymeMerchant instance.
    If merchant_id given — look it up from DB.
    If not — fall back to config (single-merchant mode).
    """
    if merchant_id:
        try:
            return PaymeMerchant.objects.get(merchant_id=merchant_id, is_enabled=True)
        except PaymeMerchant.DoesNotExist:
            return None

    # single-merchant fallback from config/paykit.json
    mid = config.PAYME_MERCHANT_ID()
    if not mid:
        return None
    merchant, _ = PaymeMerchant.objects.get_or_create(
        merchant_id=mid,
        defaults={
            "name": "Default",
            "secret_key": config.PAYME_SECRET_KEY(),
            "test_mode": config.PAYME_TEST_MODE(),
            "is_enabled": True,
        },
    )
    return merchant


def check_auth_header(request, merchant=None):
    """
    Validates Basic auth header against merchant secret key.
    Returns (True, merchant) or (False, None).
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Basic "):
        return False, None

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        _, key = decoded.split(":", 1)
    except Exception:
        return False, None

    # multi-merchant: match any enabled merchant
    if merchant is None:
        try:
            merchant = PaymeMerchant.objects.get(secret_key=key, is_enabled=True)
            return True, merchant
        except PaymeMerchant.DoesNotExist:
            # also check test key
            test_key = config.PAYME_TEST_SECRET_KEY()
            if test_key and key == test_key:
                return True, None
            return False, None

    # single merchant passed in
    expected = merchant.secret_key
    if config.PAYME_TEST_MODE() and config.PAYME_TEST_SECRET_KEY():
        expected = config.PAYME_TEST_SECRET_KEY()

    return key == expected, merchant


def now_ms():
    return int(time.time() * 1000)


def get_account_model():
    from django.apps import apps

    model_path = config.PAYME_ACCOUNT_MODEL()
    if not model_path:
        return None
    app_label, model_name = model_path.rsplit(".", 1)
    return apps.get_model(app_label, model_name)


def get_order(account_value):
    model = get_account_model()
    if model is None:
        return None
    field = config.PAYME_ACCOUNT_FIELD()
    try:
        return model.objects.get(**{field: account_value})
    except model.DoesNotExist:
        return None
