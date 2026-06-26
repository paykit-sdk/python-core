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
from paykit.providers.payme.api.utils import _decode_basic
from paykit.providers.payme.models import (
    PaymeMerchant,
    PaymeSubscription,
)

logger = logging.getLogger(__name__)


class PaymeSubscribeAPI:
    """
    Subscribe API — card tokenisation + recurring charges.
    One instance per request; merchant resolved from Basic auth.
    Requires payme_subscribe_client to be set (injected or overridden).
    """

    def __init__(self, subscribe_client=None):
        """
        subscribe_client: object with methods matching Payme Subscribe API.
        Inject your HTTP client wrapper here.
        """
        if subscribe_client is not None:
            self.client = subscribe_client
        else:
            self.client = PaymeSubscribeClient()

    def resolve_merchant(self, authorization_header: str) -> PaymeMerchant | None:
        creds = _decode_basic(authorization_header)
        if not creds:
            return None
        _, password = creds
        return PaymeMerchant.objects.filter(
            merchant_secret=password,
            is_enabled=True,
        ).first()

    # ── Response builders ─────────────────────────────────────────────────────

    def _ok(self, result: dict, rpc_id) -> dict:
        return success_response(rpc_id, result)

    def _err(self, error: dict, rpc_id, data=None) -> dict:
        err = dict(error)
        if data is not None:
            err["data"] = data
        return error_response(rpc_id, err)

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def dispatch(self, body: dict, authorization_header: str) -> tuple[dict, int]:
        rpc_id = body.get("id")

        merchant = self.resolve_merchant(authorization_header)
        if not merchant:
            return self._err(PaymeError.ACCESS_DENIED, rpc_id), HTTPStatus.OK

        method_name = body.get("method", "").replace(".", "_")
        handler: Callable | None = getattr(self, f"_{method_name}", None)
        if handler is None or not callable(handler):
            return self._err(PaymeError.METHOD_NOT_FOUND, rpc_id), HTTPStatus.OK

        try:
            result = cast(dict, handler(body.get("params", {}), rpc_id, merchant))
            return result, HTTPStatus.OK
        except Exception as exc:
            logger.exception("Subscribe API error in '%s'", method_name)
            return self._err(PaymeError.SYSTEM_ERROR, rpc_id, str(exc)), HTTPStatus.OK

    # ── cards.create ──────────────────────────────────────────────────────────

    def _cards_create(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Initiate card tokenisation. Returns token + OTP prompt flag.
        params: { card: { number, expire }, save: bool }
        """
        try:
            result = self.client.cards_create(
                merchant=merchant,
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

    def _cards_get_verify_code(
        self, params: dict, rpc_id, merchant: PaymeMerchant
    ) -> dict:
        """
        Request OTP SMS for the given token.
        params: { token: str }
        """
        try:
            result = self.client.cards_get_verify_code(
                merchant=merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.get_verify_code failed")
            return self._err(
                PaymeError.SubscribeError.OtpError.OTP_SEND_ERROR, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── cards.verify ──────────────────────────────────────────────────────────

    def _cards_verify(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Verify OTP and activate token. Persists card_token to PaymeSubscription if order_id given.
        params: { token: str, code: str, order_id: str (optional) }
        """
        try:
            result = self.client.cards_verify(
                merchant=merchant,
                token=params["token"],
                code=params["code"],
            )
        except Exception as exc:
            logger.exception("cards.verify failed")
            return self._err(
                PaymeError.SubscribeError.OtpError.OTP_INVALID_CODE, rpc_id, str(exc)
            )

        # Persist verified token to subscription if order_id was provided
        order_id = params.get("order_id")
        if order_id and result.get("card", {}).get("token"):
            PaymeSubscription.objects.update_or_create(
                merchant=merchant,
                order_id=order_id,
                defaults={
                    "card_token": result["card"]["token"],
                    "card_number": result["card"].get("number", ""),
                    "state": PaymeSubscription.SubscriptionState.STATE_ACTIVE,
                },
            )

        return self._ok(result, rpc_id)

    # ── cards.check ───────────────────────────────────────────────────────────

    def _cards_check(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Check card token validity.
        params: { token: str }
        """
        try:
            result = self.client.cards_check(
                merchant=merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.check failed")
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id, str(exc))

        return self._ok(result, rpc_id)

    # ── cards.remove ─────────────────────────────────────────────────────────

    def _cards_remove(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Remove a card token.
        params: { token: str }
        """
        try:
            result = self.client.cards_remove(
                merchant=merchant,
                token=params["token"],
            )
        except Exception as exc:
            logger.exception("cards.remove failed")
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id, str(exc))

        # Deactivate any subscription tied to this token
        PaymeSubscription.objects.filter(
            merchant=merchant, card_token=params["token"]
        ).update(state=PaymeSubscription.SubscriptionState.STATE_CANCELLED)

        return self._ok(result, rpc_id)

    # ── receipts.create ───────────────────────────────────────────────────────

    def _receipts_create(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Create a payment receipt for a card charge.
        params: { amount: int, account: { order_id: str }, description: str (optional) }
        """
        try:
            result = self.client.receipts_create(
                merchant=merchant,
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

    def _receipts_pay(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Charge a card token against a receipt.
        params: { id: str (receipt _id), token: str, payer: { phone: str } (optional) }
        Automatically resolves token from PaymeSubscription if not provided.
        """
        receipt_id = params["id"]
        token = params.get("token")

        # Resolve token from active subscription when not explicitly passed
        if not token:
            order_id = params.get("account", {}).get("order_id")
            if order_id:
                sub = PaymeSubscription.objects.filter(
                    merchant=merchant,
                    order_id=order_id,
                    state=PaymeSubscription.SubscriptionState.STATE_ACTIVE,
                ).first()
                if sub:
                    token = sub.card_token

        if not token:
            return self._err(PaymeError.SubscribeError.CARD_NOT_FOUND, rpc_id)

        try:
            result = self.client.receipts_pay(
                merchant=merchant,
                receipt_id=receipt_id,
                token=token,
                payer=params.get("payer", {}),
            )
        except Exception as exc:
            logger.exception("receipts.pay failed")
            return self._err(
                PaymeError.SubscribeError.INSUFFICIENT_FUNDS, rpc_id, str(exc)
            )

        # Update subscription last_payment_at
        PaymeSubscription.objects.filter(merchant=merchant, card_token=token).update(
            last_payment_at=datetime.now()
        )

        return self._ok(result, rpc_id)

    # ── receipts.send ─────────────────────────────────────────────────────────

    def _receipts_send(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Send a receipt to the payer via SMS.
        params: { id: str, phone: str }
        """
        try:
            result = self.client.receipts_send(
                merchant=merchant,
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

    def _receipts_cancel(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Cancel an unpaid receipt.
        params: { id: str }
        """
        try:
            result = self.client.receipts_cancel(
                merchant=merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.cancel failed")
            return self._err(
                PaymeError.MerchantError.CANNOT_CANCEL_TRANSACTION, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.check ────────────────────────────────────────────────────────

    def _receipts_check(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Check the status of a receipt.
        params: { id: str }
        """
        try:
            result = self.client.receipts_check(
                merchant=merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.check failed")
            return self._err(
                PaymeError.MerchantError.RECEIPTS_NOT_FOUND, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.get ─────────────────────────────────────────────────────────

    def _receipts_get(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        Get a receipt by id.
        params: { id: str }
        """
        try:
            result = self.client.receipts_get(
                merchant=merchant,
                receipt_id=params["id"],
            )
        except Exception as exc:
            logger.exception("receipts.get failed")
            return self._err(
                PaymeError.MerchantError.RECEIPTS_NOT_FOUND, rpc_id, str(exc)
            )

        return self._ok(result, rpc_id)

    # ── receipts.get_all ──────────────────────────────────────────────────────

    def _receipts_get_all(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        """
        List receipts with optional filters.
        params: { count: int, _from: int, _to: int, offset: int }
        """
        try:
            result = self.client.receipts_get_all(
                merchant=merchant,
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


sapi = PaymeSubscribeAPI()
