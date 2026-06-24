from django.contrib import admin

from paykit.providers.payme.models import (
    PaymeMerchant,
    PaymeSubscription,
    PaymeTransaction,
)


@admin.register(PaymeMerchant)
class PaymeMerchantAdmin(admin.ModelAdmin):
    list_display = ("name", "merchant_key", "is_enabled", "created_at")
    list_filter = ("is_enabled",)
    search_fields = ("name", "merchant_key")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "payme_id",  # Payme's transaction identifier
        "order_id",
        "amount",
        "state",
        "merchant",
        "created_at",
    )
    list_filter = ("state", "merchant")
    search_fields = ("payme_id", "order_id")
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
