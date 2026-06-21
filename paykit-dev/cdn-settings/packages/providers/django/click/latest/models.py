from django.db import models


class ClickTransaction(models.Model):
    STATUS_CREATED   = "created"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_CREATED,   "Created"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    click_trans_id     = models.BigIntegerField(unique=True, db_index=True)
    service_id         = models.BigIntegerField()
    merchant_trans_id  = models.CharField(max_length=256, db_index=True)
    merchant_prepare_id = models.CharField(max_length=256, blank=True)
    amount             = models.DecimalField(max_digits=15, decimal_places=2)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED)
    error              = models.IntegerField(default=0)
    error_note         = models.CharField(max_length=512, blank=True)
    sign_time          = models.CharField(max_length=50, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "click_transactions"
        verbose_name        = "Click Transaction"
        verbose_name_plural = "Click Transactions"
        ordering            = ["-id"]

    def __str__(self):
        return f"Click#{self.click_trans_id}[{self.status}]"

    def confirm(self):
        self.status = self.STATUS_CONFIRMED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self, error: int = -9, note: str = "Cancelled"):
        self.status     = self.STATUS_CANCELLED
        self.error      = error
        self.error_note = note
        self.save(update_fields=["status", "error", "error_note", "updated_at"])
