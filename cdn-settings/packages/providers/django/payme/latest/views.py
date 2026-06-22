import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .errors import PaymeError, error_response, success_response
from .models import PaymeTransaction
from .utils import check_auth_header, get_active_merchant, get_order, now_ms


@method_decorator(csrf_exempt, name="dispatch")
class MerchantAPIView(View):
    """
    Plug-in Payme MerchantAPI endpoint.

    Usage:
        class MyPaymeView(MerchantAPIView):
            def check_order(self, amount, account, **kwargs):
                order = Order.objects.get(id=account["order_id"])
                if order.amount != amount:
                    return self.INVALID_AMOUNT
                return self.ORDER_FOUND

            def successfully_payment(self, account, transaction, **kwargs):
                Order.objects.filter(id=account["order_id"]).update(is_paid=True)

            def cancel_payment(self, account, transaction, **kwargs):
                Order.objects.filter(id=account["order_id"]).update(is_paid=False)

    urlpatterns = [
        path("payme/", MyPaymeView.as_view()),
    ]
    """

    # status constants
    ORDER_FOUND = 1
    ORDER_NOT_FOUND = -1
    INVALID_AMOUNT = -2
    ORDER_ALREADY_PAID = -3

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(error_response(None, PaymeError.PARSE_ERROR))

        request_id = body.get("id")
        method = body.get("method")
        params = body.get("params", {})

        # resolve merchant — multi-merchant: from DB by secret key header
        merchant = None
        auth_ok, merchant = check_auth_header(request, merchant=None)
        if not auth_ok:
            return JsonResponse(
                error_response(request_id, PaymeError.INSUFFICIENT_PRIVILEGE)
            )

        handlers = {
            "CheckPerformTransaction": self._check_perform,
            "CreateTransaction": self._create,
            "PerformTransaction": self._perform,
            "CancelTransaction": self._cancel,
            "CheckTransaction": self._check,
            "GetStatement": self._statement,
        }

        handler = handlers.get(method)
        if handler is None:
            return JsonResponse(error_response(request_id, PaymeError.METHOD_NOT_FOUND))

        result = handler(request_id, params, merchant)
        return JsonResponse(result)

    # ------------------------------------------------------------------
    # Overridable hooks
    # ------------------------------------------------------------------

    def check_order(self, amount, account, **kwargs):
        raise NotImplementedError("Implement check_order()")

    def successfully_payment(self, account, transaction, **kwargs):
        pass

    def cancel_payment(self, account, transaction, **kwargs):
        pass

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _check_perform(self, request_id, params, merchant):
        amount = params.get("amount")
        account = params.get("account", {})

        status = self.check_order(amount=amount, account=account)

        if status == self.ORDER_NOT_FOUND or status == self.INVALID_ACCOUNT:
            return error_response(request_id, PaymeError.ORDER_NOT_FOUND)
        if status == self.INVALID_AMOUNT:
            return error_response(request_id, PaymeError.INVALID_AMOUNT)
        if status == self.ORDER_ALREADY_PAID:
            return error_response(request_id, PaymeError.ORDER_ALREADY_PAID)

        return success_response(request_id, {"allow": True})

    def _create(self, request_id, params, merchant):
        amount = params.get("amount")
        account = params.get("account", {})
        transaction_id = params.get("id")
        time_ms = params.get("time")

        # check if already exists
        existing = PaymeTransaction.objects.filter(
            transaction_id=transaction_id
        ).first()
        if existing:
            if existing.state != PaymeTransaction.STATE_CREATED:
                return error_response(request_id, PaymeError.TRANSACTION_CANNOT_PERFORM)
            return success_response(
                request_id,
                {
                    "create_time": existing.create_time,
                    "transaction": str(existing.id),
                    "state": existing.state,
                },
            )

        status = self.check_order(amount=amount, account=account)
        if status == self.ORDER_NOT_FOUND:
            return error_response(request_id, PaymeError.ORDER_NOT_FOUND)
        if status == self.INVALID_AMOUNT:
            return error_response(request_id, PaymeError.INVALID_AMOUNT)
        if status == self.ORDER_ALREADY_PAID:
            return error_response(request_id, PaymeError.ORDER_ALREADY_PAID)

        order_id = account.get("order_id") or account.get(
            list(account.keys())[0] if account else "id"
        )

        txn = PaymeTransaction.objects.create(
            merchant=merchant,
            transaction_id=transaction_id,
            order_id=str(order_id),
            amount=amount,
            state=PaymeTransaction.STATE_CREATED,
            create_time=time_ms or now_ms(),
        )

        return success_response(
            request_id,
            {
                "create_time": txn.create_time,
                "transaction": str(txn.id),
                "state": txn.state,
            },
        )

    def _perform(self, request_id, params, merchant):
        transaction_id = params.get("id")
        txn = PaymeTransaction.objects.filter(transaction_id=transaction_id).first()

        if not txn:
            return error_response(request_id, PaymeError.TRANSACTION_NOT_FOUND)

        if txn.state == PaymeTransaction.STATE_COMPLETED:
            return success_response(
                request_id,
                {
                    "transaction": str(txn.id),
                    "perform_time": txn.perform_time,
                    "state": txn.state,
                },
            )

        if txn.state != PaymeTransaction.STATE_CREATED:
            return error_response(request_id, PaymeError.TRANSACTION_CANNOT_PERFORM)

        perform_time = now_ms()
        txn.state = PaymeTransaction.STATE_COMPLETED
        txn.perform_time = perform_time
        txn.save(update_fields=["state", "perform_time", "updated_at"])

        order = get_order(txn.order_id)
        self.successfully_payment(
            account={"order_id": txn.order_id}, transaction=txn, order=order
        )

        return success_response(
            request_id,
            {
                "transaction": str(txn.id),
                "perform_time": perform_time,
                "state": txn.state,
            },
        )

    def _cancel(self, request_id, params, merchant):
        transaction_id = params.get("id")
        reason = params.get("reason")

        txn = PaymeTransaction.objects.filter(transaction_id=transaction_id).first()
        if not txn:
            return error_response(request_id, PaymeError.TRANSACTION_NOT_FOUND)

        if txn.state == PaymeTransaction.STATE_COMPLETED:
            new_state = PaymeTransaction.STATE_CANCELLED_AFTER_COMPLETE
        elif txn.state == PaymeTransaction.STATE_CREATED:
            new_state = PaymeTransaction.STATE_CANCELLED
        else:
            return success_response(
                request_id,
                {
                    "transaction": str(txn.id),
                    "cancel_time": txn.cancel_time,
                    "state": txn.state,
                },
            )

        cancel_time = now_ms()
        txn.state = new_state
        txn.reason = reason
        txn.cancel_time = cancel_time
        txn.save(update_fields=["state", "reason", "cancel_time", "updated_at"])

        order = get_order(txn.order_id)
        self.cancel_payment(
            account={"order_id": txn.order_id}, transaction=txn, order=order
        )

        return success_response(
            request_id,
            {
                "transaction": str(txn.id),
                "cancel_time": cancel_time,
                "state": new_state,
            },
        )

    def _check(self, request_id, params, merchant):
        transaction_id = params.get("id")
        txn = PaymeTransaction.objects.filter(transaction_id=transaction_id).first()

        if not txn:
            return error_response(request_id, PaymeError.TRANSACTION_NOT_FOUND)

        return success_response(
            request_id,
            {
                "create_time": txn.create_time,
                "perform_time": txn.perform_time or 0,
                "cancel_time": txn.cancel_time or 0,
                "transaction": str(txn.id),
                "state": txn.state,
                "reason": txn.reason,
            },
        )

    def _statement(self, request_id, params, merchant):
        from_time = params.get("from")
        to_time = params.get("to")

        qs = PaymeTransaction.objects.filter(
            create_time__gte=from_time,
            create_time__lte=to_time,
        )
        if merchant:
            qs = qs.filter(merchant=merchant)

        transactions = []
        for txn in qs:
            transactions.append(
                {
                    "id": txn.transaction_id,
                    "time": txn.create_time,
                    "amount": txn.amount,
                    "account": {"order_id": txn.order_id},
                    "create_time": txn.create_time,
                    "perform_time": txn.perform_time or 0,
                    "cancel_time": txn.cancel_time or 0,
                    "transaction": str(txn.id),
                    "state": txn.state,
                    "reason": txn.reason,
                }
            )

        return success_response(request_id, {"transactions": transactions})


@method_decorator(csrf_exempt, name="dispatch")
class SubscriptionAPIView(View):
    """
    Payme Cards/Subscriptions (P2P token-based) API.

    Handles:
        cards.create  → request OTP for card
        cards.verify  → verify OTP, get token
        cards.check   → check card info
        cards.remove  → remove card token
        receipts.create  → create receipt for subscription charge
        receipts.pay     → charge saved card
        receipts.get     → get receipt info
        receipts.cancel  → cancel receipt
    """

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(error_response(None, PaymeError.PARSE_ERROR))

        request_id = body.get("id")
        method = body.get("method")
        params = body.get("params", {})

        auth_ok, merchant = check_auth_header(request)
        if not auth_ok:
            return JsonResponse(
                error_response(request_id, PaymeError.INSUFFICIENT_PRIVILEGE)
            )

        handlers = {
            "cards.create": self._cards_create,
            "cards.verify": self._cards_verify,
            "cards.check": self._cards_check,
            "cards.remove": self._cards_remove,
            "receipts.create": self._receipts_create,
            "receipts.pay": self._receipts_pay,
            "receipts.get": self._receipts_get,
            "receipts.cancel": self._receipts_cancel,
        }

        handler = handlers.get(method)
        if handler is None:
            return JsonResponse(error_response(request_id, PaymeError.METHOD_NOT_FOUND))

        result = handler(request_id, params, merchant)
        return JsonResponse(result)

    # ------------------------------------------------------------------
    # Overridable hooks
    # ------------------------------------------------------------------

    def on_card_verified(self, token, card_number, merchant, **kwargs):
        """Called after card is verified. Save token to subscription if needed."""
        pass

    def on_subscription_paid(self, subscription, receipt, **kwargs):
        """Called after subscription charge succeeds."""
        pass

    # ------------------------------------------------------------------
    # Internal handlers — proxy to Payme Cards API
    # ------------------------------------------------------------------

    def _payme_request(self, method, params, merchant):
        import base64
        import urllib.request

        from . import config

        if merchant and merchant.test_mode:
            url = "https://checkout.test.paycom.uz/api"
            key = config.PAYME_TEST_SECRET_KEY() or merchant.secret_key
        else:
            url = "https://checkout.paycom.uz/api"
            key = merchant.secret_key if merchant else config.PAYME_SECRET_KEY()

        merchant_id = merchant.merchant_id if merchant else config.PAYME_MERCHANT_ID()
        token = base64.b64encode(f"{merchant_id}:{key}".encode()).decode()

        payload = json.dumps(
            {
                "id": now_ms(),
                "method": method,
                "params": params,
            }
        ).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "X-Auth": token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def _cards_create(self, request_id, params, merchant):
        try:
            resp = self._payme_request("cards.create", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _cards_verify(self, request_id, params, merchant):
        try:
            resp = self._payme_request("cards.verify", params, merchant)
            result = resp.get("result", {})
            card = result.get("card", {})
            if card.get("verify"):
                self.on_card_verified(
                    token=card.get("token"),
                    card_number=card.get("number"),
                    merchant=merchant,
                )
            return success_response(request_id, result)
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _cards_check(self, request_id, params, merchant):
        try:
            resp = self._payme_request("cards.check", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _cards_remove(self, request_id, params, merchant):
        try:
            resp = self._payme_request("cards.remove", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _receipts_create(self, request_id, params, merchant):
        try:
            resp = self._payme_request("receipts.create", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _receipts_pay(self, request_id, params, merchant):
        try:
            resp = self._payme_request("receipts.pay", params, merchant)
            result = resp.get("result", {})
            receipt = result.get("receipt", {})
            if receipt.get("state") == 4:  # paid
                sub = None
                try:
                    from .models import PaymeSubscription

                    sub = PaymeSubscription.objects.filter(
                        card_token=params.get("token")
                    ).first()
                    if sub:
                        sub.last_payment_at = __import__(
                            "django.utils.timezone", fromlist=["timezone"]
                        ).timezone.now()
                        sub.save(update_fields=["last_payment_at", "updated_at"])
                except Exception:
                    pass
                self.on_subscription_paid(subscription=sub, receipt=receipt)
            return success_response(request_id, result)
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _receipts_get(self, request_id, params, merchant):
        try:
            resp = self._payme_request("receipts.get", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )

    def _receipts_cancel(self, request_id, params, merchant):
        try:
            resp = self._payme_request("receipts.cancel", params, merchant)
            return success_response(request_id, resp.get("result", {}))
        except Exception as e:
            return error_response(
                request_id, {**PaymeError.INTERNAL_ERROR, "data": str(e)}
            )
