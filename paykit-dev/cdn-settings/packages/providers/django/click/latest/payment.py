"""
ClickPayment — generates Click.uz payment URLs.

Click uses a simple GET redirect to their checkout page.
Docs: https://docs.click.uz/en/payment-api/
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .config import ClickConfig

CLICK_CHECKOUT_BASE = "https://my.click.uz/services/pay"


@dataclass
class ClickPayment:
    """
    Represents a payment request for Click.uz checkout.

    Usage:
        payment = ClickPayment(
            amount=15_000,                     # UZS (Click uses full sum, not tiyin)
            merchant_trans_id="order-42",      # your order identifier
            config=ClickConfig(),
        )
        url = payment.checkout_url()           # redirect user here
        data = payment.checkout_data()         # all fields for template/JS
    """

    amount:            float             # UZS (NOT tiyin — Click takes sum directly)
    merchant_trans_id: str               # your order/transaction ID
    config:            ClickConfig = field(default_factory=ClickConfig)
    return_url:        Optional[str] = None
    lang:              str = "uz"        # uz | ru | en

    def __post_init__(self):
        self.config.validate()
        if self.amount <= 0:
            raise ValueError("amount must be > 0")
        if not self.merchant_trans_id:
            raise ValueError("merchant_trans_id is required")

    # ── Public API ────────────────────────────────────────────────────────

    def to_params(self) -> Dict[str, Any]:
        params = {
            "service_id":         self.config.service_id,
            "merchant_id":        self.config.merchant_id,
            "amount":             self.amount,
            "transaction_param":  self.merchant_trans_id,
            "lang":               self.lang,
        }
        if self.return_url:
            params["return_url"] = self.return_url
        return {k: v for k, v in params.items() if v is not None}

    def checkout_url(self) -> str:
        from urllib.parse import urlencode
        return f"{CLICK_CHECKOUT_BASE}?{urlencode(self.to_params())}"

    checkout_link = checkout_url

    def checkout_data(self) -> Dict[str, Any]:
        return {
            "url":                self.checkout_url(),
            "params":             self.to_params(),
            "amount":             self.amount,
            "merchant_trans_id":  self.merchant_trans_id,
            "lang":               self.lang,
        }
