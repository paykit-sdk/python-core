import logging
from http import HTTPStatus
from typing import Callable, cast

from paykit.providers.payme.api.errors import (
    PaymeError,
    error_response,
    success_response,
)
from paykit.providers.payme.api.utils import _decode_basic, _now_ms
from paykit.providers.payme.models import (
    PaymeMerchant,
    PaymeTransaction,
)

logger = logging.getLogger(__name__)


class Triggers:
    def check_order(self, merchant: PaymeMerchant, order_id: str, amount: int) -> bool:
        """Return True if the order exists and amount is valid. Must be overridden."""
        raise NotImplementedError("check_order() must be implemented")

    def on_payment(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        """Called when a transaction is successfully performed. Must be overridden."""
        print("on_payment() must be implemented")
        # raise NotImplementedError("on_payment() must be implemented")

    def on_cancelled(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        """Called when a PENDING transaction is cancelled. Must be overridden."""
        print("on_cancelled() must be implemented")
        # raise NotImplementedError("on_cancelled() must be implemented")

    def on_cancelled_after_perform(
        self, merchant: PaymeMerchant, tx: PaymeTransaction
    ) -> None:
        """Called when an already PERFORMED transaction is cancelled. Must be overridden."""
        print("on_cancelled_after_perform() must be implemented")
        # raise NotImplementedError("on_cancelled_after_perform() must be implemented")


class PaymeMerchantAPI(Triggers):
    """
    Inherit this class and override check_order().
    Auth is resolved from PaymeMerchant DB records — no hardcoded keys.
    """

    # ── Response builders ─────────────────────────────────────────────────────

    def _ok(self, result: dict, rpc_id) -> dict:
        return success_response(rpc_id, result)

    def _err(self, error: dict, rpc_id, data=None) -> dict:
        err = dict(error)
        if data is not None:
            err["data"] = data
        return error_response(rpc_id, err)

    def resolve_merchant(self, authorization_header: str) -> PaymeMerchant | None:
        creds = _decode_basic(authorization_header)
        if not creds:
            return None
        _, password = creds
        # Payme sends: login = "Paycom", password = merchant_secret
        return PaymeMerchant.objects.filter(
            merchant_secret=password,
            is_enabled=True,
        ).first()

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def dispatch(self, body: dict, authorization_header: str) -> tuple[dict, int]:
        rpc_id = body.get("id")

        merchant = self.resolve_merchant(authorization_header)
        if not merchant:
            return self._err(PaymeError.ACCESS_DENIED, rpc_id), HTTPStatus.OK

        method_name = body.get("method")
        handler: Callable | None = getattr(self, f"_{method_name}", None)
        if handler is None or not callable(handler):
            return self._err(PaymeError.METHOD_NOT_FOUND, rpc_id), HTTPStatus.OK

        try:
            result = cast(dict, handler(body.get("params", {}), rpc_id, merchant))
            return result, HTTPStatus.OK
        except Exception as exc:
            logger.exception("Error in '%s'", method_name)
            return self._err(PaymeError.SYSTEM_ERROR, rpc_id, str(exc)), HTTPStatus.OK

    # ── Payme methods ─────────────────────────────────────────────────────────

    def _CheckPerformTransaction(
        self, params: dict, rpc_id, merchant: PaymeMerchant
    ) -> dict:
        order_id = params["account"]["order_id"]
        amount = params["amount"]

        if not self.check_order(merchant, order_id, amount):
            return self._err(PaymeError.MerchantError.ACCOUNT_NOT_FOUND, rpc_id)

        return self._ok({"allow": True}, rpc_id)

    def _CreateTransaction(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        payme_id = params["id"]
        payme_time = params["time"]
        amount = params["amount"]
        order_id = params["account"]["order_id"]

        tx = PaymeTransaction.objects.filter(
            payme_id=payme_id, merchant=merchant
        ).first()

        if tx:
            if tx.state != PaymeTransaction.TransactionState.PENDING:
                return self._err(
                    PaymeError.MerchantError.CANNOT_PERFORM_OPERATION, rpc_id
                )
            return self._ok(
                {
                    "create_time": tx.create_time,
                    "transaction": str(tx.pk),
                    "state": tx.state,
                },
                rpc_id,
            )

        if not self.check_order(merchant, order_id, amount):
            return self._err(PaymeError.MerchantError.ACCOUNT_NOT_FOUND, rpc_id)

        tx = PaymeTransaction.objects.create(
            merchant=merchant,
            payme_id=payme_id,
            payme_time=payme_time,
            order_id=order_id,
            amount=amount,
            state=PaymeTransaction.TransactionState.PENDING,
            create_time=_now_ms(),
        )
        return self._ok(
            {
                "create_time": tx.create_time,
                "transaction": str(tx.pk),
                "state": tx.state,
            },
            rpc_id,
        )

    def _PerformTransaction(
        self, params: dict, rpc_id, merchant: PaymeMerchant
    ) -> dict:
        tx = PaymeTransaction.objects.filter(
            payme_id=params["id"], merchant=merchant
        ).first()
        if not tx:
            return self._err(PaymeError.MerchantError.TRANSACTION_NOT_FOUND, rpc_id)

        if tx.state == PaymeTransaction.TransactionState.PERFORMED:
            return self._ok(
                {
                    "transaction": str(tx.pk),
                    "perform_time": tx.perform_time,
                    "state": tx.state,
                },
                rpc_id,
            )

        if tx.state != PaymeTransaction.TransactionState.PENDING:
            return self._err(PaymeError.MerchantError.CANNOT_PERFORM_OPERATION, rpc_id)

        tx.state = PaymeTransaction.TransactionState.PERFORMED
        tx.perform_time = _now_ms()
        tx.save(update_fields=["state", "perform_time"])

        self.on_payment(merchant, tx)

        return self._ok(
            {
                "transaction": str(tx.pk),
                "perform_time": tx.perform_time,
                "state": tx.state,
            },
            rpc_id,
        )

    def _CancelTransaction(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        tx = PaymeTransaction.objects.filter(
            payme_id=params["id"], merchant=merchant
        ).first()
        if not tx:
            return self._err(PaymeError.MerchantError.TRANSACTION_NOT_FOUND, rpc_id)

        if tx.state in (
            PaymeTransaction.TransactionState.CANCELLED,
            PaymeTransaction.TransactionState.CANCELLED_AFTER_PERFORM,
        ):
            return self._ok(
                {
                    "transaction": str(tx.pk),
                    "cancel_time": tx.cancel_time,
                    "state": tx.state,
                },
                rpc_id,
            )

        now = _now_ms()
        reason = params.get("reason")

        if tx.state == PaymeTransaction.TransactionState.PENDING:
            tx.state = PaymeTransaction.TransactionState.CANCELLED
            tx.cancel_time = now
            tx.reason = reason
            tx.save(update_fields=["state", "cancel_time", "reason"])
            self.on_cancelled(merchant, tx)

        elif tx.state == PaymeTransaction.TransactionState.PERFORMED:
            tx.state = PaymeTransaction.TransactionState.CANCELLED_AFTER_PERFORM
            tx.cancel_time = now
            tx.reason = reason
            tx.save(update_fields=["state", "cancel_time", "reason"])
            self.on_cancelled_after_perform(merchant, tx)

        return self._ok(
            {
                "transaction": str(tx.pk),
                "cancel_time": tx.cancel_time,
                "state": tx.state,
            },
            rpc_id,
        )

    def _CheckTransaction(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        tx = PaymeTransaction.objects.filter(
            payme_id=params["id"], merchant=merchant
        ).first()
        if not tx:
            return self._err(PaymeError.MerchantError.TRANSACTION_NOT_FOUND, rpc_id)

        return self._ok(
            {
                "create_time": tx.create_time,
                "perform_time": tx.perform_time or 0,
                "cancel_time": tx.cancel_time or 0,
                "transaction": str(tx.pk),
                "state": tx.state,
                "reason": tx.reason,
            },
            rpc_id,
        )

    def _GetStatement(self, params: dict, rpc_id, merchant: PaymeMerchant) -> dict:
        txs = PaymeTransaction.objects.filter(
            merchant=merchant,
            create_time__gte=params["from"],
            create_time__lte=params["to"],
        )
        return self._ok(
            {
                "transactions": [
                    {
                        "id": tx.payme_id,
                        "time": tx.payme_time,
                        "amount": tx.amount,
                        "account": {"order_id": tx.order_id},
                        "create_time": tx.create_time,
                        "perform_time": tx.perform_time or 0,
                        "cancel_time": tx.cancel_time or 0,
                        "transaction": str(tx.pk),
                        "state": tx.state,
                        "reason": tx.reason,
                    }
                    for tx in txs
                ]
            },
            rpc_id,
        )
