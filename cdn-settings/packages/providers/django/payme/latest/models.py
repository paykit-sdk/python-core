from django.db import models


class PaymeMerchant(models.Model):
    name = models.CharField(max_length=255)
    merchant_key = models.CharField(max_length=255, unique=True)
    merchant_secret = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.merchant_key})"

    @property
    def base64_key(self):
        import base64

        raw = f"Paycom:{self.merchant_secret}"
        return base64.b64encode(raw.encode()).decode()


class PaymeTransaction(models.Model):
    class TransactionState(models.IntegerChoices):
        PENDING = 1
        PERFORMED = 2
        CANCELLED = -1
        CANCELLED_AFTER_PERFORM = -2

    class CancelReason(models.IntegerChoices):
        RECEIVER_NOT_FOUND = 1
        DEBIT_FAILED = 2
        EXEC_FAILED = 3
        CANCELLED_BY_TIMEOUT = 4
        FUND_RETURNED = 5
        UNKNOWN = 10

    merchant = models.ForeignKey(
        PaymeMerchant,
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )

    payme_id = models.CharField(max_length=255, unique=True)
    payme_time = models.BigIntegerField()

    order_id = models.CharField(max_length=255)
    amount = models.BigIntegerField()

    state = models.IntegerField(
        choices=TransactionState.choices, default=TransactionState.PENDING.value
    )
    reason = models.IntegerField(choices=CancelReason.choices, null=True, blank=True)

    create_time = models.BigIntegerField(null=True, blank=True)
    perform_time = models.BigIntegerField(null=True, blank=True)
    cancel_time = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    extra = models.JSONField(default=dict)

    def __str__(self):
        return f"Transaction {self.payme_id} — {self.state}"


class PaymeReceipt(models.Model):
    transaction = models.OneToOneField(
        PaymeTransaction, on_delete=models.PROTECT, related_name="receipt"
    )

    receipt_id = models.CharField(max_length=255, unique=True)  # Payme's _id
    state = models.IntegerField()  # 0 created, 1 paid, 2 cancelled, 4 paid+fiscal
    type = models.IntegerField()  # 0 = debit, 1 = credit
    external_id = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    paid_at = models.BigIntegerField(null=True, blank=True)
    cancelled_at = models.BigIntegerField(null=True, blank=True)

    detail = models.JSONField(default=dict)


class PaymeSubscription(models.Model):
    class SubscriptionState(models.TextChoices):
        STATE_ACTIVE = "active"
        STATE_INACTIVE = "inactive"
        STATE_EXPIRED = "expired"
        STATE_CANCELLED = "cancelled"

    merchant = models.ForeignKey(
        PaymeMerchant,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    card_token = models.CharField(max_length=255)
    card_number = models.CharField(max_length=20, blank=True)
    amount = models.BigIntegerField(help_text="Amount in tiyins")
    order_id = models.CharField(max_length=255)
    state = models.CharField(
        max_length=20,
        choices=SubscriptionState.choices,
        default=SubscriptionState.STATE_INACTIVE.value,
    )
    next_payment_at = models.DateTimeField(null=True, blank=True)
    last_payment_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Subscription {self.order_id} — {self.state}"

    def is_active(self):
        return self.state == self.SubscriptionState.STATE_ACTIVE
