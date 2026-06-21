from django.db import models


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


class PaymeTransaction(models.Model):
    merchant_id = models.CharField(max_length=255, unique=True)
    merchant_key = models.CharField(max_length=255)

    payme_id = models.CharField(max_length=255, unique=True)
    payme_time = models.BigIntegerField()

    order_id = models.CharField(max_length=255)
    amount = models.BigIntegerField()

    state = models.IntegerField(
        choices=TransactionState.choices, default=TransactionState.PENDING
    )
    reason = models.IntegerField(choices=CancelReason.choices, null=True, blank=True)

    create_time = models.BigIntegerField(null=True, blank=True)
    perform_time = models.BigIntegerField(null=True, blank=True)
    cancel_time = models.BigIntegerField(null=True, blank=True)

    extra = models.JSONField(default=dict)

    class Meta:
        db_table = "payme_transactions"


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

    class Meta:
        db_table = "payme_receipts"
