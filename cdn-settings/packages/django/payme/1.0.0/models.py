"""
Django models for the Payme payment provider.

Covers merchants, transactions, receipts, and subscriptions.
All monetary values are stored in **tiyins** (1 UZS = 100 tiyins).
"""

from django.db import models


class PaymeMerchant(models.Model):
    """
    Represents a Payme merchant account.

    Each merchant holds its own credentials and can be linked
    to multiple transactions and subscriptions.

    Attributes:
        name: Human-readable merchant name.
        merchant_key: Payme merchant ID (unique).
        merchant_secret: Payme secret key used for Basic Auth.
        is_enabled: Whether this merchant is active.
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    name = models.CharField(max_length=255)
    merchant_key = models.CharField(max_length=255, unique=True)
    merchant_secret = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.merchant_key})"

    @property
    def base64_key(self) -> str:
        """
                Base64-encoded Basic Auth credential for Payme API requests.

                Returns:
                    Base64 string of ``Paycom:<merchant_secret>``.

                Example:
        ```python
                    merchant = PaymeMerchant.objects.get(pk=1)
                    headers = {"Authorization": f"Basic {merchant.base64_key}"}
        ```
        """
        import base64

        raw = f"Paycom:{self.merchant_secret}"
        return base64.b64encode(raw.encode()).decode()


class PaymeTransaction(models.Model):
    """
    Records a single Payme payment transaction.

    Tracks the full lifecycle from pending through performed or cancelled,
    including cancel reasons and timestamps from Payme's system.

    Attributes:
        merchant: The merchant this transaction belongs to.
        payme_id: Unique transaction ID assigned by Payme.
        payme_time: Transaction creation time from Payme (Unix ms).
        order_id: Your internal order identifier.
        amount: Payment amount in tiyins.
        state: Current transaction state (see ``TransactionState``).
        reason: Cancellation reason code (see ``CancelReason``), if applicable.
        create_time: Time transaction was created on Payme's side (Unix ms).
        perform_time: Time transaction was performed (Unix ms).
        cancel_time: Time transaction was cancelled (Unix ms).
        extra: Arbitrary extra data from Payme's response.
    """

    class TransactionState(models.IntegerChoices):
        """Payme transaction lifecycle states."""

        PENDING = 1, "Pending"
        PERFORMED = 2, "Performed"
        CANCELLED = -1, "Cancelled"
        CANCELLED_AFTER_PERFORM = -2, "Cancelled after perform"

    class CancelReason(models.IntegerChoices):
        """Payme-defined cancellation reason codes."""

        RECEIVER_NOT_FOUND = 1, "Receiver not found"
        DEBIT_FAILED = 2, "Debit failed"
        EXEC_FAILED = 3, "Execution failed"
        CANCELLED_BY_TIMEOUT = 4, "Cancelled by timeout"
        FUND_RETURNED = 5, "Fund returned"
        UNKNOWN = 10, "Unknown"

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
    """
    Payme receipt linked one-to-one with a transaction.

    Stores the fiscal/receipt data returned by Payme after a transaction
    is performed or cancelled.

    Attributes:
        transaction: The related ``PaymeTransaction``.
        receipt_id: Payme's internal receipt ``_id``.
        state: Receipt state (0=created, 1=paid, 2=cancelled, 4=paid+fiscal).
        type: Receipt type (0=debit, 1=credit).
        external_id: Optional external reference ID.
        description: Human-readable receipt description.
        paid_at: Payment timestamp (Unix ms).
        cancelled_at: Cancellation timestamp (Unix ms).
        detail: Full receipt detail payload from Payme.
    """

    transaction = models.OneToOneField(
        PaymeTransaction, on_delete=models.PROTECT, related_name="receipt"
    )
    receipt_id = models.CharField(max_length=255, unique=True)
    state = models.IntegerField()
    type = models.IntegerField()
    external_id = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    paid_at = models.BigIntegerField(null=True, blank=True)
    cancelled_at = models.BigIntegerField(null=True, blank=True)
    detail = models.JSONField(default=dict)


class PaymeSubscription(models.Model):
    """
    Represents a recurring subscription charged via Payme card token.

    Subscriptions use a saved card token to charge the customer
    at a defined interval without redirecting to checkout.

    Attributes:
        merchant: The merchant managing this subscription.
        card_token: Payme card token for recurring charges.
        card_number: Masked card number for display (e.g. ``"**** 1234"``).
        amount: Charge amount in tiyins.
        order_id: Your internal order/subscription identifier.
        state: Current subscription state (see ``SubscriptionState``).
        next_payment_at: Scheduled datetime for the next charge.
        last_payment_at: Datetime of the most recent successful charge.
    """

    class SubscriptionState(models.TextChoices):
        """Subscription lifecycle states."""

        STATE_ACTIVE = "active", "Active"
        STATE_INACTIVE = "inactive", "Inactive"
        STATE_EXPIRED = "expired", "Expired"
        STATE_CANCELLED = "cancelled", "Cancelled"

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

    def is_active(self) -> bool:
        """
        Check whether the subscription is currently active.

        Returns:
            ``True`` if state is ``active``, ``False`` otherwise.
        """
        return self.state == self.SubscriptionState.STATE_ACTIVE
