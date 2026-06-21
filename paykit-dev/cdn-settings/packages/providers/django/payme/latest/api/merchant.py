# paykit/providers/payme/merchant_api.py
import base64
import logging
from http import HTTPStatus
from typing import Callable, cast

from paykit.providers.payme.models import PaymeTransaction, TransactionState

logger = logging.getLogger(__name__)

ERRORS = {
    "PARSE_ERROR": {
        "code": -32700,
        "message": {"ru": "Ошибка разбора JSON", "en": "Parse error"},
    },
    "METHOD_NOT_FOUND": {
        "code": -32601,
        "message": {"ru": "Метод не найден", "en": "Method not found"},
    },
    "INVALID_PARAMS": {
        "code": -32600,
        "message": {"ru": "Неверные параметры", "en": "Invalid params"},
    },
    "INTERNAL_ERROR": {
        "code": -32400,
        "message": {"ru": "Внутренняя ошибка", "en": "Internal error"},
    },
    "INSUFFICIENT_PRIV": {
        "code": -32504,
        "message": {"ru": "Недостаточно прав", "en": "Insufficient privileges"},
    },
    "ORDER_NOT_FOUND": {
        "code": -31050,
        "message": {"ru": "Заказ не найден", "en": "Order not found"},
    },
    "ORDER_NOT_ALLOWED": {
        "code": -31051,
        "message": {"ru": "Оплата недоступна", "en": "Payment not allowed"},
    },
    "TRANSACTION_NOT_FOUND": {
        "code": -31003,
        "message": {"ru": "Транзакция не найдена", "en": "Transaction not found"},
    },
    "TRANSACTION_CANCELLED": {
        "code": -31008,
        "message": {"ru": "Транзакция отменена", "en": "Transaction cancelled"},
    },
    "INVALID_AMOUNT": {
        "code": -31001,
        "message": {"ru": "Неверная сумма", "en": "Invalid amount"},
    },
}


class PaymeMerchantAPI:
    """
    Inherit this, set merchant_id + merchant_key, override check_order().
    All 6 Payme methods are implemented against PaymeTransaction model.
    """

    merchant_id: str = None  # Payme's m= value  (public)
    merchant_key: str = None  # Payme's secret key (used in Basic auth password)

    def __init__(self, merchant_id: str = None, merchant_key: str = None):
        from paykit.providers.payme.config import defaults

        self.merchant_id = (
            merchant_id or self.__class__.merchant_id or defaults.merchant_key
        )
        self.merchant_key = (
            merchant_key or self.__class__.merchant_key or defaults.merchant_key
        )
        if not self.merchant_key:
            raise ValueError("merchant_key is required")

    # ── Override this ────────────────────────────────────────────────────────
    def check_order(self, order_id: str, amount: int) -> bool:
        """Return True if order exists and amount is valid. Override in subclass."""
        raise NotImplementedError("check_order() must be implemented")

    # ── Auth ─────────────────────────────────────────────────────────────────
    def check_auth(self, authorization_header: str) -> bool:
        try:
            _, encoded = authorization_header.split(" ", 1)
            login, password = base64.b64decode(encoded).decode().split(":", 1)
            return login == self.merchant_id and password == self.merchant_key
        except Exception:
            return False

    # ── Response builders ────────────────────────────────────────────────────
    def ok(self, result: dict, rpc_id) -> dict:
        return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

    def error(self, key: str, rpc_id, data=None) -> dict:
        err = dict(ERRORS.get(key, ERRORS["INTERNAL_ERROR"]))
        body = {"jsonrpc": "2.0", "id": rpc_id, "error": err}
        if data is not None:
            body["error"]["data"] = data
        return body

    # ── Dispatcher ───────────────────────────────────────────────────────────
    def dispatch(self, body: dict, authorization_header: str) -> tuple[dict, int]:
        rpc_id = body.get("id")

        if not self.check_auth(authorization_header):
            return self.error("INSUFFICIENT_PRIV", rpc_id), HTTPStatus.OK

        method_name = body.get("method")
        handler: Callable[..., dict] | None = getattr(self, f"_{method_name}", None)
        if handler is None or not callable(handler):
            return self.error("METHOD_NOT_FOUND", rpc_id), HTTPStatus.OK

        try:
            result = cast(dict, handler(body.get("params", {}), rpc_id))
            return self.ok(result, rpc_id), HTTPStatus.OK
        except NotImplementedError as exc:
            logger.warning("Method '%s' not implemented: %s", method_name, exc)
            return self.error("INTERNAL_ERROR", rpc_id, str(exc)), HTTPStatus.OK
        except Exception as exc:
            logger.exception("Error in '%s'", method_name)
            return self.error("INTERNAL_ERROR", rpc_id, str(exc)), HTTPStatus.OK

    # ── Payme methods ────────────────────────────────────────────────────────
    def _CheckPerformTransaction(self, params: dict, rpc_id) -> dict:
        order_id = params["account"]["order_id"]
        amount = params["amount"]

        if not self.check_order(order_id, amount):
            return self.error("ORDER_NOT_FOUND", rpc_id)

        return {"allow": True}

    def _CreateTransaction(self, params: dict, rpc_id) -> dict:
        import time

        payme_id = params["id"]
        payme_time = params["time"]
        amount = params["amount"]
        order_id = params["account"]["order_id"]

        tx = PaymeTransaction.objects.filter(payme_id=payme_id).first()

        if tx:
            if tx.state != TransactionState.PENDING:
                return self.error("TRANSACTION_CANCELLED", rpc_id)
            return {
                "create_time": tx.create_time,
                "transaction": str(tx.pk),
                "state": tx.state,
            }

        if not self.check_order(order_id, amount):
            return self.error("ORDER_NOT_FOUND", rpc_id)

        now = int(time.time() * 1000)
        tx = PaymeTransaction.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
            merchant_id=self.merchant_id,
            merchant_key=self.merchant_key,
            payme_id=payme_id,
            payme_time=payme_time,
            order_id=order_id,
            amount=amount,
            state=TransactionState.PENDING,
            create_time=now,
        )
        return {
            "create_time": tx.create_time,
            "transaction": str(tx.pk),
            "state": tx.state,
        }

    def _PerformTransaction(self, params: dict, rpc_id) -> dict:
        import time

        tx = PaymeTransaction.objects.filter(payme_id=params["id"]).first()
        if not tx:
            return self.error("TRANSACTION_NOT_FOUND", rpc_id)

        if tx.state == TransactionState.PERFORMED:
            return {
                "transaction": str(tx.pk),
                "perform_time": tx.perform_time,
                "state": tx.state,
            }

        if tx.state != TransactionState.PENDING:
            return self.error("TRANSACTION_CANCELLED", rpc_id)

        now = int(time.time() * 1000)
        tx.state = TransactionState.PERFORMED
        tx.perform_time = now
        tx.save(update_fields=["state", "perform_time"])

        return {
            "transaction": str(tx.pk),
            "perform_time": tx.perform_time,
            "state": tx.state,
        }

    def _CancelTransaction(self, params: dict, rpc_id) -> dict:
        import time

        tx = PaymeTransaction.objects.filter(payme_id=params["id"]).first()
        if not tx:
            return self.error("TRANSACTION_NOT_FOUND", rpc_id)

        if tx.state == TransactionState.PENDING:
            tx.state = TransactionState.CANCELLED
            tx.cancel_time = int(time.time() * 1000)
            tx.reason = params.get("reason")
            tx.save(update_fields=["state", "cancel_time", "reason"])

        elif tx.state == TransactionState.PERFORMED:
            tx.state = TransactionState.CANCELLED_AFTER_PERFORM
            tx.cancel_time = int(time.time() * 1000)
            tx.reason = params.get("reason")
            tx.save(update_fields=["state", "cancel_time", "reason"])

        # already cancelled — idempotent, fall through
        return {
            "transaction": str(tx.pk),
            "cancel_time": tx.cancel_time,
            "state": tx.state,
        }

    def _CheckTransaction(self, params: dict, rpc_id) -> dict:
        tx = PaymeTransaction.objects.filter(payme_id=params["id"]).first()
        if not tx:
            return self.error("TRANSACTION_NOT_FOUND", rpc_id)

        return {
            "create_time": tx.create_time,
            "perform_time": tx.perform_time or 0,
            "cancel_time": tx.cancel_time or 0,
            "transaction": str(tx.pk),
            "state": tx.state,
            "reason": tx.reason,
        }

    def _GetStatement(self, params: dict, rpc_id) -> dict:
        txs = PaymeTransaction.objects.filter(
            merchant_id=self.merchant_id,
            create_time__gte=params["from"],
            create_time__lte=params["to"],
        )
        return {
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
        }
