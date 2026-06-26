import logging
from datetime import datetime
from http import HTTPStatus
from typing import Callable, cast

from paykit.providers.payme.api.client import PaymeSubscribeClient
from paykit.providers.payme.api.errors import (
    PaymeError,
    error_response,
    success_response,
)
from paykit.providers.payme.models import (
    PaymeMerchant,
    PaymeSubscription,
)

logger = logging.getLogger(__name__)


class PaymeSubscribeAPI:
    """
    Subscribe API — card tokenisation + recurring charges.
    Merchant is resolved once at instantiation:
      - None        → first enabled merchant in DB
      - str         → merchant matched by name
      - PaymeMerchant → used directly
    """

    def __init__(
        self, merchant: PaymeMerchant | str | None = None, subscribe_client=None
    ):
        self.merchant = self._resolve_merchant(merchant)
        self.client = (
            subscribe_client if subscribe_client is not None else PaymeSubscribeClient()
        )

    # ── Merchant resolution ───────────────────────────────────────────────────

    @staticmethod
    def _resolve_merchant(merchant: PaymeMerchant | str | None) -> PaymeMerchant:
        if merchant is None:
            obj = PaymeMerchant.objects.filter(is_enabled=True).first()
            if not obj:
                raise ValueError("No active merchant found in DB")
            return obj

        if isinstance(merchant, str):
            obj = PaymeMerchant.objects.filter(name=merchant, is_enabled=True).first()
            if not obj:
                raise ValueError(f"No active merchant found with name '{merchant}'")
            return obj

        if isinstance(merchant, PaymeMerchant):
            return merchant

        raise TypeError(
            f"merchant must be None, str, or PaymeMerchant — got {type(merchant)}"
        )

    # ── Response builders ─────────────────────────────────────────────────────

    def _ok(self, result: dict, rpc_id) -> dict:
        return success_response(rpc_id, result)

    def _err(self, error: dict, rpc_id, data=None) -> dict:
        err = dict(error)
        if data is not None:
            err["data"] = data
        return error_response(rpc_id, err)

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def dispatch(self, body: dict) -> tuple[dict, int]:
        rpc_id = body.get("id")

        method_name = body.get("method", "").replace(".", "_")
        handler: Callable | None = getattr(self, f"_{method_name}", None)
        if handler is None or not callable(handler):
            return self._err(PaymeError.METHOD_NOT_FOUND, rpc_id), HTTPStatus.OK

        try:
            result = cast(dict, handler(body.get("params", {}), rpc_id))
            return result, HTTPStatus.OK
        except Exception as exc:
            logger.exception("Subscribe API error in '%s'", method_name)
            return self._err(PaymeError.SYSTEM_ERROR, rpc_id, str(exc)), HTTPStatus.OK

    # ── cards.create ──────────────────────────────────────────────────────────

    def _cards_create(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.cards_create(
                merchant=self.merchant,
                card_number=params["card"]["number"],
                card_expire=params["card"]["expire"],
                save=params.get("save", True),
            )
        except Exception as exc:
            logger.exception("cards.create failed")
            return self._err(
                PaymeError.SubscribeError.INVALID_CARD_NUMBER, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── cards.get_verify_code ─────────────────────────────────────────────────

    def _cards_get_verify_code(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.cards_get_verify_code(
                merchant=self.merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.get_verify_code failed")
            return self._err(
                PaymeError.SubscribeError.OtpError.OTP_SEND_ERROR, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── cards.verify ──────────────────────────────────────────────────────────

    def _cards_verify(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.cards_verify(
                merchant=self.merchant,
                token=params["token"],
                code=params["code"],
            )
        except Exception as exc:
            logger.exception("cards.verify failed")
            return self._err(
                PaymeError.SubscribeError.OtpError.OTP_INVALID_CODE, rpc_id, str(exc)
            )

        order_id = params.get("order_id")
        if order_id and result.get("card", {}).get("token"):
            PaymeSubscription.objects.update_or_create(
                merchant=self.merchant,
                order_id=order_id,
                defaults={
                    "card_token": result["card"]["token"],
                    "card_number": result["card"].get("number", ""),
                    "state": PaymeSubscription.SubscriptionState.STATE_ACTIVE,
                },
            )

        return self._ok(result, rpc_id)

    # ── cards.check ───────────────────────────────────────────────────────────

    def _cards_check(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.cards_check(
                merchant=self.merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.check failed")
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id, str(exc))

        return self._ok(result, rpc_id)

    # ── cards.remove ─────────────────────────────────────────────────────────

    def _cards_remove(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.cards_remove(
                merchant=self.merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.remove failed")
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id, str(exc))

        PaymeSubscription.objects.filter(
            merchant=self.merchant, card_token=params["token"]
        ).update(state=PaymeSubscription.SubscriptionState.STATE_CANCELLED)

        return self._ok(result, rpc_id)

    # ── receipts.create ───────────────────────────────────────────────────────

    def _receipts_create(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_create(
                merchant=self.merchant,
                amount=params["amount"],
                account=params["account"],
                description=params.get("description", ""),
            )
        except Exception as exc:
            logger.exception("receipts.create failed")
            return self._err(
                PaymeError.MerchantError.INCORRECT_AMOUNT, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.pay ─────────────────────────────────────────────────────────

    def _receipts_pay(self, params: dict, rpc_id) -> dict:
        receipt_id = params["id"]
        token = params.get("token")

        if not token:
            order_id = params.get("account", {}).get("order_id")
            if order_id:
                sub = PaymeSubscription.objects.filter(
                    merchant=self.merchant,
                    order_id=order_id,
                    state=PaymeSubscription.SubscriptionState.STATE_ACTIVE,
                ).first()
                if sub:
                    token = sub.card_token

        if not token:
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id)

        try:
            result = self.client.receipts_pay(
                merchant=self.merchant,
                receipt_id=receipt_id,
                token=token,
                payer=params.get("payer", {}),
            )
        except Exception as exc:
            logger.exception("receipts.pay failed")
            return self._err(
                PaymeError.SubscribeError.INSUFFICIENT_FUNDS, rpc_id, str(exc)
            )

        PaymeSubscription.objects.filter(
            merchant=self.merchant, card_token=token
        ).update(last_payment_at=datetime.now())

        return self._ok(result, rpc_id)

    # ── receipts.send ─────────────────────────────────────────────────────────

    def _receipts_send(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_send(
                merchant=self.merchant,
                receipt_id=params["id"],
                phone=params["phone"],
            )
        except Exception as exc:
            logger.exception("receipts.send failed")
            return self._err(
                PaymeError.SubscribeError.OtpError.OTP_SEND_ERROR, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.cancel ───────────────────────────────────────────────────────

    def _receipts_cancel(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_cancel(
                merchant=self.merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.cancel failed")
            return self._err(
                PaymeError.MerchantError.CANNOT_CANCEL_TRANSACTION, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.check ────────────────────────────────────────────────────────

    def _receipts_check(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_check(
                merchant=self.merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.check failed")
            return self._err(
                PaymeError.MerchantError.RECEIPTS_NOT_FOUND, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.get ─────────────────────────────────────────────────────────

    def _receipts_get(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_get(
                merchant=self.merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.get failed")
            return self._err(
                PaymeError.MerchantError.RECEIPTS_NOT_FOUND, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.get_all ──────────────────────────────────────────────────────

    def _receipts_get_all(self, params: dict, rpc_id) -> dict:
        try:
            result = self.client.receipts_get_all(
                merchant=self.merchant,
                count=params.get("count", 50),
                from_time=params.get("_from"),
                to_time=params.get("_to"),
                offset=params.get("offset", 0),
            )
        except Exception as exc:
            logger.exception("receipts.get_all failed")
            return self._err(
                PaymeError.MerchantError.RECEIPTS_NOT_FOUND, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)


# Module-level default instance — first enabled merchant
sapi = PaymeSubscribeAPI()
