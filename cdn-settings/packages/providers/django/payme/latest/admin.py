from django.contrib import admin

from paykit.providers.payme.models import (
    PaymeMerchant,
    PaymeSubscription,
    PaymeTransaction,
)


@admin.register(PaymeMerchant)
class PaymeMerchantAdmin(admin.ModelAdmin):
    list_display = ("name", "merchant_id", "is_enabled", "test_mode", "created_at")
    list_filter = ("is_enabled", "test_mode")
    search_fields = ("name", "merchant_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "order_id",
        "amount",
        "state",
        "merchant",
        "created_at",
    )
    list_filter = ("state", "merchant")
    search_fields = ("transaction_id", "order_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymeSubscription)
class PaymeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "card_number",
        "amount",
        "state",
        "merchant",
        "last_payment_at",
    )
    list_filter = ("state", "merchant")
    search_fields = ("order_id", "card_number", "card_token")
    readonly_fields = ("created_at", "updated_at")
