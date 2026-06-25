# paykit — Payme Integration for Django

A Django integration for Payme (Uzbekistan payment gateway) supporting payment link generation, merchant webhook handling, and transaction lifecycle callbacks.


---

## Django Settings

Add the app and configure your Payme credentials:

```python
INSTALLED_APPS = [
    ...
    "paykit",
]
```
---

## Migrations

```bash
python manage.py migrate
```

---

## URL Configuration

```python
# urls.py
from django.contrib import admin
from django.urls import path
from yourapp.views import pay_link, MerchantAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("generate_url/", pay_link),
    path("payme_endpoint/", MerchantAPIView.as_view(), name="payme_merchant"),
]
```

---

## Generating a Payment Link

```python
from paykit.providers.payme import generate_paylink

# Minimal: uses first active merchant from DB
link = generate_paylink(amount=200)  # amount in UZS (converted to tiyin internally)

# With extra account params (e.g. order or account ID)
link = generate_paylink(amount=200, account=42)

# With specific merchant (by name or PaymeMerchant instance)
link = generate_paylink(amount=200, merchant="my_merchant")
```

> **Note:** `amount` is in **UZS**. The library multiplies by 100 internally to convert to tiyin.

---

## Merchant Webhook View

Subclass `MerchantAPIViewRaw` and override the three lifecycle hooks:

```python
from paykit.providers.payme.models import PaymeMerchant, PaymeTransaction
from paykit.providers.payme.views import MerchantAPIViewRaw

class MerchantAPIView(MerchantAPIViewRaw):

    def check_order(self, merchant, order_id, amount) -> bool:
        """
        Called before a transaction is created.
        Return True to allow, False to deny.

        For order-based payments:
            return Order.objects.filter(id=order_id, amount=amount).exists()

        For account top-ups:
            return Account.objects.filter(user_id=order_id).exists()
        """
        return True

    def on_payment(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        """Called when payment is successfully completed."""
        # order = Order.objects.get(id=tx.order_id)
        # order.is_paid = True
        # order.save()
        return super().on_payment(merchant, tx)

    def on_cancelled(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        """Called when a transaction is cancelled before completion."""
        return super().on_cancelled(merchant, tx)

    def on_cancelled_after_perform(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        """Called when a transaction is cancelled after funds were received (refund scenario)."""
        return super().on_cancelled_after_perform(merchant, tx)
```

---

## Admin
> Get your `MERCHANT_KEY` from [Payme Business](https://business.payme.uz).

`PaymeMerchant` and `PaymeTransaction` models are registered in Django Admin automatically. Add merchants there and set `is_enabled = True`.

---

## Use Cases

| Scenario | `check_order` filter | `on_payment` action |
|---|---|---|
| Account top-up | `Account.objects.filter(user_id=order_id)` | `account.balance += tx.amount` |
| Order payment | `Order.objects.filter(id=order_id, amount=amount)` | `order.is_paid = True` |
| Subscription | custom | activate plan |

---

## Notes

- Payme sends requests to your `payme_endpoint/` — this URL must be publicly accessible (use ngrok for local dev).
- Register this endpoint in your [Payme Business](https://business.payme.uz) dashboard under merchant settings.
- For test mode, use the Payme test checkout URL and test credentials.
